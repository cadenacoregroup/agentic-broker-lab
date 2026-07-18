"""The demo agent: three acts. Phase 0 uses a scripted planner;
swap in a real LLM later — the authorization flow doesn't change."""
import os, sys, uuid
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.config import BROKER_URL, ERP_URL
from idp.issue import user_token, agent_token

MARIA = user_token("maria@cadenacore.dev")
AGENT = agent_token("invoice-agent-01")

def declare(task_class, task_id=None, initiated_by="human"):
    return {"task_id": task_id or f"task-{uuid.uuid4().hex[:6]}",
            "task_class": task_class, "params": {},
            "initiated_by": initiated_by}

def grant(decl, delegation=MARIA):
    return httpx.post(f"{BROKER_URL}/grant", json=decl,
                      headers={"Authorization": f"Bearer {AGENT}",
                               "X-Delegation": delegation})

def act(n, title):
    print(f"\n{'='*62}\nACT {n} — {title}\n{'='*62}")

# ---------------- ACT 1: the happy path ----------------
act(1, "Declared task, scoped grant, legitimate access")
decl = declare("invoice_analysis")
r = grant(decl)
print(f"[broker] grant: {r.status_code} scope={r.json().get('scope')} "
      f"ttl={r.json().get('expires_in')}s")
token = r.json()["access_token"]
r = httpx.get(f"{ERP_URL}/invoices", params={"quarter": "Q2"},
              headers={"Authorization": f"Bearer {token}"})
body = r.json()
print(f"[erp]    {r.status_code} — {len(body['invoices'])} invoices; "
      f"served to agent={body['served_to']['agent']} "
      f"on_behalf_of={body['served_to']['on_behalf_of']}")

# Same task class, different provenance: a scheduled nightly run.
# Identical scope — but the audit trail now distinguishes them.
r = grant(declare("invoice_analysis", initiated_by="schedule"))
print(f"[broker] same task via schedule     -> {r.status_code} "
      f"(audit will show via:schedule vs via:human above)")

# ---------------- ACT 2: the boundaries ----------------
act(2, "Out-of-scope attempts are denied — at broker AND at resource")
r = grant(declare("payroll_review"))
print(f"[broker] undeclared task class      -> {r.status_code}: {r.json()['detail']}")
r = httpx.get(f"{ERP_URL}/payroll", headers={"Authorization": f"Bearer {token}"})
print(f"[erp]    invoices token on /payroll -> {r.status_code}: {r.json()['detail']}")
r = httpx.post(f"{ERP_URL}/ledger", json={"account": "4000", "amount": 99.0},
               headers={"Authorization": f"Bearer {token}"})
print(f"[erp]    invoices token on /ledger  -> {r.status_code}: {r.json()['detail']}")
r = grant(declare("ledger_posting"), delegation=user_token("intern@cadenacore.dev"))
print(f"[broker] intern delegates posting   -> {r.status_code}: {r.json()['detail']}"
      f"  (empty intersection: delegator lacks the right)")

# ---------------- ACT 3: the irreversible verb ----------------
act(3, "Irreversible verb parks for the delegating human")
decl = declare("ledger_posting")
r = grant(decl)
rid = r.json()["grant_request_id"]
print(f"[broker] ledger_posting -> {r.json()['status']} (id={rid}, "
      f"approver={r.json()['approver']})")
r = httpx.post(f"{BROKER_URL}/approve/{rid}", headers={"X-Approver": MARIA})
print(f"[maria]  approves -> {r.status_code}, scope={r.json()['scope']} "
      f"ttl={r.json()['expires_in']}s")
token = r.json()["access_token"]
r = httpx.post(f"{ERP_URL}/ledger", json={"account": "4000", "amount": 30000.0},
               headers={"Authorization": f"Bearer {token}"})
print(f"[erp]    {r.status_code} — posted {r.json()['posted']['amount']} "
      f"by agent={r.json()['by']['agent']} "
      f"on_behalf_of={r.json()['by']['on_behalf_of']}")

print("\nDone. Run `python audit/view.py` to see the full attribution chain.\n")

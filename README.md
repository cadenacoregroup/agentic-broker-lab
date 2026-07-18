# Agentic Broker Lab

A minimal, working prototype of **runtime authorization for AI agents**: the
layer between agent runtimes and enterprise resources that turns a declared
task into a short-lived, narrowly-scoped, fully-attributed credential.

Companion code for the essay series starting with
*"Your Agents Don't Have an Authentication Problem. They Have an Authorization Problem."*

## The idea in one sentence

**Effective grant = task profile ∩ agent ceiling ∩ delegator rights** —
intersection at every hop, expiry instead of deprovisioning, attribution in
every log line.

## Architecture (Phase 0)

```
  agent (declares task)
     │  agent identity token + delegation token
     ▼
  BROKER  ──── policy: task_catalog.yaml ∩ registry.yaml
     │           │
     │           └── irreversible verb? → park for human approval
     │  mints short-lived scoped JWT (act claim = delegation chain)
     ▼
  MOCK ERP  (accepts broker tokens ONLY — never raw IdP tokens)

  every decision → audit/audit.jsonl
```

Phase 0 mocks the IdP (`idp/issue.py`). Phase 1 swaps it for Entra ID
(JWKS validation + on-behalf-of token exchange) — nothing downstream changes.

## Quickstart

```bash
pip install -r requirements.txt
uvicorn broker.main:app --port 8001 &
uvicorn erp.main:app --port 8002 &
python agent/demo.py       # runs all three acts
python audit/view.py       # the attribution chain
pytest                     # policy unit tests
```

## The three acts

1. **Happy path** — agent declares `invoice_analysis`, receives a 10-minute
   read-only grant, calls the ERP. The response names the agent *and* the
   human it acted for.
2. **Boundaries** — undeclared task class: denied at the broker. Legitimate
   token used outside its scope: denied at the resource. A delegator without
   the underlying right: denied by empty intersection.
3. **The irreversible verb** — `ledger_posting` parks as `pending_approval`;
   only the delegating human can release it; the grant that results is still
   scoped and short-lived.

## Initiation provenance

Every grant records **how the task came to exist** — `initiated_by: human |
schedule | agent` — as a first-class claim in the minted token and a field in
the audit log. A 2 a.m. action running on a standing schedule and one spawned
mid-chain by another agent deserve different scrutiny even with identical
scopes. Phase 2 risk-tiering keys off this (e.g., scheduled or agent-spawned
irreversible verbs always require approval).

## Roadmap

- **Phase 1** — real identities: Entra ID sign-in, agent as service principal,
  OBO/token exchange in `_mint`.
- **Phase 2** — delegation-chain hop (sub-agent receives the intersection of
  its parent's grant), divergence detection + revocation of live grants.
- **Phase 3** — governance plane: Entra Agent ID + access packages as the
  "may ever" ceiling; publish alongside the "Anatomy of an Identity Broker" essay.

*Deliberately not production-grade: one scenario, one resource, shapes over
robustness. HS256 shared secrets stand in for JWKS; a dict stands in for a
pending-approval store.*

© Cadena Core Group — MIT license.

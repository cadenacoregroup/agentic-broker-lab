"""The Broker: the runtime authorization layer.
Verify requester -> decide (policy intersection) -> mint (short-lived, scoped) -> audit."""
import json, os, sys, time, uuid
import jwt
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.config import (IDP_SECRET, IDP_ISSUER, BROKER_SECRET, BROKER_ISSUER,
                           ERP_AUDIENCE, AUDIT_LOG)
from broker.policy import evaluate

app = FastAPI(title="Cadena Broker (Phase 0)")
PENDING: dict = {}  # grant_request_id -> context awaiting human approval

class TaskDeclaration(BaseModel):
    task_id: str
    task_class: str
    params: dict = {}
    # Initiation provenance: how this task came to exist. A human-run action,
    # a standing schedule, and an agent-spawned sub-task deserve different
    # scrutiny even with identical scopes. (h/t community discussion on post 1)
    initiated_by: str = "human"   # human | schedule | agent

def _validate_identity(token: str, expected_type: str) -> str:
    try:
        claims = jwt.decode(token, IDP_SECRET, algorithms=["HS256"], issuer=IDP_ISSUER)
    except jwt.PyJWTError as e:
        raise HTTPException(401, f"invalid {expected_type} token: {e}")
    if claims.get("typ") != expected_type:
        raise HTTPException(401, f"expected a {expected_type} token")
    return claims["sub"]

def _audit(event: str, **fields):
    os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "event": event, **fields}) + "\n")

def _mint(agent: str, delegator: str, decl: TaskDeclaration, scope, ttl) -> dict:
    now = int(time.time())
    token = jwt.encode(
        {"iss": BROKER_ISSUER, "aud": ERP_AUDIENCE, "sub": agent,
         "act": {"sub": delegator},              # the delegation chain (RFC 8693 style)
         "scope": " ".join(scope), "task_id": decl.task_id,
         "initiated_by": decl.initiated_by,      # human | schedule | agent
         "iat": now, "exp": now + ttl},
        BROKER_SECRET, algorithm="HS256")
    _audit("granted", task_id=decl.task_id, task_class=decl.task_class,
           delegator=delegator, agent=agent, scope=scope, ttl=ttl,
           initiated_by=decl.initiated_by)
    return {"access_token": token, "expires_in": ttl, "scope": scope}

@app.post("/grant")
def grant(decl: TaskDeclaration,
          authorization: str = Header(...),        # agent identity token
          x_delegation: str = Header(...)):        # delegating user's token
    agent = _validate_identity(authorization.removeprefix("Bearer "), "agent")
    delegator = _validate_identity(x_delegation, "user")

    d = evaluate(agent, delegator, decl.task_class)
    if d["decision"] == "deny":
        _audit("denied", task_id=decl.task_id, task_class=decl.task_class,
               delegator=delegator, agent=agent, reason=d["reason"])
        raise HTTPException(403, d["reason"])

    if d["approval_required"]:
        rid = str(uuid.uuid4())[:8]
        PENDING[rid] = {"agent": agent, "delegator": delegator,
                        "decl": decl, "scope": d["scope"], "ttl": d["ttl"]}
        _audit("pending_approval", grant_request_id=rid, task_id=decl.task_id,
               task_class=decl.task_class, delegator=delegator, agent=agent,
               scope=d["scope"])
        return {"status": "pending_approval", "grant_request_id": rid,
                "approver": delegator}

    return _mint(agent, delegator, decl, d["scope"], d["ttl"])

@app.post("/approve/{rid}")
def approve(rid: str, x_approver: str = Header(...)):
    approver = _validate_identity(x_approver, "user")
    ctx = PENDING.pop(rid, None)
    if ctx is None:
        raise HTTPException(404, "no such pending grant")
    if approver != ctx["delegator"]:
        PENDING[rid] = ctx
        raise HTTPException(403, "only the delegating human can approve")
    _audit("approved", grant_request_id=rid, approver=approver,
           task_id=ctx["decl"].task_id)
    return _mint(ctx["agent"], ctx["delegator"], ctx["decl"], ctx["scope"], ctx["ttl"])

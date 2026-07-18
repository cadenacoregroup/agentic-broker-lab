"""Mock ERP: the protected resource. Accepts ONLY broker-minted tokens —
never raw IdP tokens. Deliberately dumb: validate, check scope, serve fakes."""
import os, sys
import jwt
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.config import BROKER_SECRET, BROKER_ISSUER, ERP_AUDIENCE

app = FastAPI(title="Mock ERP")

def _require(token_header: str, needed_scope: str) -> dict:
    try:
        claims = jwt.decode(token_header.removeprefix("Bearer "), BROKER_SECRET,
                            algorithms=["HS256"], audience=ERP_AUDIENCE,
                            issuer=BROKER_ISSUER)
    except jwt.PyJWTError as e:
        raise HTTPException(401, f"invalid broker token: {e}")
    if needed_scope not in claims.get("scope", "").split():
        raise HTTPException(403, f"scope '{needed_scope}' not granted "
                                 f"(token has: '{claims.get('scope')}')")
    return claims

class LedgerEntry(BaseModel):
    account: str
    amount: float

@app.get("/invoices")
def invoices(quarter: str = "Q2", authorization: str = Header(...)):
    c = _require(authorization, "erp/invoices:read")
    return {"quarter": quarter,
            "invoices": [{"id": "INV-1001", "amount": 12500.00},
                         {"id": "INV-1002", "amount": 8300.50}],
            "served_to": {"agent": c["sub"], "on_behalf_of": c["act"]["sub"],
                          "task_id": c["task_id"]}}

@app.post("/ledger", status_code=201)
def ledger(entry: LedgerEntry, authorization: str = Header(...)):
    c = _require(authorization, "erp/ledger:post")
    return {"posted": entry.model_dump(),
            "by": {"agent": c["sub"], "on_behalf_of": c["act"]["sub"],
                   "task_id": c["task_id"]}}

@app.get("/payroll")
def payroll(authorization: str = Header(...)):
    _require(authorization, "erp/payroll:read")   # no task profile grants this
    return {"never": "reached"}

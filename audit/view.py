"""Render the audit log as human-readable attribution chains."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.config import AUDIT_LOG

ICONS = {"granted": "[GRANT]  ", "denied": "[DENY]   ",
         "pending_approval": "[PENDING]", "approved": "[APPROVE]"}
if not os.path.exists(AUDIT_LOG):
    sys.exit("no audit log yet — run the demo first")
for line in open(AUDIT_LOG):
    e = json.loads(line)
    icon = ICONS.get(e["event"], e["event"])
    if e["event"] == "denied":
        detail = f"reason: {e['reason']}"
    elif e["event"] == "approved":
        detail = f"by {e['approver']}"
    else:
        detail = f"scope={' '.join(e.get('scope', []))} ttl={e.get('ttl','-')}s"
    chain = f"{e.get('delegator','?')} -> {e.get('agent','?')}" \
        if e.get("agent") else ""
    prov = f" via:{e['initiated_by']}" if e.get("initiated_by") else ""
    print(f"{e['ts']}  {icon}  {e.get('task_class', e.get('task_id',''))}"
          f"{prov}  {chain}  {detail}")

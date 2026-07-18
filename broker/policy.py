"""Policy decision: effective grant = task profile ∩ agent ceiling ∩ delegator rights.
Intersection, never union — this is what prevents privilege amplification."""
import os, yaml

BASE = os.path.join(os.path.dirname(__file__), "..", "policy")

def _load(name):
    with open(os.path.join(BASE, name)) as f:
        return yaml.safe_load(f)

def evaluate(agent_id: str, delegator: str, task_class: str) -> dict:
    catalog = _load("task_catalog.yaml")["task_classes"]
    registry = _load("registry.yaml")

    profile = catalog.get(task_class)
    if profile is None:
        return {"decision": "deny", "reason": f"unknown task class '{task_class}'"}

    agent = registry["agents"].get(agent_id)
    if agent is None:
        return {"decision": "deny", "reason": f"agent '{agent_id}' not registered"}
    if task_class not in agent["allowed_task_classes"]:
        return {"decision": "deny",
                "reason": f"task class '{task_class}' outside agent ceiling"}

    user = registry["users"].get(delegator)
    if user is None:
        return {"decision": "deny", "reason": f"delegator '{delegator}' unknown"}

    effective = (set(profile["grants"])
                 & set(agent["resource_ceiling"])
                 & set(user["rights"]))
    if not effective:
        return {"decision": "deny",
                "reason": "empty intersection of task, agent ceiling, delegator rights"}

    return {"decision": "allow",
            "scope": sorted(effective),
            "ttl": profile["ttl_seconds"],
            "approval_required": profile["approval_required"]}

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from broker.policy import evaluate

def test_happy_path_intersection():
    d = evaluate("invoice-agent-01", "maria@cadenacore.dev", "invoice_analysis")
    assert d["decision"] == "allow"
    assert d["scope"] == ["erp/invoices:read"]
    assert d["approval_required"] is False

def test_unknown_task_class_denied():
    d = evaluate("invoice-agent-01", "maria@cadenacore.dev", "payroll_review")
    assert d["decision"] == "deny"

def test_delegator_without_right_gets_empty_intersection():
    d = evaluate("invoice-agent-01", "intern@cadenacore.dev", "ledger_posting")
    assert d["decision"] == "deny"
    assert "intersection" in d["reason"]

def test_irreversible_verb_requires_approval():
    d = evaluate("invoice-agent-01", "maria@cadenacore.dev", "ledger_posting")
    assert d["decision"] == "allow"
    assert d["approval_required"] is True


def test_initiation_provenance_is_policy_visible():
    # provenance doesn't change the intersection today, but it must be
    # available for risk-tiering (e.g., scheduled irreversible verbs)
    d = evaluate("invoice-agent-01", "maria@cadenacore.dev", "invoice_analysis")
    assert d["decision"] == "allow"  # placeholder: provenance rules land in Phase 2

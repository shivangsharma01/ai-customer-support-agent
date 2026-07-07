"""Verification script for the refund agent.

  python verify_agent.py --unit   # deterministic policy engine only (no LLM)
  python verify_agent.py          # full graph, end to end (needs Ollama + seeded DB)
"""

import sys
import uuid

from graph.nodes import _validate

UNIT_CASES = [
    # (description, customer, order, items, age, expected_verdict)
    ("approve in window",
     {"customer_tier": "standard", "fraud_score": 0.1, "refunds_last_12_months": 0},
     {"order_status": "delivered", "total_amount": 1499},
     [{"category": "apparel", "opened": False, "damaged": False, "is_non_refundable": False, "return_window_days": 30}],
     10, "approved"),
    ("deny outside window",
     {"customer_tier": "gold", "fraud_score": 0.02, "refunds_last_12_months": 0},
     {"order_status": "delivered", "total_amount": 5499},
     [{"category": "apparel", "opened": True, "damaged": False, "is_non_refundable": False, "return_window_days": 30}],
     40, "denied"),
    ("vip override rescues window denial",
     {"customer_tier": "vip", "fraud_score": 0.05, "refunds_last_12_months": 0, "vip_override_used": False},
     {"order_status": "delivered", "total_amount": 6999},
     [{"category": "apparel", "opened": False, "damaged": False, "is_non_refundable": False, "return_window_days": 30}],
     35, "approved"),
    ("vip override already used",
     {"customer_tier": "vip", "fraud_score": 0.05, "refunds_last_12_months": 1, "vip_override_used": True},
     {"order_status": "delivered", "total_amount": 6999},
     [{"category": "apparel", "opened": False, "damaged": False, "is_non_refundable": False, "return_window_days": 30}],
     35, "denied"),
    ("escalate high value",
     {"customer_tier": "gold", "fraud_score": 0.08, "refunds_last_12_months": 1},
     {"order_status": "delivered", "total_amount": 82000},
     [{"category": "electronics", "opened": False, "damaged": False, "is_non_refundable": False, "return_window_days": 30}],
     5, "escalated"),
    ("deny refund limit",
     {"customer_tier": "standard", "fraud_score": 0.35, "refunds_last_12_months": 2},
     {"order_status": "delivered", "total_amount": 2999},
     [{"category": "apparel", "opened": False, "damaged": False, "is_non_refundable": False, "return_window_days": 30}],
     8, "denied"),
    ("escalate fraud",
     {"customer_tier": "standard", "fraud_score": 0.85, "refunds_last_12_months": 1},
     {"order_status": "delivered", "total_amount": 3999},
     [{"category": "home", "opened": False, "damaged": False, "is_non_refundable": False, "return_window_days": 30}],
     6, "escalated"),
    ("deny opened electronics",
     {"customer_tier": "standard", "fraud_score": 0.1, "refunds_last_12_months": 0},
     {"order_status": "delivered", "total_amount": 7999},
     [{"category": "electronics", "opened": True, "damaged": False, "is_non_refundable": False, "return_window_days": 15}],
     9, "denied"),
    ("deny digital",
     {"customer_tier": "standard", "fraud_score": 0.1, "refunds_last_12_months": 0},
     {"order_status": "delivered", "total_amount": 12999},
     [{"category": "digital", "opened": False, "damaged": False, "is_non_refundable": True, "return_window_days": 0}],
     3, "denied"),
    ("approve damaged",
     {"customer_tier": "standard", "fraud_score": 0.1, "refunds_last_12_months": 0},
     {"order_status": "delivered", "total_amount": 4999},
     [{"category": "home", "opened": True, "damaged": True, "is_non_refundable": False, "return_window_days": 30}],
     4, "approved"),
]

E2E_CASES = [
    # (customer_id, order_id, message, expected_decision)
    ("CUST-006", "ORD-1001", "Hi, I'd like a refund for order ORD-1001, the t-shirt doesn't fit.", "approved"),
    ("CUST-004", "ORD-1002", "Please refund order ORD-1002, I don't like the shoes anymore.", "denied"),
    ("CUST-005", "ORD-1004", "I want to return my laptop, order ORD-1004. It's slower than expected.", "escalated"),
]


def run_unit() -> bool:
    ok = True
    for desc, cust, order, items, age, expected in UNIT_CASES:
        verdict, reason, rules, _ = _validate(cust, order, items, age)
        status = "PASS" if verdict == expected else "FAIL"
        ok &= verdict == expected
        print(f"[{status}] {desc}: {verdict} ({', '.join(rules) or 'no rules'})")
    return ok


def run_e2e() -> bool:
    from services.agent import run_turn
    ok = True
    for customer_id, order_id, message, expected in E2E_CASES:
        session = f"verify-{uuid.uuid4().hex[:8]}"
        view = run_turn(session, customer_id, message)
        got = view.get("final_decision")
        status = "PASS" if got == expected else "FAIL"
        ok &= got == expected
        print(f"[{status}] {customer_id}/{order_id}: expected={expected} got={got}")
        print(f"        rules={view.get('policy_rules_triggered')} tools={view.get('tools_called')}")
        print(f"        reply: {view.get('response', '')[:160]}")
    return ok


if __name__ == "__main__":
    passed = run_unit() if "--unit" in sys.argv else run_unit() and run_e2e()
    sys.exit(0 if passed else 1)

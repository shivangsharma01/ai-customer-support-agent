"""Agent tools. Everything returned here is fed to the LLM (and therefore may
appear in traces), so outputs are sanitized: no names, emails, phones,
addresses, or raw fraud scores. Full rows live only in the graph's private state.
"""

from datetime import date

from langchain_core.tools import tool
from sqlalchemy import select

from models.db import Customer, HistoricalCase, Order, OrderItem, PolicyChunk, Product
from services.database import get_session
from services.embeddings import embed_one

FRAUD_THRESHOLD = 0.7


@tool
def get_customer(customer_id: str) -> dict:
    """Look up the customer's account profile: tier, account age, refund usage."""
    with get_session() as s:
        c = s.get(Customer, customer_id)
        if c is None:
            return {"error": "customer not found"}
        return {
            "customer_id": c.customer_id,
            "customer_tier": c.customer_tier,
            "account_age_days": (date.today() - c.account_created_at).days,
            "refunds_last_12_months": c.refunds_last_12_months,
            "vip_override_available": c.customer_tier == "vip" and not c.vip_override_used,
            "fraud_flag": float(c.fraud_score) >= FRAUD_THRESHOLD,
        }


@tool
def get_order(order_id: str) -> dict:
    """Look up an order: status, dates, amount, and the items in it."""
    with get_session() as s:
        o = s.get(Order, order_id)
        if o is None:
            return {"error": "order not found"}
        items = s.execute(
            select(OrderItem, Product).join(Product, OrderItem.product_id == Product.product_id)
            .where(OrderItem.order_id == order_id)
        ).all()
        return {
            "order_id": o.order_id,
            "order_status": o.order_status,
            "purchase_date": str(o.purchase_date),
            "delivery_date": str(o.delivery_date) if o.delivery_date else None,
            "order_age_days": (date.today() - o.delivery_date).days if o.delivery_date else None,
            "total_amount": float(o.total_amount),
            "items": [
                {
                    "product_name": p.product_name,
                    "category": p.category,
                    "price": float(p.price),
                    "quantity": i.quantity,
                    "opened": i.opened,
                    "damaged": i.damaged,
                    "return_window_days": p.return_window_days,
                    "is_non_refundable": p.is_non_refundable,
                }
                for i, p in items
            ],
        }


@tool
def get_refund_count(customer_id: str) -> dict:
    """Return how many refunds this customer received in the last 12 months."""
    with get_session() as s:
        c = s.get(Customer, customer_id)
        if c is None:
            return {"error": "customer not found"}
        return {"refunds_last_12_months": c.refunds_last_12_months, "limit": 2}


@tool
def get_vip_status(customer_id: str) -> dict:
    """Check whether the customer is VIP and whether their annual manual override is still available."""
    with get_session() as s:
        c = s.get(Customer, customer_id)
        if c is None:
            return {"error": "customer not found"}
        return {
            "is_vip": c.customer_tier == "vip",
            "vip_override_available": c.customer_tier == "vip" and not c.vip_override_used,
        }


@tool
def retrieve_policy(query: str) -> list[dict]:
    """Semantic search over the refund policy. Returns the most relevant policy sections."""
    vec = embed_one(query)
    with get_session() as s:
        chunks = s.scalars(
            select(PolicyChunk).order_by(PolicyChunk.embedding.cosine_distance(vec)).limit(3)
        ).all()
        return [{"content": c.content} for c in chunks]


@tool
def retrieve_similar_cases(query: str) -> list[dict]:
    """Retrieve past refund decisions similar to the current scenario (precedents)."""
    vec = embed_one(query)
    with get_session() as s:
        cases = s.scalars(
            select(HistoricalCase).order_by(HistoricalCase.embedding.cosine_distance(vec)).limit(3)
        ).all()
        return [
            {"scenario": c.scenario, "decision": c.decision, "policy_triggered": c.policy_triggered}
            for c in cases
        ]


@tool
def escalate_to_human(reason: str) -> dict:
    """Escalate this refund request to a human reviewer. Use when policy requires manual review."""
    return {"status": "escalation_ticket_created", "reason": reason}


ALL_TOOLS = [
    get_customer,
    get_order,
    get_refund_count,
    get_vip_status,
    retrieve_policy,
    retrieve_similar_cases,
    escalate_to_human,
]
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}

"""Seed the CRM database with a deterministic synthetic dataset.

Run from the repo root:  python data/seed_customers.py
Requires Postgres (DATABASE_URL) and the embedding endpoint (Ollama/vLLM) running.
"""

import json
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import text

from models.db import Customer, HistoricalCase, Order, OrderItem, PolicyChunk, Product, RefundRequest
from services.database import engine, get_session, init_db
from services.embeddings import embed

TODAY = date.today()
DATA_DIR = Path(__file__).resolve().parent

def d(days_ago: int) -> date:
    return TODAY - timedelta(days=days_ago)

# --- 15 customers: profiles required by the spec §6 ---
CUSTOMERS = [
    # VIP customer, override still available
    Customer(customer_id="CUST-001", name="Ananya Iyer", email="ananya.iyer@example.com",
             phone_number="+91-98100-11001", address="14 Marine Drive, Mumbai, MH",
             customer_tier="vip", account_created_at=d(1500), lifetime_value=485000,
             fraud_score=0.05, refunds_last_12_months=0, vip_override_used=False),
    # Repeat refund abuser — already at the 2-refund limit
    Customer(customer_id="CUST-002", name="Rohan Mehta", email="rohan.mehta@example.com",
             phone_number="+91-98100-11002", address="88 Koramangala, Bengaluru, KA",
             customer_tier="standard", account_created_at=d(700), lifetime_value=42000,
             fraud_score=0.35, refunds_last_12_months=2, vip_override_used=False),
    # Fraudulent customer
    Customer(customer_id="CUST-003", name="Vikram Shah", email="vikram.shah@example.com",
             phone_number="+91-98100-11003", address="3 Ring Road, Delhi, DL",
             customer_tier="standard", account_created_at=d(200), lifetime_value=18000,
             fraud_score=0.85, refunds_last_12_months=1, vip_override_used=False),
    # Loyal customer
    Customer(customer_id="CUST-004", name="Priya Nair", email="priya.nair@example.com",
             phone_number="+91-98100-11004", address="21 MG Road, Kochi, KL",
             customer_tier="gold", account_created_at=d(1900), lifetime_value=210000,
             fraud_score=0.02, refunds_last_12_months=0, vip_override_used=False),
    # High lifetime value customer
    Customer(customer_id="CUST-005", name="Arjun Kapoor", email="arjun.kapoor@example.com",
             phone_number="+91-98100-11005", address="7 Banjara Hills, Hyderabad, TS",
             customer_tier="gold", account_created_at=d(1100), lifetime_value=390000,
             fraud_score=0.08, refunds_last_12_months=1, vip_override_used=False),
    # First-time customer
    Customer(customer_id="CUST-006", name="Sneha Reddy", email="sneha.reddy@example.com",
             phone_number="+91-98100-11006", address="45 Jubilee Hills, Hyderabad, TS",
             customer_tier="standard", account_created_at=d(20), lifetime_value=1499,
             fraud_score=0.10, refunds_last_12_months=0, vip_override_used=False),
    # VIP who already used their annual override
    Customer(customer_id="CUST-007", name="Kabir Malhotra", email="kabir.m@example.com",
             phone_number="+91-98100-11007", address="12 Golf Links, Delhi, DL",
             customer_tier="vip", account_created_at=d(2200), lifetime_value=620000,
             fraud_score=0.04, refunds_last_12_months=1, vip_override_used=True),
]
_rng = random.Random(42)
_names = ["Isha Verma", "Aditya Rao", "Meera Pillai", "Farhan Khan", "Divya Menon",
          "Nikhil Joshi", "Tanvi Desai", "Sameer Kulkarni"]
for i, name in enumerate(_names, start=8):
    first = name.split()[0].lower()
    CUSTOMERS.append(Customer(
        customer_id=f"CUST-{i:03d}", name=name, email=f"{first}@example.com",
        phone_number=f"+91-98100-11{i:03d}", address=f"{i} Park Street, Pune, MH",
        customer_tier=_rng.choice(["standard", "standard", "gold"]),
        account_created_at=d(_rng.randint(60, 1400)),
        lifetime_value=_rng.randint(5000, 150000),
        fraud_score=round(_rng.uniform(0.01, 0.3), 2),
        refunds_last_12_months=_rng.choice([0, 0, 1]),
        vip_override_used=False))

# --- 20 products ---
PRODUCTS = [
    Product(product_id="PROD-001", product_name="NovaBook Pro 14 Laptop", category="electronics", price=82000, return_window_days=30),
    Product(product_id="PROD-002", product_name="Pixelon X2 Smartphone", category="electronics", price=54999, return_window_days=30),
    Product(product_id="PROD-003", product_name="AirBeat Wireless Earbuds", category="electronics", price=7999, return_window_days=15),
    Product(product_id="PROD-004", product_name="UltraView 27\" Monitor", category="electronics", price=21500, return_window_days=30),
    Product(product_id="PROD-005", product_name="MechType K87 Keyboard", category="electronics", price=6499, return_window_days=30),
    Product(product_id="PROD-006", product_name="SoundBar Home Theatre", category="electronics", price=32000, return_window_days=30),
    Product(product_id="PROD-007", product_name="ProOffice Suite License", category="digital", price=12999, return_window_days=0, is_non_refundable=True),
    Product(product_id="PROD-008", product_name="GameZone Gift Card ₹5000", category="digital", price=5000, return_window_days=0, is_non_refundable=True),
    Product(product_id="PROD-009", product_name="CloudDrive 2TB Annual Plan", category="digital", price=8400, return_window_days=0, is_non_refundable=True),
    Product(product_id="PROD-010", product_name="Classic Cotton T-Shirt", category="apparel", price=1499, return_window_days=30),
    Product(product_id="PROD-011", product_name="Denim Slim-Fit Jeans", category="apparel", price=2999, return_window_days=30),
    Product(product_id="PROD-012", product_name="Trailblazer Running Shoes", category="apparel", price=5499, return_window_days=30),
    Product(product_id="PROD-013", product_name="Winter Puffer Jacket", category="apparel", price=6999, return_window_days=30),
    Product(product_id="PROD-014", product_name="Ceramic Dinner Set (24pc)", category="home", price=4999, return_window_days=30),
    Product(product_id="PROD-015", product_name="Aroma Drip Coffee Maker", category="home", price=3999, return_window_days=30),
    Product(product_id="PROD-016", product_name="Memory Foam Pillow Pair", category="home", price=2499, return_window_days=30),
    Product(product_id="PROD-017", product_name="Robo-Vac S6 Vacuum", category="electronics", price=28999, return_window_days=30),
    Product(product_id="PROD-018", product_name="Vitamin C Face Serum", category="beauty", price=899, return_window_days=15),
    Product(product_id="PROD-019", product_name="Herbal Hair Care Kit", category="beauty", price=1299, return_window_days=15),
    Product(product_id="PROD-020", product_name="Yoga Mat Pro 6mm", category="home", price=1799, return_window_days=30),
]

# --- Orders: 9 scripted demo orders + 41 filler = 50 ---
# (order, [(product_id, qty, opened, damaged), ...])
SCRIPTED_ORDERS = [
    # Approve: first-time customer, in window
    (Order(order_id="ORD-1001", customer_id="CUST-006", purchase_date=d(14), delivery_date=d(10),
           order_status="delivered", payment_method="upi", total_amount=1499),
     [("PROD-010", 1, False, False)]),
    # Deny: outside 30-day window
    (Order(order_id="ORD-1002", customer_id="CUST-004", purchase_date=d(45), delivery_date=d(40),
           order_status="delivered", payment_method="credit_card", total_amount=5499),
     [("PROD-012", 1, True, False)]),
    # VIP override: out of window but override available
    (Order(order_id="ORD-1003", customer_id="CUST-001", purchase_date=d(40), delivery_date=d(35),
           order_status="delivered", payment_method="credit_card", total_amount=6999),
     [("PROD-013", 1, False, False)]),
    # Escalate: high value > ₹50,000
    (Order(order_id="ORD-1004", customer_id="CUST-005", purchase_date=d(9), delivery_date=d(5),
           order_status="delivered", payment_method="credit_card", total_amount=82000),
     [("PROD-001", 1, False, False)]),
    # Deny: refund limit reached
    (Order(order_id="ORD-1005", customer_id="CUST-002", purchase_date=d(12), delivery_date=d(8),
           order_status="delivered", payment_method="upi", total_amount=2999),
     [("PROD-011", 1, False, False)]),
    # Escalate: fraud score
    (Order(order_id="ORD-1006", customer_id="CUST-003", purchase_date=d(10), delivery_date=d(6),
           order_status="delivered", payment_method="cod", total_amount=3999),
     [("PROD-015", 1, False, False)]),
    # Deny: opened electronics
    (Order(order_id="ORD-1007", customer_id="CUST-008", purchase_date=d(13), delivery_date=d(9),
           order_status="delivered", payment_method="upi", total_amount=7999),
     [("PROD-003", 1, True, False)]),
    # Deny: digital product
    (Order(order_id="ORD-1008", customer_id="CUST-009", purchase_date=d(3), delivery_date=d(3),
           order_status="delivered", payment_method="credit_card", total_amount=12999),
     [("PROD-007", 1, False, False)]),
    # Approve: damaged on arrival
    (Order(order_id="ORD-1009", customer_id="CUST-010", purchase_date=d(8), delivery_date=d(4),
           order_status="delivered", payment_method="upi", total_amount=4999),
     [("PROD-014", 1, True, True)]),
]

def build_filler_orders() -> list[tuple[Order, list[tuple[str, int, bool, bool]]]]:
    rng = random.Random(7)
    out = []
    refundable = [p for p in PRODUCTS if not p.is_non_refundable]
    for i in range(41):
        oid = f"ORD-{1010 + i}"
        cust = rng.choice(CUSTOMERS).customer_id
        purchase = rng.randint(5, 320)
        status = rng.choice(["delivered"] * 7 + ["shipped", "processing", "cancelled"])
        delivered = purchase - rng.randint(2, 4) if status == "delivered" else None
        prod = rng.choice(refundable)
        qty = rng.choice([1, 1, 2])
        order = Order(order_id=oid, customer_id=cust, purchase_date=d(purchase),
                      delivery_date=d(delivered) if delivered else None, order_status=status,
                      payment_method=rng.choice(["upi", "credit_card", "debit_card", "cod"]),
                      total_amount=float(prod.price) * qty)
        out.append((order, [(prod.product_id, qty, rng.random() < 0.3, rng.random() < 0.05)]))
    return out

# --- 25 historical refund requests (already decided) ---
def build_refund_requests(orders: list[Order]) -> list[RefundRequest]:
    rng = random.Random(11)
    decided = [
        ("denied", "Request made outside the 30-day refund window (Rule 1).", False),
        ("denied", "Opened electronics are non-refundable (Rule 2).", False),
        ("denied", "Customer exceeded two refunds in 12 months (Rule 3).", False),
        ("approved", "Within refund window and all policy checks passed.", False),
        ("approved", "Item damaged on arrival; refund issued under Rule 7.", False),
        ("escalated", "Order value exceeds ₹50,000; manual review required (Rule 5).", True),
        ("escalated", "High fraud risk score; escalated under Rule 8.", True),
    ]
    reasons = ["Item did not match description", "Changed my mind", "Product stopped working",
               "Wrong size delivered", "Arrived damaged", "Found a better price", "No longer needed"]
    delivered_orders = [o for o in orders if o.order_status == "delivered"]
    out = []
    for i in range(25):
        order = rng.choice(delivered_orders)
        decision, reason, escalated = rng.choice(decided)
        days_ago = rng.randint(10, 300)
        out.append(RefundRequest(
            refund_id=f"REF-{2001 + i}", customer_id=order.customer_id, order_id=order.order_id,
            request_reason=rng.choice(reasons),
            request_date=datetime.combine(d(days_ago), datetime.min.time()),
            final_decision=decision, decision_reason=reason, escalation_required=escalated))
    return out


def chunk_policy() -> list[str]:
    md = (DATA_DIR / "refund_policy.md").read_text()
    chunks = ["## " + c.strip() for c in md.split("## ") if c.strip() and not c.startswith("# ")]
    return chunks


def main() -> None:
    init_db()
    with engine.connect() as conn:
        for table in ["refund_requests", "order_items", "orders", "products",
                      "customers", "historical_cases", "policy_chunks"]:
            conn.execute(text(f"TRUNCATE {table} CASCADE"))
        conn.commit()

    session = get_session()
    all_orders = SCRIPTED_ORDERS + build_filler_orders()
    session.add_all(CUSTOMERS)
    session.add_all(PRODUCTS)
    session.add_all([o for o, _ in all_orders])
    session.flush()
    for order, items in all_orders:
        for pid, qty, opened, damaged in items:
            session.add(OrderItem(order_id=order.order_id, product_id=pid,
                                  quantity=qty, opened=opened, damaged=damaged))
    session.add_all(build_refund_requests([o for o, _ in all_orders]))

    chunks = chunk_policy()
    for content, vec in zip(chunks, embed(chunks)):
        session.add(PolicyChunk(content=content, embedding=vec))

    cases = json.loads((DATA_DIR / "historical_cases.json").read_text())
    vecs = embed([c["scenario"] for c in cases])
    for case, vec in zip(cases, vecs):
        session.add(HistoricalCase(case_id=case["case_id"], scenario=case["scenario"],
                                   decision=case["decision"],
                                   policy_triggered=case["policy_triggered"], embedding=vec))
    session.commit()

    for table in ["customers", "orders", "products", "order_items",
                  "refund_requests", "historical_cases", "policy_chunks"]:
        n = session.execute(text(f"SELECT count(*) FROM {table}")).scalar()
        print(f"{table}: {n}")
    session.close()


if __name__ == "__main__":
    main()

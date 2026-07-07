from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import settings


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    phone_number: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String)
    customer_tier: Mapped[str] = mapped_column(String)  # standard | gold | vip
    account_created_at: Mapped[date] = mapped_column(Date)
    lifetime_value: Mapped[float] = mapped_column(Numeric(12, 2))
    fraud_score: Mapped[float] = mapped_column(Numeric(3, 2))  # 0.00–1.00
    refunds_last_12_months: Mapped[int] = mapped_column(Integer)
    vip_override_used: Mapped[bool] = mapped_column(Boolean, default=False)


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"))
    purchase_date: Mapped[date] = mapped_column(Date)
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    order_status: Mapped[str] = mapped_column(String)  # delivered | shipped | processing | cancelled
    payment_method: Mapped[str] = mapped_column(String)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2))


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String, primary_key=True)
    product_name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)  # electronics | apparel | home | digital | beauty
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    return_window_days: Mapped[int] = mapped_column(Integer)
    is_non_refundable: Mapped[bool] = mapped_column(Boolean, default=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    opened: Mapped[bool] = mapped_column(Boolean, default=False)
    damaged: Mapped[bool] = mapped_column(Boolean, default=False)


class RefundRequest(Base):
    __tablename__ = "refund_requests"

    refund_id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"))
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"))
    request_reason: Mapped[str] = mapped_column(Text)
    request_date: Mapped[datetime] = mapped_column(DateTime)
    final_decision: Mapped[str | None] = mapped_column(String, nullable=True)  # approved | denied | escalated
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalation_required: Mapped[bool] = mapped_column(Boolean, default=False)


class HistoricalCase(Base):
    __tablename__ = "historical_cases"

    case_id: Mapped[str] = mapped_column(String, primary_key=True)
    scenario: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String)
    policy_triggered: Mapped[str] = mapped_column(String)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))


class PolicyChunk(Base):
    __tablename__ = "policy_chunks"

    chunk_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))

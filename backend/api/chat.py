import uuid

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from models.db import Customer
from services.agent import run_turn
from services.database import get_session

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str
    customer_id: str
    session_id: str | None = None


@router.post("/chat")
def chat(req: ChatRequest) -> dict:
    session_id = req.session_id or f"sess-{uuid.uuid4().hex[:12]}"
    view = run_turn(session_id, req.customer_id, req.message)
    return {"session_id": session_id, **view}


@router.get("/demo/customers")
def demo_customers() -> list[dict]:
    """Demo identity picker (stands in for auth). Exposes only opaque ids and tier — no PII."""
    with get_session() as s:
        rows = s.scalars(select(Customer).order_by(Customer.customer_id)).all()
        return [{"customer_id": c.customer_id, "customer_tier": c.customer_tier} for c in rows]

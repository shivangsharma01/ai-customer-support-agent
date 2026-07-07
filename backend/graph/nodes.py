import json
import re
import time
import uuid
from datetime import date, datetime
from functools import wraps
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel

from graph.state import AgentState, public_view
from models.db import Customer, Order, OrderItem, Product, RefundRequest
from prompts.system import ASK_ORDER_ID_PROMPT, DECISION_PROMPT, INTENT_PROMPT, RESPONSE_PROMPT
from services.database import get_session
from services.events import bus
from services.llm import get_llm
from tools.refund_tools import FRAUD_THRESHOLD, TOOLS_BY_NAME, ALL_TOOLS, retrieve_policy, retrieve_similar_cases

MAX_TOOL_ROUNDS = 3
HIGH_VALUE_LIMIT = 50000
REFUND_LIMIT = 2


def traced(name: str):
    def deco(fn):
        @wraps(fn)
        def wrapper(state: AgentState) -> dict:
            sid = state["session_id"]
            bus.emit(sid, "node_started", {"node": name})
            t0 = time.perf_counter()
            update = fn(state)
            latency = round((time.perf_counter() - t0) * 1000, 1)
            bus.emit(sid, "node_completed", {
                "node": name,
                "latency_ms": latency,
                "state": public_view({**state, **update}),
            })
            return update
        return wrapper
    return deco


def _extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in response")
    return json.loads(text[start:end + 1])


def _call_json(messages, model_cls, session_id: str, step: str, attempts: int = 3):
    """Invoke the LLM expecting a JSON reply; retry with an explicit reminder on failure."""
    llm = get_llm()
    last_err = None
    for attempt in range(1, attempts + 1):
        try:
            raw = llm.invoke(messages).content
            return model_cls.model_validate(_extract_json(raw))
        except Exception as e:  # noqa: BLE001 — any parse/validation failure triggers a retry
            last_err = e
            bus.emit(session_id, "retry", {"step": step, "attempt": attempt, "error": str(e)[:200]})
            messages = list(messages) + [HumanMessage(
                content="Your last reply was not valid JSON. Reply with ONLY the JSON object.")]
    raise RuntimeError(f"{step} failed after {attempts} attempts: {last_err}")


# ---------------------------------------------------------------- intent

class IntentOut(BaseModel):
    intent: Literal["refund_request", "order_question", "general"] = "general"
    order_id: str | None = None
    reason: str | None = None


@traced("extract_intent")
def extract_intent(state: AgentState) -> dict:
    recent = [m for m in state["messages"] if isinstance(m, HumanMessage)][-3:]
    convo = "\n".join(m.content for m in recent)
    sys = INTENT_PROMPT.format(known_order_id=state.get("order_id") or "none")
    try:
        out = _call_json(
            [SystemMessage(content=sys), HumanMessage(content=convo)],
            IntentOut, state["session_id"], "extract_intent",
        )
    except RuntimeError:
        out = IntentOut()
    # Regex backstop: a 3B model occasionally drops the order id.
    if not out.order_id:
        m = re.search(r"ORD-\d+", convo, re.IGNORECASE)
        out.order_id = m.group(0).upper() if m else None
    return {
        "intent": out.intent,
        "order_id": out.order_id or state.get("order_id"),
        "private": {**state.get("private", {}), "request_reason": out.reason},
        # reset per-turn fields
        "policy_rules_triggered": [],
        "tools_called": [],
        "final_decision": None,
        "decision_reason": None,
        "tool_rounds": 0,
    }


# ---------------------------------------------------------------- retrieval

@traced("retrieve_customer")
def retrieve_customer(state: AgentState) -> dict:
    with get_session() as s:
        c = s.get(Customer, state["customer_id"])
    if c is None:
        return {"customer_tier": "unknown"}
    private = {**state.get("private", {}), "customer": {
        "customer_id": c.customer_id,
        "name": c.name,
        "email": c.email,
        "phone_number": c.phone_number,
        "address": c.address,
        "customer_tier": c.customer_tier,
        "account_created_at": str(c.account_created_at),
        "lifetime_value": float(c.lifetime_value),
        "fraud_score": float(c.fraud_score),
        "refunds_last_12_months": c.refunds_last_12_months,
        "vip_override_used": c.vip_override_used,
    }}
    return {"customer_tier": c.customer_tier, "private": private}


@traced("retrieve_order")
def retrieve_order(state: AgentState) -> dict:
    order_id = state.get("order_id")
    if not order_id:
        return {}
    with get_session() as s:
        o = s.get(Order, order_id)
        if o is None or o.customer_id != state["customer_id"]:
            return {"order_id": None}
        rows = s.execute(
            OrderItem.__table__.join(Product.__table__).select().where(OrderItem.order_id == order_id)
        ).mappings().all()
    age = (date.today() - o.delivery_date).days if o.delivery_date else None
    private = {**state.get("private", {}),
               "order": {
                   "order_id": o.order_id,
                   "order_status": o.order_status,
                   "purchase_date": str(o.purchase_date),
                   "delivery_date": str(o.delivery_date) if o.delivery_date else None,
                   "payment_method": o.payment_method,
                   "total_amount": float(o.total_amount),
               },
               "items": [{
                   "product_name": r["product_name"],
                   "category": r["category"],
                   "price": float(r["price"]),
                   "quantity": r["quantity"],
                   "opened": r["opened"],
                   "damaged": r["damaged"],
                   "return_window_days": r["return_window_days"],
                   "is_non_refundable": r["is_non_refundable"],
               } for r in rows]}
    return {"order_age_days": age, "private": private}


def _run_retrieval_tool(state: AgentState, tool, query: str, key: str) -> dict:
    t0 = time.perf_counter()
    result = tool.func(query=query)
    bus.emit(state["session_id"], "tool_called", {
        "tool": tool.name, "query": query,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        "result_count": len(result),
    })
    return {
        "tools_called": state.get("tools_called", []) + [tool.name],
        "private": {**state.get("private", {}), key: result},
    }


def _retrieval_query(state: AgentState) -> str:
    priv = state.get("private", {})
    reason = priv.get("request_reason") or "refund request"
    items = priv.get("items", [])
    cats = ", ".join({i["category"] for i in items}) or "unknown category"
    age = state.get("order_age_days")
    flags = [f for i in items for f in (["opened"] if i["opened"] else []) + (["damaged"] if i["damaged"] else [])]
    return f"Refund request: {reason}. Items: {cats} {' '.join(set(flags))}. Delivered {age} days ago."


@traced("retrieve_policy")
def retrieve_policy_node(state: AgentState) -> dict:
    return _run_retrieval_tool(state, retrieve_policy, _retrieval_query(state), "policy_chunks")


@traced("retrieve_similar_cases")
def retrieve_similar_cases_node(state: AgentState) -> dict:
    return _run_retrieval_tool(state, retrieve_similar_cases, _retrieval_query(state), "similar_cases")


# ---------------------------------------------------------------- decision

class DecisionOut(BaseModel):
    decision: Literal["approved", "denied", "escalated"]
    reason: str
    rules_triggered: list[str] = []


def _decision_context(state: AgentState) -> str:
    priv = state.get("private", {})
    cust = priv.get("customer", {})
    context = {
        "customer_id": state["customer_id"],
        "customer_tier": cust.get("customer_tier"),
        "refunds_last_12_months": cust.get("refunds_last_12_months"),
        "vip_override_available": cust.get("customer_tier") == "vip" and not cust.get("vip_override_used"),
        "fraud_flag": (cust.get("fraud_score") or 0) >= FRAUD_THRESHOLD,
        "request_reason": priv.get("request_reason"),
        "order": priv.get("order"),
        "items": priv.get("items"),
        "order_age_days": state.get("order_age_days"),
    }
    return json.dumps(context, indent=2)


@traced("decision")
def decision(state: AgentState) -> dict:
    priv = state.get("private", {})
    policy = "\n\n".join(c["content"] for c in priv.get("policy_chunks", []))
    cases = "\n".join(
        f"- {c['scenario']} → {c['decision']} ({c['policy_triggered']})"
        for c in priv.get("similar_cases", [])
    )
    sys = SystemMessage(content=DECISION_PROMPT.format(
        context=_decision_context(state), policy=policy, cases=cases))
    convo = [m for m in state["messages"] if isinstance(m, (HumanMessage, AIMessage, ToolMessage))]

    rounds = state.get("tool_rounds", 0)
    llm = get_llm()
    use_tools = rounds < MAX_TOOL_ROUNDS
    model = llm.bind_tools(ALL_TOOLS) if use_tools else llm
    ai_msg = model.invoke([sys] + convo)

    if getattr(ai_msg, "tool_calls", None):
        return {"messages": [ai_msg]}

    try:
        out = DecisionOut.model_validate(_extract_json(ai_msg.content))
    except Exception:
        try:
            out = _call_json([sys] + convo + [HumanMessage(
                content="Reply with ONLY the decision JSON object now.")],
                DecisionOut, state["session_id"], "decision", attempts=2)
        except RuntimeError:
            out = DecisionOut(decision="escalated",
                              reason="Automated decision was unreliable; escalating for manual review.")
    return {
        "messages": [ai_msg],
        "final_decision": out.decision,
        "decision_reason": out.reason,
        "policy_rules_triggered": out.rules_triggered,
    }


@traced("tools")
def tool_node(state: AgentState) -> dict:
    last = state["messages"][-1]
    tool_msgs, called = [], []
    update: dict = {}
    for call in last.tool_calls:
        tool = TOOLS_BY_NAME.get(call["name"])
        t0 = time.perf_counter()
        try:
            result = tool.invoke(call["args"]) if tool else {"error": f"unknown tool {call['name']}"}
        except Exception as e:  # noqa: BLE001 — surface tool failure to the LLM, don't crash the graph
            result = {"error": str(e)[:200]}
        latency = round((time.perf_counter() - t0) * 1000, 1)
        bus.emit(state["session_id"], "tool_called", {
            "tool": call["name"], "args": call["args"], "latency_ms": latency,
        })
        if call["name"] == "escalate_to_human":
            bus.emit(state["session_id"], "escalation", {"reason": call["args"].get("reason", "")})
        called.append(call["name"])
        tool_msgs.append(ToolMessage(content=json.dumps(result), tool_call_id=call["id"]))
    raw = {**state.get("private", {}).get("tool_outputs", {}),
           **{c["name"]: json.loads(m.content) for c, m in zip(last.tool_calls, tool_msgs)}}
    update.update({
        "messages": tool_msgs,
        "tools_called": state.get("tools_called", []) + called,
        "tool_rounds": state.get("tool_rounds", 0) + 1,
        "private": {**state.get("private", {}), "tool_outputs": raw},
    })
    return update


# ---------------------------------------------------------------- validation

def _validate(cust: dict, order: dict, items: list[dict], age: int | None) -> tuple[str, str, list[str], bool]:
    """Deterministic policy engine. Returns (verdict, reason, rules, used_vip_override).

    The LLM proposes; this code disposes. Every check uses DB facts only.
    """
    if not order or order.get("order_status") != "delivered":
        return "denied", "The order has not been delivered, so it is not eligible for a refund.", [], False
    if (cust.get("fraud_score") or 0) >= FRAUD_THRESHOLD:
        return ("escalated", "Account flagged for fraud risk; manual review required.",
                ["Rule 8: Fraud Check"], False)
    if order["total_amount"] > HIGH_VALUE_LIMIT:
        return ("escalated", f"Order value exceeds ₹{HIGH_VALUE_LIMIT:,}; manual review required.",
                ["Rule 5: High-Value Manual Review"], False)
    if any(i["is_non_refundable"] or i["category"] == "digital" for i in items):
        return "denied", "Digital products are non-refundable once delivered.", ["Rule 6: Digital Products"], False

    damaged = any(i["damaged"] for i in items)
    window = min((i["return_window_days"] for i in items), default=30)
    in_window = age is not None and age <= window

    if damaged and in_window:
        return ("approved", "Item damaged on arrival; refund approved within the return window.",
                ["Rule 7: Damaged Items"], False)

    denial_rules: list[str] = []
    reasons: list[str] = []
    if any(i["opened"] and i["category"] == "electronics" for i in items) and not damaged:
        return "denied", "Opened electronics are non-refundable.", ["Rule 2: Opened Electronics"], False
    if not in_window:
        denial_rules.append("Rule 1: Refund Window")
        reasons.append(f"the request is outside the {window}-day refund window (delivered {age} days ago)")
    if (cust.get("refunds_last_12_months") or 0) >= REFUND_LIMIT:
        denial_rules.append("Rule 3: Refund Frequency Limit")
        reasons.append("the two-refunds-per-12-months limit has been reached")

    if denial_rules:
        vip_eligible = (cust.get("customer_tier") == "vip" and not cust.get("vip_override_used"))
        if vip_eligible:
            return ("approved", "Approved via the VIP annual manual override.",
                    denial_rules + ["Rule 4: VIP Manual Override"], True)
        return "denied", f"Denied because {' and '.join(reasons)}.", denial_rules, False

    return "approved", "All policy checks passed; refund approved.", [], False


@traced("policy_validation")
def policy_validation(state: AgentState) -> dict:
    priv = state.get("private", {})
    cust, order, items = priv.get("customer", {}), priv.get("order", {}), priv.get("items", [])
    verdict, reason, rules, used_override = _validate(cust, order, items, state.get("order_age_days"))

    llm_decision = state.get("final_decision")
    if llm_decision and llm_decision != verdict:
        bus.emit(state["session_id"], "decision_overridden", {
            "llm_decision": llm_decision, "validated_decision": verdict, "rules": rules,
        })
    if verdict == "escalated":
        bus.emit(state["session_id"], "escalation", {"reason": reason})

    with get_session() as s:
        s.add(RefundRequest(
            refund_id=f"REF-{uuid.uuid4().hex[:8].upper()}",
            customer_id=state["customer_id"],
            order_id=order.get("order_id", state.get("order_id") or "unknown"),
            request_reason=priv.get("request_reason") or "not stated",
            request_date=datetime.now(),
            final_decision=verdict,
            decision_reason=reason,
            escalation_required=verdict == "escalated",
        ))
        if used_override:
            c = s.get(Customer, state["customer_id"])
            c.vip_override_used = True
        s.commit()

    return {"final_decision": verdict, "decision_reason": reason, "policy_rules_triggered": rules}


# ---------------------------------------------------------------- response

@traced("generate_response")
def generate_response(state: AgentState) -> dict:
    llm = get_llm(temperature=0.4)
    if state.get("final_decision"):
        prompt = RESPONSE_PROMPT.format(
            decision=state["final_decision"],
            reason=state.get("decision_reason", ""),
            rules=", ".join(state.get("policy_rules_triggered", [])) or "none",
        )
    else:
        last_human = next((m.content for m in reversed(state["messages"])
                           if isinstance(m, HumanMessage)), "")
        prompt = ASK_ORDER_ID_PROMPT.format(message=last_human)
    reply = llm.invoke([HumanMessage(content=prompt)]).content.strip()
    return {"messages": [AIMessage(content=reply)], "response": reply}


# ---------------------------------------------------------------- routing

def route_after_intent(state: AgentState) -> str:
    return "retrieve_customer" if state.get("intent") == "refund_request" else "generate_response"


def route_after_order(state: AgentState) -> str:
    return "retrieve_policy" if state.get("order_id") and state.get("private", {}).get("order") \
        else "generate_response"


def route_after_decision(state: AgentState) -> str:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "policy_validation"

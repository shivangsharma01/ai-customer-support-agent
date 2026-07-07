"""Agent state, split per the design doc:

- shared:  ids used to drive graph execution (opaque, safe to expose)
- public:  visible to the frontend, admin dashboard, and LangFuse
- private: never leaves the backend (PII, fraud score, raw tool outputs)

The privacy boundary is `public_view()`: every trace event and API response is
built from it, and it never touches the `private` key.
"""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    # -- shared --
    session_id: str
    customer_id: str
    order_id: str | None
    # -- public --
    messages: Annotated[list, add_messages]
    intent: str
    order_age_days: int | None
    customer_tier: str
    policy_rules_triggered: list[str]
    tools_called: list[str]
    final_decision: str | None
    decision_reason: str | None
    response: str
    tool_rounds: int
    # -- private --
    private: dict[str, Any]


PUBLIC_FIELDS = (
    "session_id",
    "customer_id",
    "order_id",
    "intent",
    "order_age_days",
    "customer_tier",
    "policy_rules_triggered",
    "tools_called",
    "final_decision",
    "decision_reason",
    "response",
)


def public_view(state: dict) -> dict:
    return {k: state.get(k) for k in PUBLIC_FIELDS if state.get(k) is not None}

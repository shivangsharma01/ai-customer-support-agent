import time

from langchain_core.messages import HumanMessage

from graph.builder import get_graph
from graph.state import public_view
from services.events import bus
from services.observability import get_callbacks


def run_turn(session_id: str, customer_id: str, message: str) -> dict:
    """Run one conversation turn through the graph. Returns the public state view."""
    bus.emit(session_id, "user_message", {"message": message, "customer_id": customer_id})
    t0 = time.perf_counter()
    result = get_graph().invoke(
        {
            "messages": [HumanMessage(content=message)],
            "session_id": session_id,
            "customer_id": customer_id,
        },
        config={
            "configurable": {"thread_id": session_id},
            "callbacks": get_callbacks(),
            "recursion_limit": 25,
        },
    )
    view = public_view(result)
    bus.emit(session_id, "agent_response", {
        "response": result.get("response", ""),
        "total_latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        "state": view,
    })
    return view

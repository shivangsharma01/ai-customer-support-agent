from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from config import settings
from graph import nodes
from graph.state import AgentState

_graph = None


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("extract_intent", nodes.extract_intent)
    g.add_node("retrieve_customer", nodes.retrieve_customer)
    g.add_node("retrieve_order", nodes.retrieve_order)
    g.add_node("retrieve_policy", nodes.retrieve_policy_node)
    g.add_node("retrieve_similar_cases", nodes.retrieve_similar_cases_node)
    g.add_node("decision", nodes.decision)
    g.add_node("tools", nodes.tool_node)
    g.add_node("policy_validation", nodes.policy_validation)
    g.add_node("generate_response", nodes.generate_response)

    g.add_edge(START, "extract_intent")
    g.add_conditional_edges("extract_intent", nodes.route_after_intent,
                            ["retrieve_customer", "generate_response"])
    g.add_edge("retrieve_customer", "retrieve_order")
    g.add_conditional_edges("retrieve_order", nodes.route_after_order,
                            ["retrieve_policy", "generate_response"])
    g.add_edge("retrieve_policy", "retrieve_similar_cases")
    g.add_edge("retrieve_similar_cases", "decision")
    g.add_conditional_edges("decision", nodes.route_after_decision,
                            ["tools", "policy_validation"])
    g.add_edge("tools", "decision")
    g.add_edge("policy_validation", "generate_response")
    g.add_edge("generate_response", END)
    return g


def get_graph():
    global _graph
    if _graph is None:
        conninfo = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
        pool = ConnectionPool(
            conninfo, max_size=5, open=True,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        )
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()
        _graph = build_graph().compile(checkpointer=checkpointer)
    return _graph

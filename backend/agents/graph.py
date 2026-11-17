"""Compiled LangGraph workflow for safe mailbox analysis."""
from langgraph.graph import END, START, StateGraph
from backend.agents.nodes import (
    classify_threads_node,
    fetch_threads_node,
    normalize_threads_node,
    persist_analyses_node,
    validate_analyses_node,
)
from backend.agents.state import AnalysisState


def build_analysis_graph():
    graph = StateGraph(AnalysisState)
    graph.add_node("fetch_threads", fetch_threads_node)
    graph.add_node("normalize_threads", normalize_threads_node)
    graph.add_node("classify_threads", classify_threads_node)
    graph.add_node("validate_analyses", validate_analyses_node)
    graph.add_node("persist_analyses", persist_analyses_node)
    graph.add_edge(START, "fetch_threads")
    graph.add_edge("fetch_threads", "normalize_threads")
    graph.add_edge("normalize_threads", "classify_threads")
    graph.add_edge("classify_threads", "validate_analyses")
    graph.add_edge("validate_analyses", "persist_analyses")
    graph.add_edge("persist_analyses", END)
    return graph.compile()


analysis_graph = build_analysis_graph()


async def run_analysis_workflow(user_id: str, db):
    return await analysis_graph.ainvoke({"user_id": user_id, "db": db})

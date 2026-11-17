from typing import Any

from langgraph.graph import END, StateGraph

from agents import (
    run_analysis_agent,
    run_extraction_agent,
    run_factcheck_agent,
    run_report_agent,
    run_research_agent,
)
from state import ResearchState


def _mark_retry(state: dict[str, Any]) -> dict[str, Any]:
    return {"retried": True}


def _route_after_factcheck(state: dict[str, Any]) -> str:
    """Retry research at most once, and only if there were claims to check."""
    fc = state.get("factcheck", {}) or {}
    if not fc.get("checks"):
        return "report"
    ratio = fc.get("support_ratio", 0.0)
    if ratio < 0.6 and not state.get("retried", False):
        return "research_retry"
    return "report"


def build_graph(enable_factcheck_loop: bool = True):
    g = StateGraph(ResearchState)

    g.add_node("research", run_research_agent)
    g.add_node("extraction", run_extraction_agent)
    g.add_node("analysis", run_analysis_agent)
    g.add_node("factcheck", run_factcheck_agent)
    g.add_node("mark_retry", _mark_retry)
    g.add_node("report", run_report_agent)

    g.set_entry_point("research")
    g.add_edge("research", "extraction")
    g.add_edge("extraction", "analysis")
    g.add_edge("analysis", "factcheck")

    if enable_factcheck_loop:
        g.add_conditional_edges(
            "factcheck",
            _route_after_factcheck,
            {"research_retry": "mark_retry", "report": "report"},
        )
        g.add_edge("mark_retry", "research")
    else:
        g.add_edge("factcheck", "report")
    g.add_edge("report", END)
    return g.compile()
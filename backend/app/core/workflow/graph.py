"""LangGraph workflow definition for iterative research."""

import logging

from langgraph.graph import END, StateGraph

from .nodes.analyze import analyze_node
from .nodes.report import report_node
from .nodes.search import search_node
from .nodes.synthesize import synthesize_node
from .nodes.wiki_retrieve import wiki_retrieve_node
from .state import ResearchState

logger = logging.getLogger(__name__)

_CONFIDENCE_THRESHOLD = 0.7


def should_continue(state: ResearchState) -> str:
    """Route to another search iteration or final report generation."""
    if state.get("status") == "error":
        logger.info("should_continue: error state detected, ending workflow")
        return "end"

    iterations = state["iterations"]
    max_iterations = state["max_iterations"]

    if iterations >= max_iterations:
        logger.info(
            "should_continue: reached max iterations (%d/%d), ending",
            iterations,
            max_iterations,
        )
        return "end"

    if len(state.get("search_results", [])) < 3:
        logger.info("should_continue: insufficient search results, continuing")
        return "continue"

    analyzed_results = state.get("analyzed_results", [])
    if analyzed_results:
        avg_confidence = sum(r["confidence"] for r in analyzed_results) / len(
            analyzed_results
        )
        if avg_confidence < _CONFIDENCE_THRESHOLD:
            logger.info(
                "should_continue: low confidence (%.2f < %.2f), continuing",
                avg_confidence,
                _CONFIDENCE_THRESHOLD,
            )
            return "continue"

    logger.info("should_continue: quality sufficient, ending")
    return "end"


def create_research_graph():
    workflow = StateGraph(ResearchState)

    workflow.add_node("wiki_retrieve", wiki_retrieve_node)
    workflow.add_node("search", search_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("synthesize", synthesize_node)
    workflow.add_node("report", report_node)

    workflow.set_entry_point("wiki_retrieve")
    workflow.add_edge("wiki_retrieve", "search")
    workflow.add_edge("search", "analyze")
    workflow.add_edge("analyze", "synthesize")
    workflow.add_conditional_edges(
        "synthesize",
        should_continue,
        {
            "continue": "search",
            "end": "report",
        },
    )
    workflow.add_edge("report", END)

    compiled = workflow.compile()
    logger.info("create_research_graph: workflow graph compiled successfully")
    return compiled


research_workflow = create_research_graph()

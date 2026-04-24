"""Report workflow node using web content and academic paper sources."""

import logging
from typing import List

from app.services.llm import create_llm
from ..state import ResearchState, SearchResult

logger = logging.getLogger(__name__)

_REPORT_PROMPT = """\
Write a research report in Markdown using the provided academic papers and web sources.

Research query: {query}
Iteration: {iterations}/{max_iterations}

Synthesis:
{synthesized_content}

Reusable Wiki context:
{wiki_context}

Query plan and task summary:
{task_summary}

Academic papers from arXiv and OpenAlex:
{paper_references}

Web/blog/background sources from Exa and DuckDuckGo:
{web_references}

Requirements:
- Treat arXiv and OpenAlex papers as the academic evidence base.
- Use Exa and DuckDuckGo web sources only for broader context, examples, or public discussion.
- Include a concise executive summary.
- Summarize the query understanding, sub-questions, and retrieval tasks.
- Include key findings, evidence, limitations, and future research directions.
- Include separate "Academic References" and "Web Sources" sections.
- Do not invent citations or claim unsupported facts.
"""


def _split_references(search_results: List[SearchResult]) -> tuple[str, str]:
    paper_refs: List[str] = []
    web_refs: List[str] = []
    seen_urls: set[str] = set()

    for index, result in enumerate(search_results, 1):
        url = result.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        title = result.get("title") or "Untitled"
        score = result.get("relevance_score", 0)
        line = f"[{index}] {title} ({url}) relevance={score:.2f}"

        if result.get("source") in {"arxiv", "openalex"}:
            paper_refs.append(line)
        else:
            web_refs.append(line)

    return "\n".join(paper_refs), "\n".join(web_refs) or "No web sources returned."


def _fallback_report(
    query: str,
    synthesized_content: str,
    task_summary: str,
    paper_references: str,
    web_references: str,
) -> str:
    return (
        f"# {query} Research Report\n\n"
        "## Executive Summary\n\n"
        f"{synthesized_content or 'The workflow collected sources but could not synthesize detailed findings.'}\n\n"
        "## Query Plan and Subtasks\n\n"
        f"{task_summary}\n\n"
        "## Academic References\n\n"
        f"{paper_references}\n\n"
        "## Web Sources\n\n"
        f"{web_references}\n"
    )


async def report_node(state: ResearchState) -> dict:
    """Generate the final report, or preserve hard failure state."""
    if state.get("status") == "error":
        message = state.get("error_message") or "Workflow failed before report generation"
        logger.error("report_node: preserving error state: %s", message)
        return {
            "status": "error",
            "error_message": message,
            "final_report": None,
        }

    search_results = state.get("search_results", [])
    paper_references, web_references = _split_references(search_results)
    if not paper_references:
        logger.warning("report_node: no academic paper sources; generating limited report")
        paper_references = (
            "No academic paper sources were available. The search tool error log should be "
            "reviewed before treating this report as evidence-backed."
        )

    query: str = state["query"]
    iterations: int = state["iterations"]
    max_iterations: int = state["max_iterations"]
    synthesized_content: str = state.get("synthesized_content", "")
    wiki_context = state.get("wiki_context", "") or "No reusable Wiki context was available."
    task_summary = _build_task_summary(state)

    prompt = _REPORT_PROMPT.format(
        query=query,
        iterations=iterations,
        max_iterations=max_iterations,
        synthesized_content=synthesized_content,
        wiki_context=wiki_context[:8000],
        task_summary=task_summary,
        paper_references=paper_references,
        web_references=web_references,
    )

    try:
        llm = create_llm(temperature=0.2)
        response = await llm.ainvoke(prompt)
        report = response.content
    except Exception as exc:
        logger.error("report_node: LLM call failed, using source-backed fallback: %s", exc)
        report = _fallback_report(
            query,
            synthesized_content,
            task_summary,
            paper_references,
            web_references,
        )

    logger.info("report_node: generated report with %d chars", len(report))

    return {
        "final_report": report,
        "status": "completed",
        "error_message": None,
    }


def _build_task_summary(state: ResearchState) -> str:
    metadata = state.get("metadata", {})
    query_plan = metadata.get("query_plan", {}) if isinstance(metadata, dict) else {}
    semantic = query_plan.get("semantic", {}) if isinstance(query_plan, dict) else {}
    sub_questions = query_plan.get("sub_questions", []) if isinstance(query_plan, dict) else []

    parts = []
    if semantic:
        parts.append(
            "- Intent: "
            f"{semantic.get('task_type', 'research')} on "
            f"{semantic.get('core_tech', 'technology')} in "
            f"{semantic.get('application_domain', 'the target domain')}."
        )
        expected = semantic.get("expected_output", [])
        if expected:
            parts.append(f"- Expected outputs: {', '.join(expected)}.")
    if sub_questions:
        parts.append("- Sub-questions:")
        for item in sub_questions:
            parts.append(f"  - {item.get('query', '')}")

    return "\n".join(parts) or "No query plan metadata available."

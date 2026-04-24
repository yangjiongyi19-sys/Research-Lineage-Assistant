"""Search workflow node combining web content and academic papers."""

import logging
import re
import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

import httpx
from app.config import settings
from app.services.arxiv import ArxivClient
from app.services.duckduckgo import DuckDuckGoClient
from app.services.openalex import OpenAlexClient
from app.services.search import ExaMCPClient
from ..state import ResearchState, SearchResult

logger = logging.getLogger(__name__)

_MAX_RESULTS_PER_SOURCE = 5
_MIN_ACADEMIC_RESULTS = 1
_MAX_TOOL_RETRIES = 2
_RETRYABLE_ERRORS = {"timeout", "network", "rate_limit", "parse_error", "unknown", "empty_result"}
_NON_RETRYABLE_ERRORS = {"auth", "bad_request", "tool_not_found"}

_TITLE_RE = re.compile(r"^Title:\s*(.+)$", re.MULTILINE)
_URL_RE = re.compile(r"^URL:\s*(\S+)$", re.MULTILINE)

ToolRunner = Callable[[str, int], Awaitable[List[Dict[str, Any]]]]


@dataclass
class GuardedToolResult:
    tool: str
    query: str
    results: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    fallback_used: Optional[str] = None


def _error(message: str, iterations: int) -> dict:
    logger.error("search_node: %s", message)
    return {
        "status": "error",
        "error_message": message,
        "iterations": iterations + 1,
    }


def classify_error(exc: Exception) -> str:
    """Classify tool errors so the workflow can decide retry/fallback behavior."""
    message = str(exc).lower()

    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, httpx.TimeoutException)):
        return "timeout"
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code in {401, 403}:
            return "auth"
        if status_code == 404:
            return "tool_not_found"
        if status_code == 429:
            return "rate_limit"
        if 400 <= status_code < 500:
            return "bad_request"
        return "network"
    if isinstance(exc, httpx.RequestError):
        return "network"
    if isinstance(exc, (ValueError, KeyError, TypeError)):
        return "parse_error"

    if "timeout" in message or "timed out" in message:
        return "timeout"
    if "rate limit" in message or "too many requests" in message or "429" in message:
        return "rate_limit"
    if "unauthorized" in message or "forbidden" in message or "api key" in message or "auth" in message:
        return "auth"
    if "bad request" in message or "invalid" in message or "400" in message:
        return "bad_request"
    if "not found" in message or "unknown tool" in message:
        return "tool_not_found"
    if "json" in message or "parse" in message or "decode" in message:
        return "parse_error"
    if "network" in message or "connect" in message or "dns" in message:
        return "network"

    return "unknown"


def should_retry(error_type: str, retry_count: int) -> bool:
    if error_type in _NON_RETRYABLE_ERRORS:
        return False
    if error_type not in _RETRYABLE_ERRORS:
        return False
    return retry_count < _MAX_TOOL_RETRIES


def _tool_error(
    tool: str,
    query: str,
    error_type: str,
    error_message: str,
    retry_count: int,
) -> Dict[str, Any]:
    return {
        "tool": tool,
        "query": query,
        "error_type": error_type,
        "error_message": error_message,
        "retry_count": retry_count,
    }


def _rewrite_query_for_retry(query: str, error_type: str, retry_count: int) -> str:
    normalized = " ".join(query.split())
    if error_type == "empty_result":
        return normalized.replace("latest progress in ", "").replace("recent papers", "survey")
    if error_type in {"timeout", "rate_limit"}:
        terms = normalized.split()
        return " ".join(terms[: max(4, min(len(terms), 10))])
    if error_type == "parse_error":
        return f"{normalized} summary"
    if retry_count > 0:
        return normalized.replace(" / ", " ").replace(" using ", " ")
    return normalized


def _retry_result_count(error_type: str, retry_count: int, default_count: int) -> int:
    if error_type in {"timeout", "rate_limit"}:
        return max(2, default_count - retry_count - 1)
    return default_count


async def call_tool_with_guard(
    tool: str,
    query: str,
    runner: ToolRunner,
    max_results: int = _MAX_RESULTS_PER_SOURCE,
    fallback_tool: Optional[str] = None,
    fallback_runner: Optional[ToolRunner] = None,
) -> GuardedToolResult:
    """Call a search tool with retry, structured errors, and optional fallback."""
    errors: List[Dict[str, Any]] = []
    current_query = query
    current_max_results = max_results

    for attempt in range(_MAX_TOOL_RETRIES + 1):
        try:
            results = await runner(current_query, current_max_results)
            if results:
                return GuardedToolResult(tool=tool, query=current_query, results=results, errors=errors)

            error_type = "empty_result"
            error = _tool_error(tool, current_query, error_type, "tool returned no results", attempt)
            errors.append(error)
            if not should_retry(error_type, attempt):
                break
            current_query = _rewrite_query_for_retry(current_query, error_type, attempt)
            current_max_results = _retry_result_count(error_type, attempt + 1, max_results)
        except Exception as exc:
            error_type = classify_error(exc)
            error = _tool_error(tool, current_query, error_type, str(exc), attempt)
            errors.append(error)
            if not should_retry(error_type, attempt):
                break
            if error_type == "rate_limit":
                await asyncio.sleep(0.8 * (attempt + 1))
            current_query = _rewrite_query_for_retry(current_query, error_type, attempt)
            current_max_results = _retry_result_count(error_type, attempt + 1, max_results)

    if fallback_tool and fallback_runner:
        fallback_query = _rewrite_query_for_retry(query, errors[-1]["error_type"] if errors else "unknown", 0)
        try:
            fallback_results = await fallback_runner(fallback_query, max(2, max_results - 1))
            if fallback_results:
                errors.append(
                    {
                        "tool": fallback_tool,
                        "query": fallback_query,
                        "error_type": "fallback_used",
                        "error_message": f"{tool} failed; used {fallback_tool}",
                        "retry_count": 0,
                    }
                )
                return GuardedToolResult(
                    tool=tool,
                    query=query,
                    results=fallback_results,
                    errors=errors,
                    fallback_used=fallback_tool,
                )
        except Exception as exc:
            errors.append(
                _tool_error(
                    fallback_tool,
                    fallback_query,
                    classify_error(exc),
                    str(exc),
                    0,
                )
            )

    return GuardedToolResult(tool=tool, query=query, results=[], errors=errors)


def _build_exa_query(query: str, depth: int, iterations: int) -> str:
    parts = [query, "blog article analysis explainer"]
    if depth >= 3:
        parts.append("latest developments")
    if iterations > 0:
        parts.append("practical examples")
    return " ".join(parts)


def _build_duckduckgo_query(query: str, depth: int, iterations: int) -> str:
    parts = [query, "blog article tutorial opinion discussion"]
    if depth >= 3:
        parts.append("latest news analysis")
    if iterations > 0:
        parts.append("examples case study")
    return " ".join(parts)


def _build_arxiv_query(query: str, depth: int, iterations: int) -> str:
    parts = [query]
    if depth >= 3:
        parts.append("survey benchmark method")
    if iterations > 0:
        parts.append("future work open problems")
    return " ".join(parts)


def _build_openalex_query(query: str, depth: int, iterations: int) -> str:
    parts = [query]
    if depth >= 3:
        parts.append("survey benchmark method")
    if iterations > 0:
        parts.append("future work open problems")
    return " ".join(parts)


def _query_plan_queries(state: ResearchState) -> tuple[List[str], List[str]]:
    metadata = state.get("metadata", {})
    query_plan = metadata.get("query_plan", {}) if isinstance(metadata, dict) else {}
    expanded = query_plan.get("expanded_queries", []) if isinstance(query_plan, dict) else []
    academic_queries: List[str] = []
    web_queries: List[str] = []

    for item in expanded:
        academic_queries.extend(item.get("academic_queries", []))
        web_queries.extend(item.get("web_queries", []))

    return _dedupe_strings(academic_queries)[:12], _dedupe_strings(web_queries)[:10]


def _dedupe_strings(values: List[str]) -> List[str]:
    seen = set()
    output = []
    for value in values:
        normalized = " ".join(str(value).split())
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(normalized)
    return output


def _source_from_tool(tool: str) -> str:
    if tool.startswith("exa"):
        return "exa"
    if tool.startswith("duckduckgo"):
        return "duckduckgo"
    if tool.startswith("arxiv"):
        return "arxiv"
    if tool.startswith("openalex"):
        return "openalex"
    return tool


def _format_tool_error(error: Dict[str, Any]) -> str:
    return (
        f"{error.get('tool')} failed for query '{error.get('query')}': "
        f"{error.get('error_type')} - {error.get('error_message')} "
        f"(retry_count={error.get('retry_count', 0)})"
    )


def _normalize_exa_result(result: Dict[str, Any]) -> SearchResult:
    content = result.get("text", result.get("content", "")) or ""
    title = result.get("title", "") or ""
    url = result.get("url", "") or ""

    if not title:
        title_match = _TITLE_RE.search(content)
        if title_match:
            title = title_match.group(1).strip()

    if not url:
        url_match = _URL_RE.search(content)
        if url_match:
            url = url_match.group(1).strip()

    return SearchResult(
        source="exa",
        title=title or "Untitled web result",
        content=content,
        url=url,
        relevance_score=float(
            result.get("score", result.get("relevance_score", 0.5)) or 0.5
        ),
    )


def _normalize_arxiv_result(result: Dict[str, Any]) -> SearchResult:
    metadata_parts = []
    if result.get("author"):
        metadata_parts.append(f"Authors: {result['author']}")
    if result.get("published_date"):
        metadata_parts.append(f"Published: {result['published_date']}")
    if result.get("categories"):
        metadata_parts.append(f"Categories: {', '.join(result['categories'])}")
    if result.get("doi"):
        metadata_parts.append(f"DOI: {result['doi']}")

    metadata = "\n".join(metadata_parts)
    content = result.get("content", "")
    if metadata:
        content = f"{metadata}\n\nAbstract: {content}"

    return SearchResult(
        source="arxiv",
        title=result.get("title", "") or "Untitled arXiv paper",
        content=content,
        url=result.get("url", ""),
        relevance_score=float(result.get("relevance_score", 1.0) or 1.0),
    )


def _normalize_openalex_result(result: Dict[str, Any]) -> SearchResult:
    return SearchResult(
        source="openalex",
        title=result.get("title", "") or "Untitled OpenAlex work",
        content=result.get("content", ""),
        url=result.get("url", ""),
        relevance_score=float(result.get("relevance_score", 0.9) or 0.9),
    )


def _normalize_duckduckgo_result(result: Dict[str, Any]) -> SearchResult:
    return SearchResult(
        source="duckduckgo",
        title=result.get("title", "") or "Untitled DuckDuckGo result",
        content=result.get("content", ""),
        url=result.get("url", ""),
        relevance_score=float(result.get("relevance_score", 0.5) or 0.5),
    )


def _dedupe(results: Iterable[SearchResult]) -> List[SearchResult]:
    seen_urls: set[str] = set()
    unique: List[SearchResult] = []

    for result in results:
        url = result.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        unique.append(result)

    unique.sort(
        key=lambda item: (
            2 if item.get("source") in {"arxiv", "openalex"} else 1 if item.get("source") == "exa" else 0,
            item.get("relevance_score", 0),
        ),
        reverse=True,
    )
    return unique


async def search_node(state: ResearchState) -> dict:
    """Run Exa, DuckDuckGo, arXiv, and OpenAlex searches for the same query."""
    if state.get("status") == "error":
        return {"status": "error", "error_message": state.get("error_message")}

    query: str = state["query"]
    depth: int = state["depth"]
    iterations: int = state["iterations"]
    existing_results = state.get("search_results", [])
    existing_tool_errors = state.get("tool_errors", [])

    logger.info(
        "search_node: combined search query=%r depth=%d iteration=%d",
        query,
        depth,
        iterations,
    )

    exa_client = ExaMCPClient(api_key=settings.EXA_API_KEY or None)
    duckduckgo_client = DuckDuckGoClient()
    arxiv_client = ArxivClient()
    openalex_client = OpenAlexClient()

    planned_academic_queries, planned_web_queries = _query_plan_queries(state)
    exa_queries = planned_web_queries or [_build_exa_query(query, depth, iterations)]
    duckduckgo_queries = planned_web_queries or [_build_duckduckgo_query(query, depth, iterations)]
    arxiv_queries = planned_academic_queries or [_build_arxiv_query(query, depth, iterations)]
    openalex_queries = planned_academic_queries or [_build_openalex_query(query, depth, iterations)]
    tool_errors: List[Dict[str, Any]] = []

    tasks = []
    for search_query in exa_queries:
        tasks.append(
            call_tool_with_guard(
                "exa_search_mcp",
                search_query,
                exa_client.web_search,
                _MAX_RESULTS_PER_SOURCE,
                fallback_tool="duckduckgo_search",
                fallback_runner=duckduckgo_client.search,
            )
        )
    for search_query in duckduckgo_queries:
        tasks.append(
            call_tool_with_guard(
                "duckduckgo_search",
                search_query,
                duckduckgo_client.search,
                _MAX_RESULTS_PER_SOURCE,
                fallback_tool="exa_search_mcp",
                fallback_runner=exa_client.web_search,
            )
        )
    for search_query in arxiv_queries:
        tasks.append(
            call_tool_with_guard(
                "arxiv_api",
                search_query,
                arxiv_client.search,
                _MAX_RESULTS_PER_SOURCE,
                fallback_tool="openalex_api",
                fallback_runner=openalex_client.search,
            )
        )
    for search_query in openalex_queries:
        tasks.append(
            call_tool_with_guard(
                "openalex_api",
                search_query,
                openalex_client.search,
                _MAX_RESULTS_PER_SOURCE,
                fallback_tool="arxiv_api",
                fallback_runner=arxiv_client.search,
            )
        )

    responses = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    raw_exa_results = []
    raw_duckduckgo_results = []
    raw_arxiv_results = []
    raw_openalex_results = []

    for response in responses:
        if isinstance(response, Exception):
            tool_errors.append(
                _tool_error(
                    "search_guard",
                    query,
                    classify_error(response),
                    str(response),
                    0,
                )
            )
            continue
        tool_errors.extend(response.errors)
        source = _source_from_tool(response.fallback_used or response.tool)
        if source == "exa":
            raw_exa_results.extend(response.results)
        elif source == "duckduckgo":
            raw_duckduckgo_results.extend(response.results)
        elif source == "arxiv":
            raw_arxiv_results.extend(response.results)
        elif source == "openalex":
            raw_openalex_results.extend(response.results)

    arxiv_results = [_normalize_arxiv_result(result) for result in raw_arxiv_results]
    openalex_results = [
        _normalize_openalex_result(result) for result in raw_openalex_results
    ]
    if len(arxiv_results) + len(openalex_results) < _MIN_ACADEMIC_RESULTS:
        logger.warning(
            "search_node: no academic papers found; continuing with limited evidence. errors=%s",
            [_format_tool_error(error) for error in tool_errors],
        )

    exa_results = [_normalize_exa_result(result) for result in raw_exa_results]
    duckduckgo_results = [
        _normalize_duckduckgo_result(result) for result in raw_duckduckgo_results
    ]
    updated_search_results = _dedupe(
        [
            *existing_results,
            *arxiv_results,
            *openalex_results,
            *exa_results,
            *duckduckgo_results,
        ]
    )

    logger.info(
        "search_node: retained %d arXiv results, %d OpenAlex results, %d Exa results, %d DuckDuckGo results",
        len(arxiv_results),
        len(openalex_results),
        len(exa_results),
        len(duckduckgo_results),
    )

    return {
        "search_results": updated_search_results[: settings.SEARCH_RESULTS_LIMIT * 2],
        "tool_errors": [*existing_tool_errors, *tool_errors][-200:],
        "iterations": iterations + 1,
        "status": "searching",
        "error_message": None,
        "metadata": {
            **state.get("metadata", {}),
            "last_exa_queries": exa_queries,
            "last_duckduckgo_queries": duckduckgo_queries,
            "last_arxiv_queries": arxiv_queries,
            "last_openalex_queries": openalex_queries,
            "last_exa_result_count": len(exa_results),
            "last_duckduckgo_result_count": len(duckduckgo_results),
            "last_arxiv_result_count": len(arxiv_results),
            "last_openalex_result_count": len(openalex_results),
            "tool_errors": [*state.get("metadata", {}).get("tool_errors", []), *tool_errors][-200:],
            "last_tool_errors": tool_errors,
            "last_search_errors": [
                _format_tool_error(error)
                for error in tool_errors
                if error.get("error_type") != "fallback_used"
            ],
        },
    }

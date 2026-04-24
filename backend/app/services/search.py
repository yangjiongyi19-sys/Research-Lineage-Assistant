"""Search service backed by Exa MCP."""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.config import settings

logger = logging.getLogger(__name__)

_TITLE_RE = re.compile(r"^Title:\s*(.+)$", re.MULTILINE)
_URL_RE = re.compile(r"^URL:\s*(\S+)$", re.MULTILINE)


class ExaMCPClient:
    """Thin async client for Exa's MCP streamable HTTP endpoint."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.EXA_API_KEY
        self.mcp_url = settings.EXA_MCP_URL

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        try:
            async with httpx.AsyncClient(headers=headers or None) as http_client:
                async with streamable_http_client(
                    url=self.mcp_url,
                    http_client=http_client,
                ) as (read_stream, write_stream, _):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        logger.debug("MCP session initialized, calling tool: %s", tool_name)
                        return await session.call_tool(tool_name, arguments=arguments)
        except Exception as exc:
            logger.error("MCP tool call failed (%s): %s", tool_name, exc)
            raise

    async def web_search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        result = await self._call_tool(
            "web_search_exa",
            {
                "query": query,
                "numResults": num_results,
            },
        )

        search_results: List[Dict[str, Any]] = []
        for item in result.content:
            if not hasattr(item, "text") or item.type != "text":
                continue

            text = item.text
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                title_match = _TITLE_RE.search(text)
                url_match = _URL_RE.search(text)
                search_results.append(
                    {
                        "source": "exa",
                        "title": title_match.group(1).strip() if title_match else "",
                        "content": text[:2000],
                        "url": url_match.group(1).strip() if url_match else "",
                        "relevance_score": 0.5,
                    }
                )
                continue

            if isinstance(parsed, list):
                search_results.extend(self._normalize_result(item) for item in parsed)
            elif isinstance(parsed, dict) and isinstance(parsed.get("results"), list):
                search_results.extend(
                    self._normalize_result(item) for item in parsed["results"]
                )
            elif isinstance(parsed, dict):
                search_results.append(self._normalize_result(parsed))

        return search_results

    async def web_fetch(self, url: str) -> Optional[str]:
        try:
            result = await self._call_tool("web_fetch_exa", {"url": url})
            for item in result.content:
                if hasattr(item, "text") and item.type == "text":
                    return item.text
            return None
        except Exception as exc:
            logger.error("Exa MCP web_fetch failed for %s: %s", url, exc)
            return None

    def _normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source": "exa",
            "title": result.get("title", ""),
            "content": result.get("text", result.get("content", "")),
            "url": result.get("url", ""),
            "relevance_score": result.get("score", 0.5),
            "published_date": result.get("publishedDate"),
            "author": result.get("author"),
        }


class SearchService:
    """Application-level search service."""

    def __init__(self):
        self._mcp_client: Optional[ExaMCPClient] = None

    async def _get_client(self) -> ExaMCPClient:
        if self._mcp_client is None:
            self._mcp_client = ExaMCPClient()
        return self._mcp_client

    async def search(self, query: str, sources: List[str] = None) -> List[Dict[str, Any]]:
        client = await self._get_client()
        results = await client.web_search(
            query=query,
            num_results=settings.SEARCH_RESULTS_LIMIT,
        )
        results = self._deduplicate_results(results)
        results.sort(key=lambda item: item.get("relevance_score", 0), reverse=True)
        return results[: settings.SEARCH_RESULTS_LIMIT]

    async def fetch_page(self, url: str) -> Optional[str]:
        client = await self._get_client()
        return await client.web_fetch(url)

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_urls = set()
        unique_results = []

        for result in results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        return unique_results

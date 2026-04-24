"""DuckDuckGo search client using the ddgs package."""

import asyncio
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class DuckDuckGoClient:
    """Search DuckDuckGo without an API key.

    Requires the `ddgs` package. The import is intentionally lazy so the backend
    can still start before dependencies are installed.
    """

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._search_sync, query, max_results)

    def _search_sync(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        try:
            from ddgs import DDGS
        except ImportError as exc:
            raise RuntimeError(
                "DuckDuckGo search requires the 'ddgs' package. "
                "Install it with: conda run -n research_agent python -m pip install ddgs"
            ) from exc

        results: List[Dict[str, Any]] = []
        with DDGS() as ddgs:
            for index, item in enumerate(ddgs.text(query, max_results=max_results)):
                url = item.get("href") or item.get("url") or ""
                title = item.get("title") or ""
                content = item.get("body") or item.get("content") or ""
                if not url or not title:
                    continue

                results.append(
                    {
                        "source": "duckduckgo",
                        "title": title,
                        "content": content,
                        "url": url,
                        "relevance_score": max(0.1, 1.0 - index * 0.08),
                    }
                )

        return results

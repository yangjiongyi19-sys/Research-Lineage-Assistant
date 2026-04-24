"""Minimal async client for the free OpenAlex Works API."""

import logging
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

_OPENALEX_WORKS_URL = "https://api.openalex.org/works"


class OpenAlexClient:
    """Search OpenAlex works without an API key."""

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        params = {
            "search": query,
            "per-page": max_results,
            "sort": "relevance_score:desc",
        }
        headers = {
            "User-Agent": "ResearchLineageAssistant/1.0 (local research assistant)"
        }

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(_OPENALEX_WORKS_URL, params=params)
            response.raise_for_status()

        payload = response.json()
        return [self._normalize_work(item) for item in payload.get("results", [])]

    def _normalize_work(self, item: Dict[str, Any]) -> Dict[str, Any]:
        authorships = item.get("authorships", []) or []
        authors = []
        for authorship in authorships:
            author = authorship.get("author") or {}
            name = author.get("display_name")
            if name:
                authors.append(name)

        primary_location = item.get("primary_location") or {}
        landing_page_url = primary_location.get("landing_page_url")
        source = primary_location.get("source") or {}
        source_name = source.get("display_name")
        open_access = item.get("open_access") or {}
        best_oa_location = item.get("best_oa_location") or {}

        url = (
            open_access.get("oa_url")
            or best_oa_location.get("landing_page_url")
            or landing_page_url
            or item.get("doi")
            or item.get("id")
            or ""
        )

        abstract = self._reconstruct_abstract(item.get("abstract_inverted_index"))

        metadata_parts = []
        if authors:
            metadata_parts.append(f"Authors: {', '.join(authors[:8])}")
        if item.get("publication_year"):
            metadata_parts.append(f"Year: {item['publication_year']}")
        if source_name:
            metadata_parts.append(f"Venue: {source_name}")
        if item.get("doi"):
            metadata_parts.append(f"DOI: {item['doi']}")
        if item.get("cited_by_count") is not None:
            metadata_parts.append(f"Cited by: {item['cited_by_count']}")

        content = abstract
        if metadata_parts:
            content = f"{chr(10).join(metadata_parts)}\n\nAbstract: {abstract}"

        return {
            "source": "openalex",
            "title": item.get("display_name", ""),
            "content": content,
            "url": url,
            "relevance_score": float(item.get("relevance_score") or 0.9),
            "published_date": str(item.get("publication_year") or ""),
            "author": ", ".join(authors),
            "doi": item.get("doi"),
            "venue": source_name,
        }

    def _reconstruct_abstract(self, inverted_index: Dict[str, List[int]] | None) -> str:
        if not inverted_index:
            return ""

        positions: Dict[int, str] = {}
        for word, indexes in inverted_index.items():
            for index in indexes:
                positions[index] = word

        return " ".join(positions[index] for index in sorted(positions))

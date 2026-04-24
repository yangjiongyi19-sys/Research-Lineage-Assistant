"""Minimal async client for the public arXiv Atom API."""

import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

_ARXIV_API_URL = "https://export.arxiv.org/api/query"
_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_ARXIV_NS = "{http://arxiv.org/schemas/atom}"


class ArxivClient:
    """Search arXiv without an API key."""

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        headers = {
            "User-Agent": "ResearchLineageAssistant/1.0 (local research assistant)"
        }

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(_ARXIV_API_URL, params=params)
            response.raise_for_status()

        return self._parse_feed(response.text)

    def _parse_feed(self, xml_text: str) -> List[Dict[str, Any]]:
        root = ET.fromstring(xml_text)
        results: List[Dict[str, Any]] = []

        for entry in root.findall(f"{_ATOM_NS}entry"):
            title = self._text(entry, "title")
            summary = self._text(entry, "summary")
            published = self._text(entry, "published")
            paper_url = self._text(entry, "id")
            authors = [
                self._text(author, "name")
                for author in entry.findall(f"{_ATOM_NS}author")
            ]
            categories = [
                category.attrib.get("term", "")
                for category in entry.findall(f"{_ATOM_NS}category")
            ]
            doi = self._text(entry, "doi", namespace=_ARXIV_NS)

            results.append(
                {
                    "source": "arxiv",
                    "title": " ".join(title.split()),
                    "content": " ".join(summary.split()),
                    "url": paper_url,
                    "relevance_score": 1.0,
                    "published_date": published,
                    "author": ", ".join(author for author in authors if author),
                    "categories": categories,
                    "doi": doi,
                }
            )

        return results

    def _text(self, element: ET.Element, name: str, namespace: str = _ATOM_NS) -> str:
        child = element.find(f"{namespace}{name}")
        return child.text.strip() if child is not None and child.text else ""

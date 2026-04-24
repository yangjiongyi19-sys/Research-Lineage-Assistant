from __future__ import annotations

from typing import Dict, List, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wiki import WikiPage
from app.services.wiki_store import extract_wikilinks


async def run_wiki_lint(db: AsyncSession) -> List[Dict[str, object]]:
    result = await db.execute(select(WikiPage))
    pages = result.scalars().all()
    titles: Set[str] = {page.title for page in pages}
    paths: Set[str] = {page.path for page in pages}
    incoming: Dict[str, Set[str]] = {page.title: set() for page in pages}
    issues: List[Dict[str, object]] = []

    for page in pages:
        links = extract_wikilinks(page.content)
        if not links and page.page_type not in {"system", "overview"}:
            issues.append(
                {
                    "type": "no_outlinks",
                    "severity": "warning",
                    "page": page.path,
                    "detail": "Page does not link to other Wiki pages.",
                    "affected_pages": [],
                }
            )
        for link in links:
            if link in incoming:
                incoming[link].add(page.path)
            if link not in titles and link not in paths:
                issues.append(
                    {
                        "type": "broken_link",
                        "severity": "error",
                        "page": page.path,
                        "detail": f"Broken wikilink: [[{link}]]",
                        "affected_pages": [link],
                    }
                )

    for page in pages:
        if page.page_type in {"system", "overview"}:
            continue
        if not incoming.get(page.title):
            issues.append(
                {
                    "type": "orphan",
                    "severity": "warning",
                    "page": page.path,
                    "detail": "No other Wiki page links to this page.",
                    "affected_pages": [],
                }
            )
    return issues

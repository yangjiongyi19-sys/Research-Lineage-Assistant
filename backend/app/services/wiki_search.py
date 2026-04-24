from __future__ import annotations

from typing import Any, Dict, List, Tuple
import re

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wiki import WikiPage
from app.services.wiki_store import ensure_workspace, reindex_workspace


def _fts_query(query: str) -> str:
    tokens = [token for token in re.split(r"\s+", query.strip()) if token]
    cleaned = [re.sub(r'["*]', "", token) for token in tokens]
    return " OR ".join(f'"{token}"' for token in cleaned if token)


def _snippet(content: str, query: str, max_length: int = 420) -> str:
    lowered = content.lower()
    terms = [term.lower() for term in re.split(r"\s+", query) if term]
    first_hit = min((lowered.find(term) for term in terms if lowered.find(term) >= 0), default=0)
    start = max(0, first_hit - 120)
    snippet = content[start : start + max_length].replace("\n", " ").strip()
    return snippet


def _score_page(page: WikiPage, query: str) -> float:
    terms = [term.lower() for term in re.split(r"\s+", query) if term]
    title = page.title.lower()
    body = page.content.lower()
    score = 0.0
    for term in terms:
        if term in title:
            score += 5
        if term in page.path.lower():
            score += 3
        score += min(body.count(term), 6) * 0.5
    return score


async def search_pages(db: AsyncSession, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    ensure_workspace()
    if not query.strip():
        result = await db.execute(select(WikiPage).order_by(WikiPage.updated_at.desc()).limit(limit))
        return [_page_result(page, "", 0) for page in result.scalars().all()]

    fts = _fts_query(query)
    rows = []
    if fts:
        try:
            result = await db.execute(
                text(
                    """
                    SELECT page_id, title, path, page_type, summary,
                           snippet(wiki_page_fts, 5, '<b>', '</b>', '...', 32) AS snippet,
                           bm25(wiki_page_fts) AS rank
                    FROM wiki_page_fts
                    WHERE wiki_page_fts MATCH :query
                    ORDER BY rank
                    LIMIT :limit
                    """
                ),
                {"query": fts, "limit": limit},
            )
            rows = result.mappings().all()
        except Exception:
            rows = []

    if rows:
        return [
            {
                "id": str(row["page_id"]),
                "title": str(row["title"]),
                "path": str(row["path"]),
                "page_type": str(row["page_type"]),
                "summary": row["summary"],
                "snippet": str(row["snippet"] or ""),
                "score": float(-row["rank"]) if row["rank"] is not None else 0.0,
            }
            for row in rows
        ]

    result = await db.execute(select(WikiPage))
    scored = [
        (page, _score_page(page, query))
        for page in result.scalars().all()
    ]
    scored = [(page, score) for page, score in scored if score > 0]
    scored.sort(key=lambda item: item[1], reverse=True)
    return [_page_result(page, query, score) for page, score in scored[:limit]]


async def build_wiki_context(
    db: AsyncSession,
    query: str,
    limit: int = 6,
    max_chars: int = 12000,
) -> Tuple[List[Dict[str, Any]], str, str]:
    pages = await search_pages(db, query, limit=limit)
    if not pages:
        await reindex_workspace(db)
        pages = await search_pages(db, query, limit=limit)

    if not pages:
        return [], "", "insufficient"

    page_ids = [page["id"] for page in pages]
    result = await db.execute(select(WikiPage).where(WikiPage.id.in_(page_ids)))
    by_id = {page.id: page for page in result.scalars().all()}
    sections: List[str] = []
    for item in pages:
        page = by_id.get(item["id"])
        if not page:
            continue
        sections.append(f"## {page.title}\nPath: {page.path}\n\n{page.content[:2400]}")
    context = "\n\n---\n\n".join(sections)[:max_chars]
    sufficiency = "sufficient" if len(pages) >= 3 and len(context) > 1500 else "partial"
    return pages, context, sufficiency


def _page_result(page: WikiPage, query: str, score: float) -> Dict[str, Any]:
    return {
        "id": page.id,
        "title": page.title,
        "path": page.path,
        "page_type": page.page_type,
        "summary": page.summary,
        "snippet": _snippet(page.content, query),
        "score": score,
    }

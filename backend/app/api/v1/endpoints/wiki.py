from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import Research
from app.models.schemas import (
    WikiLintResult,
    WikiLogResponse,
    WikiPageResponse,
    WikiSaveResponse,
    WikiSearchResult,
)
from app.models.wiki import WikiLog, WikiPage
from app.services.database import get_db
from app.services.wiki_ingest import save_research_to_wiki
from app.services.wiki_lint import run_wiki_lint
from app.services.wiki_search import search_pages
from app.services.wiki_store import ensure_workspace, reindex_workspace

router = APIRouter()


@router.get("/pages", response_model=List[WikiPageResponse])
async def list_pages(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WikiPage).order_by(WikiPage.updated_at.desc()).limit(limit))
    return result.scalars().all()


@router.get("/pages/{page_id}", response_model=WikiPageResponse)
async def get_page(page_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WikiPage).where(WikiPage.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    return page


@router.get("/search", response_model=List[WikiSearchResult])
async def search_wiki(
    query: str = Query("", max_length=500),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    return await search_pages(db, query, limit=limit)


@router.get("/logs", response_model=List[WikiLogResponse])
async def list_logs(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WikiLog).order_by(WikiLog.created_at.desc()).limit(limit))
    return result.scalars().all()


@router.post("/reindex")
async def reindex(db: AsyncSession = Depends(get_db)):
    ensure_workspace()
    count = await reindex_workspace(db)
    return {"count": count, "message": f"Reindexed {count} wiki page(s)"}


@router.post("/lint", response_model=List[WikiLintResult])
async def lint(db: AsyncSession = Depends(get_db)):
    return await run_wiki_lint(db)


@router.post("/research/{research_id}/save", response_model=WikiSaveResponse)
async def save_research(research_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Research).where(Research.id == research_id))
    research = result.scalar_one_or_none()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    if not research.final_report:
        raise HTTPException(status_code=400, detail="Research does not have a final report")

    written_paths = await save_research_to_wiki(db, research)
    metadata = research.research_metadata or {}
    metadata["wiki_updated_pages"] = written_paths
    research.research_metadata = metadata
    await db.commit()
    return WikiSaveResponse(
        research_id=research_id,
        written_paths=written_paths,
        message=f"Saved {len(written_paths)} Wiki file(s)",
    )

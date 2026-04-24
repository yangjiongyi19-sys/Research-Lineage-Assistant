from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
import hashlib
import json
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import Research
from app.models.wiki import WikiSource
from app.services.wiki_store import (
    append_log,
    frontmatter_block,
    read_text,
    slugify,
    today,
    upsert_page_from_file,
    safe_path,
    write_text,
)


def _clean_title(value: str, fallback: str = "Untitled") -> str:
    return re.sub(r"\s+", " ", value or fallback).strip()[:180] or fallback


def _source_url(source: Dict[str, Any]) -> str:
    return str(source.get("url") or source.get("link") or "")


def _source_title(source: Dict[str, Any], index: int) -> str:
    return _clean_title(str(source.get("title") or f"Source {index}"))


async def save_research_to_wiki(db: AsyncSession, research: Research) -> List[str]:
    if not research.final_report:
        return []

    date = today()
    slug = slugify(research.title or research.query or research.id, "research-report")
    sources = research.search_results or []
    source_urls = [_source_url(source) for source in sources if _source_url(source)]
    written: List[str] = []

    report_path = f"wiki/reports/{date}-{slug}.md"
    report_title = _clean_title(research.title, "Research Report")
    source_links = "\n".join(
        f"- [{_source_title(source, idx)}]({_source_url(source)})"
        for idx, source in enumerate(sources, start=1)
        if _source_url(source)
    )
    report_body = "\n".join(
        [
            frontmatter_block(
                report_title,
                "report",
                tags=["research-report", "generated"],
                sources=source_urls,
                related=["Wiki Index"],
            ),
            f"# {report_title}",
            "",
            f"Original query: `{research.query}`",
            "",
            research.final_report,
            "",
            "## Source Index",
            source_links or "No external sources were recorded.",
            "",
        ]
    )
    written.append(write_text(report_path, report_body))
    await upsert_page_from_file(db, safe_path(report_path))

    for idx, source in enumerate(sources[:60], start=1):
        source_type = str(source.get("source") or "source")
        title = _source_title(source, idx)
        url = _source_url(source)
        content = str(source.get("content") or source.get("snippet") or "")
        source_slug = slugify(title, f"source-{idx}")[:90]
        raw_path = f"raw/sources/{date}-{source_type}-{source_slug}-{idx}.md"
        summary_path = f"wiki/sources/{date}-{source_type}-{source_slug}-{idx}.md"

        raw_body = "\n".join(
            [
                frontmatter_block(title, "raw_source", tags=[source_type], sources=[url] if url else []),
                f"# {title}",
                "",
                f"- Source: {source_type}",
                f"- URL: {url or 'N/A'}",
                "",
                content,
                "",
            ]
        )
        written.append(write_text(raw_path, raw_body))

        summary_body = "\n".join(
            [
                frontmatter_block(
                    title,
                    "source",
                    tags=[source_type],
                    sources=[url] if url else [],
                    related=[report_title],
                ),
                f"# {title}",
                "",
                f"Source type: `{source_type}`",
                "",
                f"URL: {url or 'N/A'}",
                "",
                "## Extract",
                content[:1800] or "No content excerpt was recorded.",
                "",
            ]
        )
        written.append(write_text(summary_path, summary_body))
        await upsert_page_from_file(db, safe_path(summary_path))

        source_hash = hashlib.sha256(json.dumps(source, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        db.add(
            WikiSource(
                id=str(uuid.uuid4()),
                research_id=research.id,
                source_type=source_type,
                title=title,
                url=url,
                raw_path=raw_path,
                content_hash=source_hash,
            )
        )

    index_path = "wiki/index.md"
    index_content = read_text(index_path)
    index_link = f"- [[{report_title}]] - {date} - `{research.query}`"
    if index_link not in index_content:
        index_content = index_content.rstrip() + "\n" + index_link + "\n"
        written.append(write_text(index_path, index_content))
        await upsert_page_from_file(db, safe_path(index_path))

    log_path = "wiki/log.md"
    log_content = read_text(log_path).rstrip()
    log_entry = f"\n- {datetime.utcnow().isoformat()} saved research `{research.id}` to [[{report_title}]]"
    written.append(write_text(log_path, log_content + log_entry + "\n"))
    await upsert_page_from_file(db, safe_path(log_path))

    await append_log(
        db,
        "save_research",
        research.id,
        report_path,
        f"Saved research report and {len(sources)} source(s) into Wiki",
    )
    return sorted(set(written))

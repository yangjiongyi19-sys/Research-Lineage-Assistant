from __future__ import annotations

from typing import Any, Dict

from app.services.database import AsyncSessionLocal
from app.services.wiki_search import build_wiki_context


async def wiki_retrieve_node(state: Dict[str, Any]) -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        pages, context, sufficiency = await build_wiki_context(db, state["query"])
        metadata = dict(state.get("metadata", {}))
        metadata["wiki_pages"] = pages
        metadata["wiki_sufficiency"] = sufficiency
        metadata["wiki_context"] = context
        metadata["wiki_context_chars"] = len(context)
        return {
            "wiki_pages": pages,
            "wiki_context": context,
            "wiki_sufficiency": sufficiency,
            "metadata": metadata,
        }

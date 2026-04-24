from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Tuple
import json
import uuid

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.models.research import Research
from app.services.llm import create_llm

_MAX_CONTEXT_CHARS = 24000
_MAX_RECENT_MESSAGES = 12


def utc_now() -> str:
    return datetime.utcnow().isoformat()


def ensure_chat_metadata(metadata: Dict[str, Any] | None) -> Dict[str, Any]:
    data = metadata or {}
    data.setdefault("chat_messages", [])
    data.setdefault("chat_memory_summary", "")
    return data


def get_chat_messages(research: Research) -> List[Dict[str, str]]:
    metadata = ensure_chat_metadata(research.research_metadata)
    return metadata.get("chat_messages", [])


def create_chat_message(role: str, content: str) -> Dict[str, str]:
    return {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "created_at": utc_now(),
    }


def append_chat_message(research: Research, message: Dict[str, str]) -> None:
    metadata = dict(ensure_chat_metadata(research.research_metadata))
    metadata["chat_messages"] = list(metadata.get("chat_messages", []))
    metadata["chat_messages"].append(message)
    research.research_metadata = metadata
    research.updated_at = datetime.utcnow()


def sse_event(event: str, payload: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def stream_research_chat(
    research: Research,
    user_message: str,
) -> AsyncIterator[str]:
    llm = create_llm(temperature=0.2, streaming=True)
    messages = _build_messages(research, user_message)
    async for chunk in llm.astream(messages):
        content = getattr(chunk, "content", "")
        if isinstance(content, list):
            content = "".join(str(item) for item in content)
        if content:
            yield str(content)


def _build_messages(research: Research, user_message: str) -> List[Any]:
    metadata = ensure_chat_metadata(research.research_metadata)
    context = _build_research_context(research, metadata)
    recent_messages = metadata.get("chat_messages", [])[-_MAX_RECENT_MESSAGES:]
    if recent_messages and recent_messages[-1].get("role") == "user":
        if recent_messages[-1].get("content", "").strip() == user_message.strip():
            recent_messages = recent_messages[:-1]

    messages: List[Any] = [
        SystemMessage(
            content=(
                "You are a research follow-up assistant. Answer using the provided research report, "
                "retrieved sources, workflow context, and prior conversation. If the available research "
                "context is insufficient, say that the current research materials do not provide enough "
                "evidence. Do not invent citations. Write in the user's language and use concise Markdown."
            )
        ),
        HumanMessage(content=context),
    ]

    for item in recent_messages:
        role = item.get("role")
        content = item.get("content", "")
        if not content:
            continue
        if role == "assistant":
            messages.append(AIMessage(content=content))
        elif role == "user":
            messages.append(HumanMessage(content=content))

    messages.append(HumanMessage(content=user_message))
    return messages


def _build_research_context(research: Research, metadata: Dict[str, Any]) -> str:
    sections: List[Tuple[str, str]] = [
        ("Original query", research.query or ""),
        ("Final report", research.final_report or ""),
        ("Synthesis", research.synthesized_content or ""),
        ("Workflow task summary", _format_tasks(metadata.get("tasks", []))),
        ("Search sources", _format_sources(research.search_results or [])),
        ("Prior memory summary", metadata.get("chat_memory_summary", "")),
    ]

    parts: List[str] = []
    remaining = _MAX_CONTEXT_CHARS
    for title, content in sections:
        if not content or remaining <= 0:
            continue
        text = f"## {title}\n{content.strip()}\n"
        if len(text) > remaining:
            text = text[:remaining]
        parts.append(text)
        remaining -= len(text)
    return "\n".join(parts)


def _format_tasks(tasks: List[Dict[str, Any]]) -> str:
    lines = []
    for task in tasks:
        summary = task.get("summary") or ""
        status = task.get("status") or "unknown"
        name = task.get("name") or task.get("id") or "task"
        lines.append(f"- {name}: {status}. {summary}".strip())
    return "\n".join(lines)


def _format_sources(sources: List[Dict[str, Any]]) -> str:
    lines = []
    for index, source in enumerate(sources[:30], start=1):
        title = source.get("title") or "Untitled source"
        provider = source.get("source") or "unknown"
        url = source.get("url") or ""
        content = (source.get("content") or "").replace("\n", " ")[:500]
        lines.append(f"[{index}] ({provider}) {title}\nURL: {url}\nExcerpt: {content}")
    return "\n\n".join(lines)

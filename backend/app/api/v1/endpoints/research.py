from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.workflow.graph import should_continue
from app.core.workflow.nodes.analyze import analyze_node
from app.core.workflow.nodes.report import report_node
from app.core.workflow.nodes.search import search_node
from app.core.workflow.nodes.synthesize import synthesize_node
from app.core.workflow.nodes.wiki_retrieve import wiki_retrieve_node
from app.core.workflow.query_planner import build_query_plan, generate_gap_queries
from app.models.research import Research, ResearchStatus
from app.models.schemas import (
    ChatHistoryResponse,
    ChatRequest,
    ResearchCreate,
    ResearchResponse,
    ResearchUpdate,
    WorkflowStartResponse,
)
from app.services.chat import (
    append_chat_message,
    create_chat_message,
    get_chat_messages,
    sse_event,
    stream_research_chat,
)
from app.services.database import get_db
from app.services.wiki_ingest import save_research_to_wiki

router = APIRouter()

_TASKS = [
    ("wiki_retrieve", "Retrieve reusable Wiki context"),
    ("query_understanding", "Understand research intent"),
    ("query_decomposition", "Decompose query into sub-questions"),
    ("query_expansion", "Expand queries for broad retrieval"),
    ("search_exa", "Search public web with Exa MCP"),
    ("search_duckduckgo", "Search public web with DuckDuckGo"),
    ("search_arxiv", "Search academic papers with arXiv"),
    ("search_openalex", "Search academic papers with OpenAlex"),
    ("analyze", "Analyze retrieved sources"),
    ("synthesize", "Synthesize findings"),
    ("report", "Generate Markdown report"),
    ("wiki_ingest", "Save final report into LLM Wiki"),
]


def _utc() -> str:
    return datetime.utcnow().isoformat()


def _initial_metadata() -> Dict[str, Any]:
    return {
        "tasks": [
            {
                "id": task_id,
                "name": name,
                "status": "pending",
                "summary": None,
                "started_at": None,
                "completed_at": None,
                "error": None,
            }
            for task_id, name in _TASKS
        ],
        "logs": [],
        "stream_events": [],
        "stream_seq": 0,
        "tool_errors": [],
    }


def _metadata(research: Research) -> Dict[str, Any]:
    metadata = research.research_metadata or _initial_metadata()
    metadata.setdefault("tasks", _initial_metadata()["tasks"])
    metadata.setdefault("logs", [])
    metadata.setdefault("stream_events", [])
    metadata.setdefault("stream_seq", 0)
    metadata.setdefault("tool_errors", [])
    return metadata


def _set_task(
    metadata: Dict[str, Any],
    task_id: str,
    status: str,
    summary: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    for task in metadata["tasks"]:
        if task["id"] != task_id:
            continue
        task["status"] = status
        if status == "running" and not task.get("started_at"):
            task["started_at"] = _utc()
        if status in {"completed", "failed"}:
            task["completed_at"] = _utc()
        if summary is not None:
            task["summary"] = summary
        if error is not None:
            task["error"] = error
        return


def _add_event(
    metadata: Dict[str, Any],
    event_type: str,
    message: str,
    task_id: Optional[str] = None,
    level: str = "info",
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    timestamp = _utc()
    log = {
        "timestamp": timestamp,
        "level": level,
        "message": message,
        "task_id": task_id,
    }
    metadata["logs"].append(log)
    metadata["logs"] = metadata["logs"][-300:]

    metadata["stream_seq"] = int(metadata.get("stream_seq", 0)) + 1
    metadata["stream_events"].append(
        {
            "seq": metadata["stream_seq"],
            "timestamp": timestamp,
            "type": event_type,
            "message": message,
            "task_id": task_id,
            "level": level,
            "payload": payload or {},
        }
    )
    metadata["stream_events"] = metadata["stream_events"][-500:]


async def _save_progress(
    db: AsyncSession,
    research: Research,
    metadata: Dict[str, Any],
    state: Dict[str, Any],
) -> None:
    research.status = ResearchStatus(state.get("status", research.status.value))
    research.iterations = state.get("iterations", research.iterations)
    research.search_results = state.get("search_results", research.search_results or [])
    research.analyzed_results = state.get("analyzed_results", research.analyzed_results or [])
    if "tool_errors" in state:
        metadata["tool_errors"] = state.get("tool_errors", metadata.get("tool_errors", []))
    research.synthesized_content = state.get("synthesized_content")
    research.final_report = state.get("final_report")
    research.error_message = state.get("error_message")
    research.research_metadata = metadata
    research.updated_at = datetime.utcnow()
    await db.commit()


def _response(research: Research) -> ResearchResponse:
    return ResearchResponse(
        id=research.id,
        title=research.title,
        description=research.description,
        query=research.query,
        status=research.status.value,
        iterations=research.iterations,
        max_iterations=research.max_iterations,
        search_results=research.search_results,
        analyzed_results=research.analyzed_results,
        synthesized_content=research.synthesized_content,
        final_report=research.final_report,
        metadata=research.research_metadata,
        error_message=research.error_message,
        created_at=research.created_at,
        updated_at=research.updated_at,
    )


@router.post("", response_model=ResearchResponse)
async def create_research(data: ResearchCreate, db: AsyncSession = Depends(get_db)):
    try:
        research = Research(
            id=str(uuid.uuid4()),
            title=data.title,
            description=data.description or "",
            query=data.query,
            status=ResearchStatus.PENDING,
            iterations=0,
            max_iterations=data.max_iterations or settings.MAX_ITERATIONS,
            search_results=[],
            analyzed_results=[],
            research_metadata=_initial_metadata(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(research)
        await db.commit()
        await db.refresh(research)
        return _response(research)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create research: {exc}") from exc


@router.get("", response_model=List[ResearchResponse])
async def list_researches(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Research).order_by(Research.created_at.desc()).offset(skip).limit(limit)
    )
    return [_response(research) for research in result.scalars().all()]


@router.get("/{research_id}", response_model=ResearchResponse)
async def get_research(research_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Research).where(Research.id == research_id))
    research = result.scalar_one_or_none()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    return _response(research)


@router.put("/{research_id}", response_model=ResearchResponse)
async def update_research(
    research_id: str,
    data: ResearchUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Research).where(Research.id == research_id))
    research = result.scalar_one_or_none()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")

    if data.title is not None:
        research.title = data.title
    if data.description is not None:
        research.description = data.description
    if data.max_iterations is not None:
        research.max_iterations = data.max_iterations
    research.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(research)
    return _response(research)


@router.delete("/{research_id}")
async def delete_research(research_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(delete(Research).where(Research.id == research_id))
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Research not found")
    return {"message": "Research deleted", "id": research_id}


@router.get("/{research_id}/chat", response_model=ChatHistoryResponse)
async def get_research_chat(research_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Research).where(Research.id == research_id))
    research = result.scalar_one_or_none()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")

    return ChatHistoryResponse(
        research_id=research_id,
        messages=get_chat_messages(research),
    )


@router.post("/{research_id}/chat/stream")
async def stream_research_chat_response(
    research_id: str,
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Research).where(Research.id == research_id))
    research = result.scalar_one_or_none()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    if research.status != ResearchStatus.COMPLETED or not research.final_report:
        raise HTTPException(status_code=400, detail="Chat is available after the final report is generated")

    content = data.message.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    user_message = create_chat_message("user", content)
    append_chat_message(research, user_message)
    await db.commit()

    async def event_stream():
        assistant_content = ""
        try:
            yield sse_event("user_message", {"message": user_message})
            async for chunk in stream_research_chat(research, content):
                assistant_content += chunk
                yield sse_event("delta", {"chunk": chunk})

            assistant_message = create_chat_message("assistant", assistant_content)
            append_chat_message(research, assistant_message)
            await db.commit()
            yield sse_event("done", {"message": assistant_message})
        except Exception as exc:
            await db.rollback()
            yield sse_event("error", {"detail": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{research_id}/start", response_model=WorkflowStartResponse)
async def start_research_workflow(
    research_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Research).where(Research.id == research_id))
    research = result.scalar_one_or_none()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    if research.status not in [ResearchStatus.PENDING, ResearchStatus.ERROR]:
        raise HTTPException(status_code=400, detail="Research workflow is already running or completed")

    metadata = _initial_metadata()
    _add_event(metadata, "workflow_started", "Research workflow started")
    research.status = ResearchStatus.SEARCHING
    research.iterations = 0
    research.search_results = []
    research.analyzed_results = []
    research.synthesized_content = None
    research.final_report = None
    research.error_message = None
    research.research_metadata = metadata
    research.updated_at = datetime.utcnow()
    await db.commit()

    background_tasks.add_task(run_research_workflow, research_id, research.query, research.max_iterations)
    return WorkflowStartResponse(
        research_id=research_id,
        status=research.status.value,
        message="Research workflow started",
    )


@router.post("/{research_id}/confirm-report", response_model=WorkflowStartResponse)
async def confirm_research_report(
    research_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Research).where(Research.id == research_id))
    research = result.scalar_one_or_none()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    if research.status != ResearchStatus.AWAITING_REPORT:
        raise HTTPException(status_code=400, detail="Report can only be confirmed after research synthesis")

    metadata = _metadata(research)
    report_task = next((task for task in metadata.get("tasks", []) if task.get("id") == "report"), None)
    if report_task and report_task.get("status") == "running":
        raise HTTPException(status_code=400, detail="Report generation is already running")

    _set_task(metadata, "report", "running")
    _add_event(metadata, "report_confirmed", "User confirmed final report generation", "report")
    research.status = ResearchStatus.SYNTHESIZING
    research.research_metadata = metadata
    research.updated_at = datetime.utcnow()
    await db.commit()

    background_tasks.add_task(generate_confirmed_report, research_id)
    return WorkflowStartResponse(
        research_id=research_id,
        status=research.status.value,
        message="Final report generation confirmed",
    )


async def run_research_workflow(research_id: str, query: str, max_iterations: int):
    from app.services.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Research).where(Research.id == research_id))
        research = result.scalar_one_or_none()
        if not research:
            return

        metadata = _metadata(research)
        state: Dict[str, Any] = {
            "query": query,
            "research_id": research_id,
            "depth": 3,
            "iterations": 0,
            "max_iterations": max_iterations,
            "search_results": [],
            "tool_errors": [],
            "wiki_pages": [],
            "wiki_context": "",
            "wiki_sufficiency": "insufficient",
            "wiki_updated_pages": [],
            "analyzed_results": [],
            "synthesized_content": "",
            "knowledge_gaps": [],
            "final_report": None,
            "sources": [],
            "status": "searching",
            "error_message": None,
            "metadata": {},
        }

        try:
            _set_task(metadata, "wiki_retrieve", "running")
            _add_event(metadata, "task_started", "Retrieving reusable context from LLM Wiki", "wiki_retrieve")
            await _save_progress(db, research, metadata, state)
            state.update(await wiki_retrieve_node(state))
            _merge_node_metadata(metadata, state.get("metadata", {}))
            wiki_pages = state.get("wiki_pages", [])
            _set_task(
                metadata,
                "wiki_retrieve",
                "completed",
                summary=f"{len(wiki_pages)} page(s), {state.get('wiki_sufficiency', 'insufficient')} context",
            )
            _add_event(
                metadata,
                "wiki_context_ready",
                f"Retrieved {len(wiki_pages)} Wiki page(s) as prior context",
                "wiki_retrieve",
                payload={"pages": wiki_pages, "sufficiency": state.get("wiki_sufficiency")},
            )
            await _save_progress(db, research, metadata, state)

            while True:
                semantic_task_status = "running" if state["iterations"] == 0 else "completed"
                for task_id in ["query_understanding", "query_decomposition", "query_expansion"]:
                    _set_task(metadata, task_id, semantic_task_status)
                _add_event(metadata, "task_started", "Parsing and expanding the research query", "query_understanding")

                analysis_gaps = []
                if state["iterations"] > 0:
                    analysis_gaps = generate_gap_queries(
                        state.get("analyzed_results", []),
                        state.get("metadata", {}).get("query_plan", {}).get("semantic", {}),
                    )
                    if analysis_gaps:
                        _add_event(
                            metadata,
                            "query_gap_generated",
                            f"Generated {len(analysis_gaps)} follow-up query gap(s)",
                            "query_expansion",
                            payload={"queries": analysis_gaps},
                        )

                query_plan = build_query_plan(query, state["iterations"], analysis_gaps)
                state["metadata"]["query_plan"] = query_plan
                _merge_node_metadata(metadata, state["metadata"])
                _set_task(
                    metadata,
                    "query_understanding",
                    "completed",
                    summary=f"{query_plan['semantic']['core_tech']} / {query_plan['semantic']['application_domain']}",
                )
                _set_task(
                    metadata,
                    "query_decomposition",
                    "completed",
                    summary=f"{len(query_plan['sub_questions'])} sub-question(s)",
                )
                expanded_count = sum(
                    len(item["academic_queries"]) + len(item["web_queries"])
                    for item in query_plan["expanded_queries"]
                )
                _set_task(
                    metadata,
                    "query_expansion",
                    "completed",
                    summary=f"{expanded_count} expanded query expression(s)",
                )
                _add_event(
                    metadata,
                    "query_plan_ready",
                    f"Query plan ready with {len(query_plan['sub_questions'])} sub-questions and {expanded_count} expanded queries",
                    "query_expansion",
                    payload=query_plan,
                )
                await _save_progress(db, research, metadata, state)

                for task_id in ["search_exa", "search_duckduckgo", "search_arxiv", "search_openalex"]:
                    _set_task(metadata, task_id, "running")
                _add_event(metadata, "task_started", "Searching Exa, DuckDuckGo, arXiv, and OpenAlex", "search_exa")
                await _save_progress(db, research, metadata, state)

                search_result = await search_node(state)
                state.update(search_result)
                source_counts = _source_counts(state.get("search_results", []))
                errors = state.get("metadata", {}).get("last_search_errors", [])
                _merge_node_metadata(metadata, state.get("metadata", {}))
                for task_id, source in [
                    ("search_exa", "exa"),
                    ("search_duckduckgo", "duckduckgo"),
                    ("search_arxiv", "arxiv"),
                    ("search_openalex", "openalex"),
                ]:
                    count = source_counts.get(source, 0)
                    source_errors = [error for error in errors if source in error.lower()]
                    failed = bool(source_errors)
                    _set_task(
                        metadata,
                        task_id,
                        "failed" if failed else "completed",
                        summary=f"{count} result(s) retained",
                        error="; ".join(source_errors) or None,
                    )
                _add_event(metadata, "sources_found", f"Collected {len(state.get('search_results', []))} sources")
                await _save_progress(db, research, metadata, state)
                if state.get("status") == "error":
                    break

                _set_task(metadata, "analyze", "running")
                _add_event(metadata, "task_started", "Analyzing retrieved sources", "analyze")
                state.update(await analyze_node(state))
                _set_task(
                    metadata,
                    "analyze",
                    "completed" if state.get("status") != "error" else "failed",
                    summary=f"{len(state.get('analyzed_results', []))} analysis result(s)",
                    error=state.get("error_message"),
                )
                await _save_progress(db, research, metadata, state)
                if state.get("status") == "error":
                    break

                _set_task(metadata, "synthesize", "running")
                _add_event(metadata, "task_started", "Synthesizing findings", "synthesize")
                state.update(await synthesize_node(state))
                _set_task(
                    metadata,
                    "synthesize",
                    "completed" if state.get("status") != "error" else "failed",
                    summary=f"{len(state.get('synthesized_content') or '')} characters",
                    error=state.get("error_message"),
                )
                await _save_progress(db, research, metadata, state)

                if should_continue(state) != "continue":
                    break

            if state.get("status") == "error":
                _set_task(metadata, "report", "failed", error=state.get("error_message"))
                _add_event(
                    metadata,
                    "workflow_failed",
                    state.get("error_message", "Research workflow failed"),
                    level="error",
                )
            else:
                state["status"] = "awaiting_report"
                _set_task(metadata, "report", "pending", summary="Ready for user confirmation")
                _add_event(
                    metadata,
                    "awaiting_report_confirmation",
                    "Research synthesis is ready. Waiting for user confirmation to generate the final report.",
                    "report",
                )
            await _save_progress(db, research, metadata, state)
        except Exception as exc:
            state["status"] = "error"
            state["error_message"] = str(exc)
            _add_event(metadata, "workflow_failed", str(exc), level="error")
            await _save_progress(db, research, metadata, state)


async def generate_confirmed_report(research_id: str):
    from app.services.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Research).where(Research.id == research_id))
        research = result.scalar_one_or_none()
        if not research:
            return

        metadata = _metadata(research)
        if research.status not in {ResearchStatus.AWAITING_REPORT, ResearchStatus.SYNTHESIZING}:
            return

        state = _state_from_research(research)
        try:
            _set_task(metadata, "report", "running")
            _add_event(metadata, "task_started", "Generating structured Markdown report", "report")
            research.research_metadata = metadata
            research.updated_at = datetime.utcnow()
            await db.commit()

            state.update(await report_node(state))
            if state.get("final_report"):
                _add_report_stream(metadata, state["final_report"])
            _set_task(
                metadata,
                "report",
                "completed" if state.get("status") == "completed" else "failed",
                summary="Markdown report generated" if state.get("final_report") else None,
                error=state.get("error_message"),
            )
            if state.get("status") == "completed" and state.get("final_report"):
                _set_task(metadata, "wiki_ingest", "running")
                _add_event(metadata, "task_started", "Saving final report into LLM Wiki", "wiki_ingest")
                try:
                    research.final_report = state.get("final_report")
                    research.search_results = state.get("search_results", [])
                    written_paths = await save_research_to_wiki(db, research)
                    state["wiki_updated_pages"] = written_paths
                    state.setdefault("metadata", {})["wiki_updated_pages"] = written_paths
                    _merge_node_metadata(metadata, state.get("metadata", {}))
                    _set_task(
                        metadata,
                        "wiki_ingest",
                        "completed",
                        summary=f"{len(written_paths)} file(s) written",
                    )
                    _add_event(
                        metadata,
                        "wiki_saved",
                        f"Saved report into LLM Wiki ({len(written_paths)} file(s))",
                        "wiki_ingest",
                        payload={"paths": written_paths},
                    )
                except Exception as exc:
                    _set_task(metadata, "wiki_ingest", "failed", error=str(exc))
                    _add_event(metadata, "wiki_save_failed", str(exc), "wiki_ingest", level="warning")
            _add_event(
                metadata,
                "workflow_completed" if state.get("status") == "completed" else "workflow_failed",
                "Research workflow completed"
                if state.get("status") == "completed"
                else state.get("error_message", "Research workflow failed"),
                level="info" if state.get("status") == "completed" else "error",
            )
            await _save_progress(db, research, metadata, state)
        except Exception as exc:
            state["status"] = "error"
            state["error_message"] = str(exc)
            _set_task(metadata, "report", "failed", error=str(exc))
            _add_event(metadata, "workflow_failed", str(exc), "report", level="error")
            await _save_progress(db, research, metadata, state)


def _state_from_research(research: Research) -> Dict[str, Any]:
    metadata = _metadata(research)
    return {
        "query": research.query,
        "research_id": research.id,
        "depth": 3,
        "iterations": research.iterations,
        "max_iterations": research.max_iterations,
        "search_results": research.search_results or [],
        "tool_errors": metadata.get("tool_errors", []),
        "wiki_pages": metadata.get("wiki_pages", []),
        "wiki_context": metadata.get("wiki_context", ""),
        "wiki_sufficiency": metadata.get("wiki_sufficiency", "insufficient"),
        "wiki_updated_pages": metadata.get("wiki_updated_pages", []),
        "analyzed_results": research.analyzed_results or [],
        "synthesized_content": research.synthesized_content or "",
        "knowledge_gaps": metadata.get("last_knowledge_gaps", []),
        "final_report": research.final_report,
        "sources": [],
        "status": research.status.value,
        "error_message": research.error_message,
        "metadata": metadata,
    }


def _source_counts(search_results: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in search_results:
        source = item.get("source", "unknown")
        counts[source] = counts.get(source, 0) + 1
    return counts


def _merge_node_metadata(metadata: Dict[str, Any], node_metadata: Dict[str, Any]) -> None:
    for key, value in node_metadata.items():
        if key not in {"tasks", "logs", "stream_events", "stream_seq"}:
            metadata[key] = value


def _add_report_stream(metadata: Dict[str, Any], report: str) -> None:
    for chunk in report.splitlines(keepends=True):
        _add_event(
            metadata,
            "report_chunk",
            "Report chunk generated",
            "report",
            payload={"chunk": chunk},
        )


@router.get("/config/llm")
async def get_llm_config():
    from app.services.llm import get_llm_info

    return {
        "llm_config": get_llm_info(),
        "message": "LLM configuration",
    }

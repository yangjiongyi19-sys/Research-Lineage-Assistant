import asyncio
import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import Research, ResearchStatus
from app.models.schemas import WorkflowState
from app.services.database import AsyncSessionLocal, get_db

router = APIRouter()


@router.get("/{research_id}/state", response_model=WorkflowState)
async def get_workflow_state(
    research_id: str,
    db: AsyncSession = Depends(get_db),
):
    research = await _get_research(db, research_id)
    metadata = _metadata(research)
    return WorkflowState(
        research_id=research_id,
        query=research.query,
        status=research.status.value,
        iterations=research.iterations,
        max_iterations=research.max_iterations,
        search_results=research.search_results,
        analyzed_results=research.analyzed_results,
        synthesized_content=research.synthesized_content,
        final_report=research.final_report,
        error_message=research.error_message,
        progress_percentage=calculate_progress_from_research(research),
        tasks=metadata.get("tasks", []),
        logs=metadata.get("logs", []),
        tool_errors=metadata.get("tool_errors", []),
        stream_events=metadata.get("stream_events", []),
    )


@router.get("/{research_id}/stream")
async def stream_workflow(research_id: str, request: Request):
    async def event_generator():
        last_seq = 0
        while True:
            if await request.is_disconnected():
                break

            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Research).where(Research.id == research_id))
                research = result.scalar_one_or_none()
                if not research:
                    yield _sse("error", {"message": "Research not found"})
                    break

                metadata = _metadata(research)
                events = [
                    event
                    for event in metadata.get("stream_events", [])
                    if int(event.get("seq", 0)) > last_seq
                ]
                for event in events:
                    last_seq = int(event.get("seq", last_seq))
                    yield _sse(event.get("type", "message"), event)

                yield _sse(
                    "state",
                    {
                        "status": research.status.value,
                        "progress_percentage": calculate_progress_from_research(research),
                        "tasks": metadata.get("tasks", []),
                        "logs": metadata.get("logs", [])[-50:],
                        "tool_errors": metadata.get("tool_errors", [])[-50:],
                        "final_report": research.final_report,
                        "error_message": research.error_message,
                    },
                )

                if research.status in {
                    ResearchStatus.AWAITING_REPORT,
                    ResearchStatus.COMPLETED,
                    ResearchStatus.ERROR,
                }:
                    break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/{research_id}/report")
async def get_report(
    research_id: str,
    format: str = "markdown",
    db: AsyncSession = Depends(get_db),
):
    research = await _get_research(db, research_id)
    if not research.final_report:
        raise HTTPException(status_code=400, detail="Report is not ready")

    return {
        "content": research.final_report,
        "format": format,
        "research_id": research_id,
        "sources": research.search_results or [],
        "tasks": _metadata(research).get("tasks", []),
    }


@router.post("/{research_id}/stop")
async def stop_workflow(
    research_id: str,
    db: AsyncSession = Depends(get_db),
):
    research = await _get_research(db, research_id)
    research.status = ResearchStatus.COMPLETED
    await db.commit()
    return {"message": "Workflow stopped", "research_id": research_id}


async def _get_research(db: AsyncSession, research_id: str) -> Research:
    result = await db.execute(select(Research).where(Research.id == research_id))
    research = result.scalar_one_or_none()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    return research


def _metadata(research: Research) -> Dict[str, Any]:
    return research.research_metadata or {
        "tasks": [],
        "logs": [],
        "stream_events": [],
    }


def _sse(event: str, payload: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def calculate_progress_from_research(research: Research) -> int:
    metadata = _metadata(research)
    tasks = metadata.get("tasks", [])
    if tasks:
        completed = sum(1 for task in tasks if task.get("status") == "completed")
        failed = sum(1 for task in tasks if task.get("status") == "failed")
        if research.status == ResearchStatus.ERROR:
            return int(((completed + failed) / len(tasks)) * 100)
        return int((completed / len(tasks)) * 100)

    progress_map = {
        ResearchStatus.PENDING: 0,
        ResearchStatus.SEARCHING: 25,
        ResearchStatus.ANALYZING: 50,
        ResearchStatus.SYNTHESIZING: 75,
        ResearchStatus.AWAITING_REPORT: 90,
        ResearchStatus.COMPLETED: 100,
        ResearchStatus.ERROR: 0,
    }
    return progress_map.get(research.status, 0)

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ResearchStatus(str, Enum):
    PENDING = "pending"
    SEARCHING = "searching"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    AWAITING_REPORT = "awaiting_report"
    COMPLETED = "completed"
    ERROR = "error"


class SearchResult(BaseModel):
    source: str
    title: str
    content: str
    url: str
    relevance_score: float = Field(..., ge=0)


class AnalysisResult(BaseModel):
    key_points: List[str] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)
    source_ids: List[str] = Field(default_factory=list)


class WorkflowTask(BaseModel):
    id: str
    name: str
    status: str
    summary: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class ProgressLog(BaseModel):
    timestamp: str
    level: str = "info"
    message: str
    task_id: Optional[str] = None


class ResearchCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    query: str = Field(..., min_length=1)
    max_iterations: int = Field(3, ge=1, le=5)


class ResearchUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    max_iterations: Optional[int] = Field(None, ge=1, le=5)


class ResearchResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    query: str
    status: ResearchStatus
    iterations: int
    max_iterations: int
    search_results: Optional[List[Dict[str, Any]]]
    analyzed_results: Optional[List[Dict[str, Any]]]
    synthesized_content: Optional[str]
    final_report: Optional[str]
    metadata: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowState(BaseModel):
    research_id: str
    query: str
    status: ResearchStatus
    iterations: int
    max_iterations: int
    search_results: Optional[List[SearchResult]]
    analyzed_results: Optional[List[AnalysisResult]]
    synthesized_content: Optional[str]
    final_report: Optional[str]
    error_message: Optional[str]
    progress_percentage: int = Field(0, ge=0, le=100)
    tasks: List[WorkflowTask] = Field(default_factory=list)
    logs: List[ProgressLog] = Field(default_factory=list)
    tool_errors: List[Dict[str, Any]] = Field(default_factory=list)
    stream_events: List[Dict[str, Any]] = Field(default_factory=list)


class WorkflowStartResponse(BaseModel):
    research_id: str
    status: ResearchStatus
    message: str


class ChatMessage(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)


class ChatHistoryResponse(BaseModel):
    research_id: str
    messages: List[ChatMessage] = Field(default_factory=list)


class WikiPageResponse(BaseModel):
    id: str
    title: str
    path: str
    page_type: str
    summary: Optional[str] = None
    content: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    related: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WikiSearchResult(BaseModel):
    id: str
    title: str
    path: str
    page_type: str
    summary: Optional[str] = None
    snippet: str = ""
    score: float = 0


class WikiSaveResponse(BaseModel):
    research_id: Optional[str] = None
    written_paths: List[str] = Field(default_factory=list)
    message: str


class WikiLogResponse(BaseModel):
    id: str
    action_type: str
    research_id: Optional[str] = None
    page_path: Optional[str] = None
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class WikiLintResult(BaseModel):
    type: str
    severity: str
    page: str
    detail: str
    affected_pages: List[str] = Field(default_factory=list)


class ReportExportRequest(BaseModel):
    format: str = Field("markdown", pattern="^(markdown|html|pdf)$")
    include_sources: bool = True
    template: Optional[str] = None

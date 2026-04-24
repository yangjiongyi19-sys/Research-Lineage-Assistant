export enum ResearchStatus {
  PENDING = 'pending',
  SEARCHING = 'searching',
  ANALYZING = 'analyzing',
  SYNTHESIZING = 'synthesizing',
  AWAITING_REPORT = 'awaiting_report',
  COMPLETED = 'completed',
  ERROR = 'error',
  FAILED = 'failed'
}

export interface SearchResult {
  source: string
  title: string
  content: string
  url: string
  relevance_score: number
}

export interface AnalysisResult {
  key_points: string[]
  entities: string[]
  confidence: number
  source_ids?: string[]
}

export interface Research {
  id: string
  title: string
  description: string | null
  query: string
  status: ResearchStatus
  iterations: number
  max_iterations: number
  search_results: SearchResult[] | null
  analyzed_results: AnalysisResult[] | null
  synthesized_content: string | null
  final_report: string | null
  metadata: ResearchMetadata | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export type ResearchDetail = Research

export interface CreateResearchRequest {
  title: string
  description?: string
  query: string
  max_iterations?: number
}

export interface WorkflowState {
  research_id: string
  query: string
  status: ResearchStatus
  iterations: number
  max_iterations: number
  search_results: SearchResult[] | null
  analyzed_results: AnalysisResult[] | null
  synthesized_content: string | null
  final_report: string | null
  error_message: string | null
  progress_percentage: number
  tasks: WorkflowTask[]
  logs: ProgressLog[]
  tool_errors: ToolError[]
  stream_events: StreamEvent[]
}

export interface ResearchReportResponse {
  content: string
  format: string
  research_id: string
  sources: SearchResult[]
}

export enum StepStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

export interface WorkflowStep {
  id: string
  name: string
  status: StepStatus
  order: number
}

export type WorkflowTaskStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface Report {
  id: string
  research_id: string
  content: string
  sources: SearchResult[]
  created_at?: string
}

export interface ResearchMetadata {
  tasks?: WorkflowTask[]
  logs?: ProgressLog[]
  tool_errors?: ToolError[]
  stream_events?: StreamEvent[]
  stream_seq?: number
  [key: string]: unknown
}

export interface ProgressLog {
  timestamp: string
  level: string
  message: string
  task_id?: string | null
}

export interface StreamEvent {
  seq: number
  timestamp: string
  type: string
  message: string
  task_id?: string | null
  level: string
  payload?: {
    chunk?: string
    [key: string]: unknown
  }
}

export interface WorkflowTask {
  id: string
  name: string
  status: WorkflowTaskStatus
  summary?: string | null
  started_at?: string | null
  completed_at?: string | null
  error?: string | null
}

export interface ToolError {
  tool: string
  query: string
  error_type: string
  error_message: string
  retry_count: number
}

export type MessageRole = 'user' | 'assistant'

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  created_at: string
}

export interface ChatHistoryResponse {
  research_id: string
  messages: ChatMessage[]
}

export interface WikiPage {
  id: string
  title: string
  path: string
  page_type: string
  summary: string | null
  content: string | null
  tags: string[]
  sources: string[]
  related: string[]
  created_at: string
  updated_at: string
}

export interface WikiSearchResult {
  id: string
  title: string
  path: string
  page_type: string
  summary: string | null
  snippet: string
  score: number
}

export interface WikiLog {
  id: string
  action_type: string
  research_id: string | null
  page_path: string | null
  message: string
  created_at: string
}

export interface WikiSaveResponse {
  research_id: string | null
  written_paths: string[]
  message: string
}

export interface WikiLintResult {
  type: string
  severity: string
  page: string
  detail: string
  affected_pages: string[]
}

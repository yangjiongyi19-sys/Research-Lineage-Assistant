# Research Lineage Assistant

AI deep research assistant built with Vue 3, FastAPI, LangGraph, SQLite, and multi-source search.

## What it does

1. You submit a research query.
2. The backend builds a structured query plan.
3. The workflow searches multiple sources in parallel:
   - Exa MCP
   - DuckDuckGo
   - arXiv API
   - OpenAlex
4. Results are analyzed and synthesized.
5. The workflow pauses at `awaiting_report` so you can confirm final report generation.
6. After the report is generated, you can continue follow-up chat with conversation memory.
7. Final reports and source summaries are also written into a local LLM Wiki workspace for reuse.

## Tech Stack

- Frontend: Vue 3 + TypeScript + Vite + Pinia + Vue Router
- Backend: FastAPI + SQLAlchemy 2.0 + LangGraph
- Storage: SQLite
- Search: Exa MCP, DuckDuckGo, arXiv, OpenAlex
- Knowledge memory: local Markdown LLM Wiki workspace with FTS5 search

## Project Layout

```text
Research Lineage Assistant/
|- backend/
|  |- app/
|  |  |- api/v1/endpoints/   # REST and SSE endpoints
|  |  |- core/workflow/      # LangGraph state, graph, nodes, query planning
|  |  |- models/             # SQLAlchemy and Pydantic schemas
|  |  `- services/           # LLM, search clients, chat, Wiki, DB
|  `- wiki_workspace/        # Generated Markdown wiki workspace
|- frontend/
|  `- src/
|     |- components/
|     |- stores/
|     |- views/
|     `- services/api.ts
`- docs/
```

## Key Features

- Iterative deep research loop: search -> analyze -> synthesize -> continue or finalize.
- Query understanding and decomposition into sub-questions.
- Parallel multi-source retrieval.
- Guarded search calls with retry and fallback handling.
- Streaming workflow state updates in the UI.
- Final report generation in Markdown.
- Follow-up chat after the report is ready.
- LLM Wiki integration:
  - retrieves reusable Wiki context before search
  - saves final reports and source summaries back into Wiki
  - supports Wiki search, reindex, and lint endpoints

## Local Setup

### Backend

```powershell
cd backend
conda activate research_agent
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.
Backend runs on `http://localhost:8000`.

## Run Both

If you prefer the combined launcher:

```powershell
start.bat all
```

If that script fails on Windows batch parsing, start the two services manually using the commands above.

## Environment Variables

Backend config lives in `backend/.env`.

Common fields:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

BAILIAN_API_KEY=your_key
BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
BAILIAN_MODEL=qwen-turbo

EXA_API_KEY=
EXA_MCP_URL=https://mcp.exa.ai/mcp

DATABASE_URL=sqlite+aiosqlite:///./research.db
WIKI_WORKSPACE_PATH=./wiki_workspace
MAX_ITERATIONS=3
SEARCH_RESULTS_LIMIT=5
```

Notes:

- Exa MCP supports a free tier and does not require a key for basic use.
- DuckDuckGo, arXiv, and OpenAlex do not require API keys.

## Main API Endpoints

### Research

- `POST /api/v1/research`
- `GET /api/v1/research`
- `GET /api/v1/research/{research_id}`
- `PUT /api/v1/research/{research_id}`
- `DELETE /api/v1/research/{research_id}`
- `POST /api/v1/research/{research_id}/start`
- `POST /api/v1/research/{research_id}/confirm-report`
- `GET /api/v1/research/{research_id}/chat`
- `POST /api/v1/research/{research_id}/chat/stream`

### Workflow

- `GET /api/v1/workflow/{research_id}/state`
- `GET /api/v1/workflow/{research_id}/stream`
- `GET /api/v1/workflow/{research_id}/report`
- `POST /api/v1/workflow/{research_id}/stop`

### Wiki

- `GET /api/v1/wiki/pages`
- `GET /api/v1/wiki/pages/{page_id}`
- `GET /api/v1/wiki/search?query=...`
- `GET /api/v1/wiki/logs`
- `POST /api/v1/wiki/reindex`
- `POST /api/v1/wiki/lint`
- `POST /api/v1/wiki/research/{research_id}/save`

## Workflow Summary

```text
User query
-> Create Research row
-> Retrieve reusable Wiki context
-> Intent understanding
-> Query decomposition
-> Query expansion
-> Parallel search
   - Exa MCP
   - DuckDuckGo
   - arXiv
   - OpenAlex
-> Analyze results
-> Synthesize findings
-> If needed, generate gap queries and search again
-> Set status = awaiting_report
-> User confirms final report
-> Generate Markdown report
-> Save report and source summaries to Wiki
-> Set status = completed
-> Follow-up chat with report and context memory
```

## Verification

Recommended checks:

```powershell
conda run -n research_agent python -c "from app.main import app; print('backend import ok')"
cd frontend
cmd /c npx tsc --noEmit
cmd /c npx vite build
```

## Notes

- SQLite tables are created automatically at startup.
- The local wiki workspace is generated under `backend/wiki_workspace/`.
- The frontend is intentionally ChatGPT-like: sidebar, task list, report panel, and follow-up chat.

# Research Lineage Assistant

一个基于 Vue 3、FastAPI、LangGraph、SQLite 和多源检索的深度研究助手。

## 功能概览

1. 用户输入研究问题。
2. 后端生成结构化查询计划。
3. 工作流并行检索多个来源：
   - Exa MCP
   - DuckDuckGo
   - arXiv API
   - OpenAlex
4. 系统分析并综合结果。
5. 工作流会停在 `awaiting_report`，等待用户确认生成最终报告。
6. 最终报告生成后，可继续进行带上下文记忆的追问。
7. 最终报告和来源摘要会写入本地 LLM Wiki 工作区，供后续复用。

## 技术栈

- 前端：Vue 3 + TypeScript + Vite + Pinia + Vue Router
- 后端：FastAPI + SQLAlchemy 2.0 + LangGraph
- 存储：SQLite
- 检索：Exa MCP、DuckDuckGo、arXiv、OpenAlex
- 知识记忆：本地 Markdown LLM Wiki 工作区，支持 FTS5 检索

## 项目结构

```text
Research Lineage Assistant/
|- backend/
|  |- app/
|  |  |- api/v1/endpoints/   # REST 和 SSE 接口
|  |  |- core/workflow/      # LangGraph 状态、图、节点、查询规划
|  |  |- models/             # SQLAlchemy 与 Pydantic schema
|  |  `- services/           # LLM、检索、聊天、Wiki、数据库
|  `- wiki_workspace/        # 自动生成的 Markdown Wiki 工作区
|- frontend/
|  `- src/
|     |- components/
|     |- stores/
|     |- views/
|     `- services/api.ts
`- docs/
```

## 核心能力

- 迭代式深度研究流程：检索 -> 分析 -> 综合 -> 继续或结束。
- 查询语义理解与子问题拆解。
- 多来源并行检索。
- 带重试和降级的安全工具调用。
- 前端流式展示工作流状态。
- Markdown 结构化最终报告。
- 报告完成后的追问聊天。
- LLM Wiki 集成：
  - 搜索前先读取可复用 Wiki 上下文
  - 最终报告和来源摘要自动写回 Wiki
  - 支持 Wiki 搜索、重建索引和 lint 检查

## 本地启动

### 后端

```powershell
cd backend
conda activate research_agent
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```powershell
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`。  
后端默认运行在 `http://localhost:8000`。

## 同时启动前后端

如果需要批处理脚本：

```powershell
start.bat all
```

如果脚本在 Windows 上解析失败，直接使用上面的后端和前端命令分别启动。

## 环境变量

后端配置位于 `backend/.env`。

常见配置如下：

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

说明：

- Exa MCP 支持免费层，不需要 API key 也可用于基础检索。
- DuckDuckGo、arXiv、OpenAlex 均不需要 API key。

## 主要 API

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

## 工作流摘要

```text
用户输入 query
-> 创建 Research 记录
-> 读取可复用 Wiki 上下文
-> 语义理解
-> 查询拆解
-> 查询扩展
-> 并行检索
   - Exa MCP
   - DuckDuckGo
   - arXiv
   - OpenAlex
-> 分析结果
-> 综合总结
-> 如有需要，生成 gap queries 并继续检索
-> 状态切换为 awaiting_report
-> 用户确认生成最终报告
-> 生成 Markdown 报告
-> 保存报告和来源摘要到 Wiki
-> 状态切换为 completed
-> 基于报告和上下文的追问聊天
```

## 验证命令

```powershell
conda run -n research_agent python -c "from app.main import app; print('backend import ok')"
cd frontend
cmd /c npx tsc --noEmit
cmd /c npx vite build
```

## 备注

- SQLite 表会在启动时自动创建。
- 本地 Wiki 工作区默认生成在 `backend/wiki_workspace/`。
- 前端界面保持 ChatGPT 风格：侧边栏、任务列表、报告面板、追问聊天。

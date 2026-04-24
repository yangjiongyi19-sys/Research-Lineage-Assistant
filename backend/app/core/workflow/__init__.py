"""研究工作流核心模块。

提供基于 LangGraph 的迭代研究工作流，支持：
- 多源搜索 (Tavily)
- LLM 驱动的分析
- 多轮综合与迭代
- 自动报告生成

使用示例::

    from app.core.workflow import create_research_graph

    graph = create_research_graph()

    result = await graph.ainvoke({
        "query": "量子计算最新进展",
        "depth": 3,
        "iterations": 0,
        "max_iterations": 3,
        "search_results": [],
        "analyzed_results": [],
        "synthesized_content": "",
        "final_report": "",
        "status": "pending",
        "error_message": None,
        "metadata": {},
    })
"""

from .state import ResearchState, SearchResult, AnalysisResult
from .graph import create_research_graph, should_continue

__all__ = [
    "ResearchState",
    "SearchResult",
    "AnalysisResult",
    "create_research_graph",
    "should_continue",
]
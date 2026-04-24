"""研究工作流状态定义。

定义 LangGraph StateGraph 中各节点间传递的状态类型，
包括搜索结果、分析结果和完整的研究状态。
"""

from typing import TypedDict, List, Optional, Dict, Any


class SearchResult(TypedDict):
    """单条搜索结果。

    Attributes:
        source: 搜索来源标识（如 "tavily", "arxiv" 等）
        title: 结果标题
        content: 结果正文内容
        url: 原始链接
        relevance_score: 与查询的相关性评分 (0.0 ~ 1.0)
    """

    source: str
    title: str
    content: str
    url: str
    relevance_score: float


class AnalysisResult(TypedDict):
    """单条分析结果。

    Attributes:
        key_points: 从搜索结果中提取的关键要点
        entities: 识别出的实体列表（人名、机构、术语等）
        confidence: 分析置信度 (0.0 ~ 1.0)
    """

    key_points: List[str]
    entities: List[str]
    confidence: float


class ToolError(TypedDict):
    tool: str
    query: str
    error_type: str
    error_message: str
    retry_count: int


class ResearchState(TypedDict):
    """研究工作流的核心状态对象。

    在 LangGraph StateGraph 的各节点之间传递，
    贯穿搜索 → 分析 → 综合 → 报告的完整生命周期。

    Attributes:
        query: 研究主题或问题
        depth: 研究深度 (1-5)，数值越大搜索越深入
        iterations: 当前已完成迭代次数
        max_iterations: 允许的最大迭代次数
        search_results: 累积的搜索结果列表
        analyzed_results: 累积的分析结果列表
        synthesized_content: 综合后的内容文本
        final_report: 最终生成的研究报告
        status: 当前状态，取值为 pending / searching / analyzing /
                synthesizing / completed / error
        error_message: 错误信息（仅在 status 为 error 时有值）
        metadata: 额外元数据，可存储任意辅助信息
    """

    query: str
    depth: int
    iterations: int
    max_iterations: int
    search_results: List[SearchResult]
    tool_errors: List[ToolError]
    wiki_pages: List[Dict[str, Any]]
    wiki_context: str
    wiki_sufficiency: str
    wiki_updated_pages: List[str]
    analyzed_results: List[AnalysisResult]
    synthesized_content: str
    final_report: str
    status: str
    error_message: Optional[str]
    metadata: Dict[str, Any]

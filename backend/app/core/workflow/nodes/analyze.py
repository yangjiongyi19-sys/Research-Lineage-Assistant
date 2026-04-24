"""分析节点 —— 对搜索结果进行深度分析。

使用 LLM 从搜索结果中提取关键要点、识别实体，
并评估信息质量与置信度。
"""

import json
import logging
from typing import List

from app.services.llm import create_llm
from ..state import AnalysisResult, ResearchState, SearchResult

logger = logging.getLogger(__name__)

_ANALYZE_PROMPT = """\
你是一位严谨的研究分析师。请对以下搜索结果进行深度分析。

研究主题: {query}

搜索结果:
{search_content}

请按以下 JSON 格式输出（不要输出其他内容）:
{{
    "key_points": ["要点1", "要点2", ...],
    "entities": ["实体1", "实体2", ...],
    "confidence": 0.85
}}

要求:
- key_points: 从搜索结果中提取 3-10 个关键要点
- entities: 识别出的人名、机构、术语、技术等实体
- confidence: 基于信息完整性和一致性给出的置信度 (0.0-1.0)
"""


def _format_search_results(results: List[SearchResult]) -> str:
    """将搜索结果格式化为可读文本供 LLM 分析。

    Args:
        results: SearchResult 列表

    Returns:
        格式化后的文本
    """
    parts: List[str] = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[{i}] (来源: {r['source']}, 相关度: {r['relevance_score']:.2f})\n"
            f"标题: {r['title']}\n"
            f"内容: {r['content']}\n"
            f"链接: {r['url']}"
        )
    return "\n\n".join(parts)


def _parse_analysis_response(response_text: str) -> AnalysisResult:
    """解析 LLM 返回的 JSON 分析结果。

    Args:
        response_text: LLM 返回的文本

    Returns:
        标准化的 AnalysisResult
    """
    try:
        data = json.loads(response_text)
        return AnalysisResult(
            key_points=data.get("key_points", []),
            entities=data.get("entities", []),
            confidence=float(data.get("confidence", 0.0)),
        )
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("analyze_node: failed to parse LLM response: %s", exc)
        return AnalysisResult(
            key_points=[],
            entities=[],
            confidence=0.0,
        )


async def analyze_node(state: ResearchState) -> dict:
    """分析搜索结果。

    工作流程：
    1. 将搜索结果格式化为文本
    2. 调用 LLM 进行分析
    3. 解析 LLM 返回的 JSON 结果
    4. 将分析结果追加到 state.analyzed_results

    Args:
        state: 当前研究状态

    Returns:
        更新后的研究状态（仅包含变更字段）
    """
    if state.get("status") == "error":
        return {
            "status": "error",
            "error_message": state.get("error_message"),
        }

    query: str = state["query"]
    search_results = state["search_results"]

    logger.info(
        "analyze_node: analyzing %d search results for query=%r",
        len(search_results),
        query,
    )

    if not search_results:
        logger.warning("analyze_node: no search results to analyze")
        fallback_analysis = AnalysisResult(
            key_points=[
                "No search results were available because all search tools failed or returned empty results.",
                "The workflow can continue with a limited report that documents the retrieval failures.",
            ],
            entities=[],
            confidence=0.0,
        )
        return {
            "analyzed_results": state["analyzed_results"] + [fallback_analysis],
            "status": "analyzing",
            "error_message": None,
        }

    # 格式化搜索结果
    search_content = _format_search_results(search_results)

    # 构建 prompt
    prompt = _ANALYZE_PROMPT.format(
        query=query,
        search_content=search_content,
    )

    # 调用 LLM（使用统一的 LLM 服务）
    try:
        llm = create_llm(temperature=0.1)
        response = await llm.ainvoke(prompt)
        analysis = _parse_analysis_response(response.content)
    except Exception as exc:
        logger.error("analyze_node: LLM call failed: %s", exc)
        analysis = AnalysisResult(
            key_points=[],
            entities=[],
            confidence=0.0,
        )

    # 追加分析结果
    updated_analyzed = state["analyzed_results"] + [analysis]

    logger.info(
        "analyze_node: extracted %d key_points, %d entities, confidence=%.2f",
        len(analysis["key_points"]),
        len(analysis["entities"]),
        analysis["confidence"],
    )

    return {
        "analyzed_results": updated_analyzed,
        "status": "analyzing",
    }

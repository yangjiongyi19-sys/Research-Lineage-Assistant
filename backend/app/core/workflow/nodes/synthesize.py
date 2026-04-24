"""综合节点 —— 整合多源分析结果，构建统一知识视图。

将多轮迭代的搜索与分析结果进行综合，
解决信息冲突，形成结构化的综合内容。
"""

import logging
from typing import List

from app.services.llm import create_llm
from ..state import AnalysisResult, ResearchState

logger = logging.getLogger(__name__)

_SYNTHESIZE_PROMPT = """\
你是一位资深研究综合专家。请将以下多源分析结果整合为一份连贯的综合报告。

研究主题: {query}
当前迭代: {iterations}/{max_iterations}

分析结果:
{analysis_content}

请完成以下任务:
1. 整合所有关键要点，去除重复和矛盾
2. 标注信息冲突并给出你的判断
3. 构建实体之间的关系网络描述
4. 评估当前信息的完整性和可靠性

请输出一份结构化的综合内容（Markdown 格式）。
"""


def _format_analyzed_results(results: List[AnalysisResult]) -> str:
    """将分析结果格式化为可读文本。

    Args:
        results: AnalysisResult 列表

    Returns:
        格式化后的文本
    """
    parts: List[str] = []
    for i, r in enumerate(results, 1):
        key_points = "\n".join(f"  - {p}" for p in r["key_points"])
        entities = ", ".join(r["entities"])
        parts.append(
            f"### 分析结果 #{i} (置信度: {r['confidence']:.2f})\n"
            f"关键要点:\n{key_points}\n\n"
            f"实体: {entities}"
        )
    return "\n\n".join(parts)


async def synthesize_node(state: ResearchState) -> dict:
    """综合多源信息。

    工作流程：
    1. 将所有分析结果格式化
    2. 调用 LLM 进行综合整合
    3. 将综合内容写入 state.synthesized_content

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
    iterations: int = state["iterations"]
    max_iterations: int = state["max_iterations"]
    analyzed_results = state["analyzed_results"]

    logger.info(
        "synthesize_node: synthesizing %d analysis results, iteration %d/%d",
        len(analyzed_results),
        iterations,
        max_iterations,
    )

    if not analyzed_results:
        logger.warning("synthesize_node: no analyzed results to synthesize")
        return {
            "synthesized_content": state.get("synthesized_content", ""),
            "status": "synthesizing",
        }

    # 格式化分析结果
    analysis_content = _format_analyzed_results(analyzed_results)

    # 构建 prompt
    prompt = _SYNTHESIZE_PROMPT.format(
        query=query,
        iterations=iterations,
        max_iterations=max_iterations,
        analysis_content=analysis_content,
    )

    # 调用 LLM（使用统一的 LLM 服务）
    try:
        llm = create_llm(temperature=0.3)
        response = await llm.ainvoke(prompt)
        synthesized = response.content
    except Exception as exc:
        logger.error("synthesize_node: LLM call failed: %s", exc)
        # 降级：将分析结果简单拼接
        synthesized = analysis_content

    logger.info(
        "synthesize_node: produced %d chars of synthesized content",
        len(synthesized),
    )

    return {
        "synthesized_content": synthesized,
        "status": "synthesizing",
    }

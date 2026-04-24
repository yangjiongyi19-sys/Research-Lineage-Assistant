"""LLM 服务 —— 统一封装 OpenAI 和阿里百炼 API 调用。

提供统一的接口来调用不同 LLM 提供商的模型，
支持 OpenAI 和阿里百炼（通义千问）。
"""

import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings, LLMProvider

logger = logging.getLogger(__name__)


def create_llm(
    model: Optional[str] = None,
    temperature: float = 0.2,
    provider: Optional[str] = None,
    streaming: bool = False,
) -> BaseChatModel:
    """创建 LLM 实例。

    根据配置自动选择 LLM 提供商（OpenAI 或阿里百炼）。

    Args:
        model: 模型名称，默认使用配置中的模型
        temperature: 温度参数，控制随机性
        provider: 强制指定提供商，默认使用配置中的 LLM_PROVIDER

    Returns:
        LangChain ChatModel 实例

    Raises:
        ValueError: 当配置的提供商不支持或缺少 API Key 时
    """
    provider = provider or settings.LLM_PROVIDER
    
    if provider == LLMProvider.BAILIAN:
        return _create_bailian_llm(model, temperature, streaming)
    elif provider == LLMProvider.OPENAI:
        return _create_openai_llm(model, temperature, streaming)
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")


def _create_openai_llm(
    model: Optional[str] = None,
    temperature: float = 0.2,
    streaming: bool = False,
) -> ChatOpenAI:
    """创建 OpenAI LLM 实例。"""
    if not settings.OPENAI_API_KEY:
        raise ValueError(
            "未配置 OpenAI API Key。请在 .env 文件中设置 OPENAI_API_KEY，"
            "或切换 LLM_PROVIDER 为 bailian 并使用百炼平台。"
        )
    
    model_name = model or settings.OPENAI_MODEL
    
    logger.debug(f"创建 OpenAI LLM: model={model_name}, temperature={temperature}")
    
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None,
        streaming=streaming,
    )


def _create_bailian_llm(
    model: Optional[str] = None,
    temperature: float = 0.2,
    streaming: bool = False,
) -> ChatOpenAI:
    """创建阿里百炼 LLM 实例。
    
    百炼平台兼容 OpenAI API 格式，使用 ChatOpenAI 配合自定义 base_url。
    
    可用模型：
    - qwen-turbo: 速度快，成本低（默认）
    - qwen-plus: 性能均衡
    - qwen-max: 最强性能
    """
    if not settings.BAILIAN_API_KEY:
        raise ValueError(
            "未配置百炼 API Key。请在 .env 文件中设置 BAILIAN_API_KEY，"
            "或从 https://bailian.console.aliyun.com/ 获取 API Key。"
        )
    
    model_name = model or settings.BAILIAN_MODEL
    
    logger.debug(f"创建百炼 LLM: model={model_name}, temperature={temperature}")
    
    # 百炼平台使用 OpenAI 兼容接口
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=settings.BAILIAN_API_KEY,
        base_url=settings.BAILIAN_BASE_URL,
        streaming=streaming,
    )


def get_llm_info() -> dict:
    """获取当前 LLM 配置信息。"""
    return {
        "provider": settings.LLM_PROVIDER,
        "openai_model": settings.OPENAI_MODEL,
        "bailian_model": settings.BAILIAN_MODEL,
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "bailian_configured": bool(settings.BAILIAN_API_KEY),
    }

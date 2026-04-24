from pydantic_settings import BaseSettings
from functools import lru_cache
from enum import Enum


class LLMProvider(str, Enum):
    """LLM 提供商枚举"""
    OPENAI = "openai"
    BAILIAN = "bailian"  # 阿里百炼


class Settings(BaseSettings):
    """应用配置"""
    APP_NAME: str = "Deep Research Assistant"
    DEBUG: bool = False
    
    # LLM 提供商选择 (openai / bailian)
    LLM_PROVIDER: str = "openai"
    
    # OpenAI 配置
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"  # 默认模型
    
    # 阿里百炼配置
    BAILIAN_API_KEY: str = ""  # 百炼 API Key (从 https://bailian.console.aliyun.com/ 获取)
    BAILIAN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    BAILIAN_MODEL: str = "qwen-turbo"  # 可选: qwen-turbo, qwen-plus, qwen-max
    
    # 搜索配置 (Exa Search MCP)
    # Exa MCP 是远程托管服务，无需 API Key 即可使用基础搜索
    # 可选：传入 API Key 以解锁高级功能 (deep_search 等) 和更高限额
    EXA_API_KEY: str = ""  # 可选，留空则使用免费额度
    EXA_MCP_URL: str = "https://mcp.exa.ai/mcp"  # Exa MCP 服务端点
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./research.db"
    WIKI_WORKSPACE_PATH: str = "./wiki_workspace"
    
    # LangGraph Settings
    MAX_ITERATIONS: int = 3
    SEARCH_RESULTS_LIMIT: int = 5
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

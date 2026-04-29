"""
应用配置管理 — 从 .env 文件加载所有配置
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """全局配置，通过环境变量或 .env 文件加载"""

    # ---------- Database ----------
    DATABASE_URL: str = "postgresql+asyncpg://stocknews:stocknews_dev@db:5432/stocknews"

    # ---------- Redis ----------
    REDIS_URL: str = "redis://redis:6379/0"

    # ---------- API Keys ----------
    RTPR_API_KEY: str = ""               # 一手新闻稿 API (rtpr.io)
    FINNHUB_API_KEY: str = ""            # 保留兼容（已弃用）
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""             # Google Gemini API
    POLYGON_API_KEY: str = ""            # Polygon.io — 新闻 + 行情数据

    # ---------- 微信推送（Server酱）----------
    WECHAT_SENDKEY: str = ""

    # ---------- App Settings ----------
    APP_NAME: str = "QuantNews"
    DEBUG: bool = True

    # ---------- LLM 模型配置（全量切换为 OpenAI）----------
    OPENAI_MODEL_L1: str = "gpt-4o-mini"          # L1 初筛（全量）
    OPENAI_MODEL_L2: str = "gpt-4o-mini"          # L2 中级分析
    OPENAI_MODEL_L3: str = "gpt-4o-mini"          # L3 深度分析（暂用mini，速度快，TPM限制宽松）

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()

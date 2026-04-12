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
    FINNHUB_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # ---------- 微信推送 (WxPusher) ----------
    WXPUSHER_APP_TOKEN: str = ""
    WXPUSHER_UIDS: str = ""  # 逗号分隔多个 UID

    # ---------- Telegram 推送 ----------
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # ---------- App Settings ----------
    APP_NAME: str = "NewsAnalysisForStock"
    DEBUG: bool = True

    # ---------- LLM 模型配置 ----------
    OPENAI_MODEL: str = "gpt-4o-mini"        # Level 1 初筛（便宜）
    OPENAI_MODEL_L2: str = "gpt-4o"          # Level 2 深度分析（更强）

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()

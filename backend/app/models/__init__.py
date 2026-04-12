"""
数据库模型汇总 — 确保 Alembic 能发现所有模型
"""
from app.models.company import Company
from app.models.news import News
from app.models.analysis import Analysis
from app.models.trial import ClinicalTrial
from app.models.catalyst import Catalyst

__all__ = [
    "Company",
    "News",
    "Analysis",
    "ClinicalTrial",
    "Catalyst",
]

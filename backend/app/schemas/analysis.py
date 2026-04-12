"""
分析结果相关的请求/响应 Schema
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AnalysisResponse(BaseModel):
    """分析结果响应"""
    id: int
    news_id: int
    ticker: str
    company_name: str
    news_title: str
    level: int
    sentiment: str
    confidence: float
    impact_level: str
    impact_duration: Optional[str] = None
    summary_cn: str
    detailed_analysis: Optional[dict] = None
    related_tickers: Optional[list] = None
    key_dates: Optional[list] = None
    created_at: datetime


class AnalyzeBatchResult(BaseModel):
    """批量分析结果"""
    total: int
    analyzed: int
    high_impact: int
    errors: int

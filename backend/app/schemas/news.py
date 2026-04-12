"""
新闻相关的请求/响应 Schema
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NewsResponse(BaseModel):
    """新闻列表项响应"""
    id: int
    company_id: int
    ticker: str
    company_name: str
    title: str
    summary: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    category: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime


class NewsFetchResult(BaseModel):
    """采集结果响应"""
    companies_processed: int
    total_fetched: int
    new_articles: int
    errors: list[str] = []

"""
Watchlist 相关的请求/响应 Schema
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CompanyCreate(BaseModel):
    """添加公司到 Watchlist"""
    ticker: str = Field(..., min_length=1, max_length=10, description="股票代码，如 MRNA")
    name: str = Field(..., min_length=1, max_length=200, description="公司名称")
    sector: str = Field(default="Biotechnology", max_length=100, description="所属板块")
    therapeutic_area: str = Field(default="", max_length=200, description="治疗领域")
    priority: str = Field(default="medium", pattern="^(high|medium)$", description="优先级")
    track_fda: bool = Field(default=True, description="是否跟踪 FDA 审批")
    track_trials: bool = Field(default=True, description="是否跟踪临床试验")
    notes: str = Field(default="", description="备注")


class CompanyUpdate(BaseModel):
    """更新 Watchlist 公司信息"""
    name: Optional[str] = Field(None, max_length=200)
    sector: Optional[str] = Field(None, max_length=100)
    therapeutic_area: Optional[str] = Field(None, max_length=200)
    priority: Optional[str] = Field(None, pattern="^(high|medium)$")
    track_fda: Optional[bool] = None
    track_trials: Optional[bool] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class CompanyResponse(BaseModel):
    """Watchlist 公司响应"""
    id: int
    ticker: str
    name: str
    sector: str
    therapeutic_area: str
    priority: str
    track_fda: bool
    track_trials: bool
    is_active: bool
    notes: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

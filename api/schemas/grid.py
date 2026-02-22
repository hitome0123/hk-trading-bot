"""
Grid Strategy Pydantic Models
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class StrategyStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class AssetType(str, Enum):
    HK_STOCK = "hk_stock"
    US_STOCK = "us_stock"
    CRYPTO = "crypto"


class GridStrategyCreate(BaseModel):
    """创建网格策略请求"""
    ticker: str = Field(..., description="交易对代码", example="0700.HK")
    asset_type: AssetType = Field(..., description="资产类型")
    price_upper: float = Field(..., gt=0, description="价格上限")
    price_lower: float = Field(..., gt=0, description="价格下限")
    grid_count: int = Field(..., ge=2, le=100, description="网格数量")
    investment_per_grid: float = Field(..., gt=0, description="每格投资金额")
    take_profit_pct: Optional[float] = Field(0.3, ge=0, le=1, description="止盈比例")
    stop_loss_pct: Optional[float] = Field(0.15, ge=0, le=1, description="止损比例")

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "0700.HK",
                "asset_type": "hk_stock",
                "price_upper": 400,
                "price_lower": 300,
                "grid_count": 10,
                "investment_per_grid": 1000,
                "take_profit_pct": 0.3,
                "stop_loss_pct": 0.15
            }
        }


class GridStrategyUpdate(BaseModel):
    """更新网格策略请求"""
    price_upper: Optional[float] = Field(None, gt=0)
    price_lower: Optional[float] = Field(None, gt=0)
    grid_count: Optional[int] = Field(None, ge=2, le=100)
    investment_per_grid: Optional[float] = Field(None, gt=0)
    take_profit_pct: Optional[float] = Field(None, ge=0, le=1)
    stop_loss_pct: Optional[float] = Field(None, ge=0, le=1)


class GridLevel(BaseModel):
    """单个网格层级"""
    level: int
    price: float
    buy_filled: bool = False
    sell_filled: bool = False
    quantity: float = 0


class GridStrategyResponse(BaseModel):
    """网格策略响应"""
    id: str
    ticker: str
    asset_type: AssetType
    price_upper: float
    price_lower: float
    grid_count: int
    grid_spacing: float
    investment_per_grid: float
    total_investment: float
    take_profit_pct: float
    stop_loss_pct: float
    status: StrategyStatus
    grid_levels: List[GridLevel]
    realized_pnl: float = 0
    unrealized_pnl: float = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GridStrategyList(BaseModel):
    """策略列表响应"""
    strategies: List[GridStrategyResponse]
    total: int


class AnalysisResponse(BaseModel):
    """分析结果响应"""
    ticker: str
    current_price: float
    signal: str
    score: float
    confidence: float
    analysis_time: datetime
    details: dict

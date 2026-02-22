"""
Grid Strategy API Router
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict
import uuid
from datetime import datetime

from ..schemas.grid import (
    GridStrategyCreate,
    GridStrategyUpdate,
    GridStrategyResponse,
    GridStrategyList,
    GridLevel,
    StrategyStatus,
)

router = APIRouter(prefix="/api/grid-strategy", tags=["Grid Strategy"])

# 内存存储 (生产环境应使用数据库)
strategies_db: Dict[str, dict] = {}


def calculate_grid_levels(price_upper: float, price_lower: float, grid_count: int) -> list:
    """计算网格层级"""
    grid_spacing = (price_upper - price_lower) / (grid_count - 1)
    levels = []
    for i in range(grid_count):
        price = price_lower + (i * grid_spacing)
        levels.append(GridLevel(
            level=i + 1,
            price=round(price, 4),
            buy_filled=False,
            sell_filled=False,
            quantity=0
        ))
    return levels


@router.post("", response_model=GridStrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(strategy: GridStrategyCreate):
    """创建网格策略"""
    if strategy.price_lower >= strategy.price_upper:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="价格下限必须小于上限"
        )

    strategy_id = str(uuid.uuid4())[:8]
    grid_spacing = (strategy.price_upper - strategy.price_lower) / (strategy.grid_count - 1)
    grid_levels = calculate_grid_levels(
        strategy.price_upper,
        strategy.price_lower,
        strategy.grid_count
    )

    now = datetime.now()
    strategy_data = {
        "id": strategy_id,
        "ticker": strategy.ticker.upper(),
        "asset_type": strategy.asset_type,
        "price_upper": strategy.price_upper,
        "price_lower": strategy.price_lower,
        "grid_count": strategy.grid_count,
        "grid_spacing": round(grid_spacing, 4),
        "investment_per_grid": strategy.investment_per_grid,
        "total_investment": strategy.investment_per_grid * strategy.grid_count,
        "take_profit_pct": strategy.take_profit_pct,
        "stop_loss_pct": strategy.stop_loss_pct,
        "status": StrategyStatus.PENDING,
        "grid_levels": [level.model_dump() for level in grid_levels],
        "realized_pnl": 0,
        "unrealized_pnl": 0,
        "created_at": now,
        "updated_at": now,
    }

    strategies_db[strategy_id] = strategy_data
    return GridStrategyResponse(**strategy_data)


@router.get("", response_model=GridStrategyList)
async def list_strategies():
    """获取所有策略"""
    strategies = [GridStrategyResponse(**s) for s in strategies_db.values()]
    return GridStrategyList(strategies=strategies, total=len(strategies))


@router.get("/{strategy_id}", response_model=GridStrategyResponse)
async def get_strategy(strategy_id: str):
    """获取单个策略"""
    if strategy_id not in strategies_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"策略 {strategy_id} 不存在"
        )
    return GridStrategyResponse(**strategies_db[strategy_id])


@router.put("/{strategy_id}", response_model=GridStrategyResponse)
async def update_strategy(strategy_id: str, update: GridStrategyUpdate):
    """更新策略"""
    if strategy_id not in strategies_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"策略 {strategy_id} 不存在"
        )

    strategy = strategies_db[strategy_id]

    if strategy["status"] == StrategyStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="运行中的策略无法修改"
        )

    update_data = update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        strategy[field] = value

    # 重新计算网格
    if "price_upper" in update_data or "price_lower" in update_data or "grid_count" in update_data:
        strategy["grid_spacing"] = round(
            (strategy["price_upper"] - strategy["price_lower"]) / (strategy["grid_count"] - 1),
            4
        )
        grid_levels = calculate_grid_levels(
            strategy["price_upper"],
            strategy["price_lower"],
            strategy["grid_count"]
        )
        strategy["grid_levels"] = [level.model_dump() for level in grid_levels]

    if "investment_per_grid" in update_data or "grid_count" in update_data:
        strategy["total_investment"] = strategy["investment_per_grid"] * strategy["grid_count"]

    strategy["updated_at"] = datetime.now()

    return GridStrategyResponse(**strategy)


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(strategy_id: str):
    """删除策略"""
    if strategy_id not in strategies_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"策略 {strategy_id} 不存在"
        )

    strategy = strategies_db[strategy_id]
    if strategy["status"] == StrategyStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="运行中的策略无法删除，请先停止"
        )

    del strategies_db[strategy_id]


@router.post("/{strategy_id}/start", response_model=GridStrategyResponse)
async def start_strategy(strategy_id: str):
    """启动策略"""
    if strategy_id not in strategies_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"策略 {strategy_id} 不存在"
        )

    strategy = strategies_db[strategy_id]

    if strategy["status"] == StrategyStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="策略已在运行中"
        )

    strategy["status"] = StrategyStatus.RUNNING
    strategy["updated_at"] = datetime.now()

    return GridStrategyResponse(**strategy)


@router.post("/{strategy_id}/stop", response_model=GridStrategyResponse)
async def stop_strategy(strategy_id: str):
    """停止策略"""
    if strategy_id not in strategies_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"策略 {strategy_id} 不存在"
        )

    strategy = strategies_db[strategy_id]

    if strategy["status"] == StrategyStatus.STOPPED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="策略已停止"
        )

    strategy["status"] = StrategyStatus.STOPPED
    strategy["updated_at"] = datetime.now()

    return GridStrategyResponse(**strategy)

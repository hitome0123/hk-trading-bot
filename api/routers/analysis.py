"""
Analysis API Router
"""
import sys
import os
from fastapi import APIRouter, HTTPException
from datetime import datetime

# 添加父目录到路径以导入现有模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..schemas.grid import AnalysisResponse

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.get("/{ticker}", response_model=AnalysisResponse)
async def analyze_ticker(ticker: str):
    """分析标的"""
    try:
        ticker_upper = ticker.upper()

        # 尝试导入分析引擎
        try:
            from hk_trading_bot.core.analysis_engine import UniversalAnalysisEngine
            from hk_trading_bot.data_providers.yfinance_provider import YFinanceProvider
            from hk_trading_bot.data_providers.crypto_provider import CryptoProvider

            engine = UniversalAnalysisEngine()

            # 根据标的类型选择数据源
            if ticker_upper.endswith('.HK') or ticker_upper.endswith('.HKG'):
                data_provider = YFinanceProvider()
            elif ticker_upper in ['BTC', 'ETH', 'SOL', 'DOT', 'ADA', 'LINK', 'UNI']:
                data_provider = CryptoProvider()
            else:
                data_provider = YFinanceProvider()

            # 执行分析
            result = engine.analyze_ticker(ticker_upper, data_provider)

            if 'error' in result:
                raise HTTPException(status_code=500, detail=result['error'])

            composite = result.get('composite_analysis', {})

            return AnalysisResponse(
                ticker=ticker_upper,
                current_price=result.get('current_price', 0),
                signal=composite.get('overall_signal', 'HOLD'),
                score=composite.get('composite_score', 0),
                confidence=composite.get('confidence', 0.5),
                analysis_time=datetime.now(),
                details={
                    'layer_1_patterns': str(result.get('layer_1_patterns', [])),
                    'layer_2_capital_flow': str(result.get('layer_2_capital_flow', [])),
                    'layer_3_relative_strength': str(result.get('layer_3_relative_strength', [])),
                    'component_scores': composite.get('component_scores', {}),
                }
            )

        except ImportError as e:
            # 如果无法导入分析模块，返回模拟数据
            return AnalysisResponse(
                ticker=ticker_upper,
                current_price=100.0,
                signal="HOLD",
                score=50.0,
                confidence=0.5,
                analysis_time=datetime.now(),
                details={
                    "message": "Analysis engine not available, returning mock data",
                    "import_error": str(e)
                }
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

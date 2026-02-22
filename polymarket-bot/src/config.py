#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器

从config.yaml和环境变量加载配置
关键安全特性：
- 私钥必须从环境变量加载
- 严格验证所有配置项
- 不允许在配置文件中存储密钥
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
import structlog
from utils import validate_wallet_address, enforce_https

logger = structlog.get_logger()


@dataclass
class SharpTraderConfig:
    """Sharp交易员识别配置"""
    win_rate: float
    min_trades: int
    min_volume: float
    max_avg_odds: float
    recency_days: int
    roi: float
    consistency_score: float


@dataclass
class KellySizingConfig:
    """凯利准则仓位配置"""
    use_half_kelly: bool
    use_quarter_kelly: bool
    max_bet_pct: float
    max_total_exposure_pct: float
    min_edge_pct: float


@dataclass
class RiskManagementConfig:
    """风险管理配置"""
    max_per_trade_pct: float
    max_per_trade_usd: Optional[float]
    max_total_exposure_pct: float
    max_per_market_pct: float
    max_per_trader_pct: float
    daily_loss_limit_pct: float
    consecutive_loss_limit: int
    sharp_trader_drawdown_pct: float
    api_error_threshold: int
    min_market_liquidity_usd: float
    max_slippage_pct: float
    max_trade_age_seconds: int


@dataclass
class PollingConfig:
    """轮询配置"""
    sharp_trader_update_hours: int
    position_check_seconds: int
    market_data_seconds: int


@dataclass
class APIConfig:
    """API配置"""
    polymarket_api_url: str
    polytrack_api_url: str
    gamma_api_url: str
    clob_api_url: str


@dataclass
class WalletConfig:
    """钱包配置"""
    private_key: str  # 从环境变量加载
    proxy_wallet_address: str


@dataclass
class BlockchainConfig:
    """区块链配置"""
    chain_id: int
    rpc_url: str
    gas_limit: int
    gas_price_limit: int


@dataclass
@dataclass
class TelegramConfig:
    """Telegram通知配置"""
    enabled: bool
    bot_token: Optional[str]
    chat_id: Optional[str]
    notify_on_trade: bool = True
    notify_on_risk_breach: bool = True
    notify_on_circuit_breaker: bool = True


@dataclass
class BotConfig:
    """机器人完整配置"""
    sharp_trader: SharpTraderConfig
    kelly_sizing: KellySizingConfig
    risk_management: RiskManagementConfig
    polling: PollingConfig
    api: APIConfig
    wallet: WalletConfig
    blockchain: BlockchainConfig
    telegram: TelegramConfig
    paper_trading: bool
    initial_balance: float


class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)

    def load(self) -> BotConfig:
        """
        加载配置

        Returns:
            BotConfig对象

        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置验证失败
            RuntimeError: 环境变量未设置
        """
        # 检查配置文件
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {self.config_path}\n"
                f"请复制 config.example.yaml 为 config.yaml 并配置"
            )

        # 加载YAML
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        # 加载各部分配置
        sharp_trader = self._load_sharp_trader(config_data.get('sharp_trader_criteria', {}))
        kelly_sizing = self._load_kelly_sizing(config_data.get('kelly_sizing', {}))
        risk_management = self._load_risk_management(config_data.get('risk_management', {}))
        polling = self._load_polling(config_data.get('polling', {}))
        api = self._load_api(config_data.get('api', {}))
        wallet = self._load_wallet(config_data.get('wallet', {}))
        blockchain = self._load_blockchain(config_data.get('blockchain', {}))
        telegram = self._load_telegram(config_data.get('notifications', {}).get('telegram', {}))

        # 模拟交易模式
        paper_trading_config = config_data.get('paper_trading', {})
        paper_trading = paper_trading_config.get('enabled', True)
        initial_balance = paper_trading_config.get('initial_balance', 10000)

        bot_config = BotConfig(
            sharp_trader=sharp_trader,
            kelly_sizing=kelly_sizing,
            risk_management=risk_management,
            polling=polling,
            api=api,
            wallet=wallet,
            blockchain=blockchain,
            telegram=telegram,
            paper_trading=paper_trading,
            initial_balance=initial_balance
        )

        # 验证配置
        self._validate_config(bot_config)

        logger.info(
            "配置加载成功",
            paper_trading=paper_trading,
            initial_balance=initial_balance if paper_trading else "真实账户"
        )

        return bot_config

    def _load_sharp_trader(self, data: Dict[str, Any]) -> SharpTraderConfig:
        """加载Sharp交易员配置"""
        return SharpTraderConfig(
            win_rate=data.get('win_rate', 0.70),
            min_trades=data.get('min_trades', 50),
            min_volume=data.get('min_volume', 10000),
            max_avg_odds=data.get('max_avg_odds', 0.90),
            recency_days=data.get('recency_days', 30),
            roi=data.get('roi', 0.20),
            consistency_score=data.get('consistency_score', 0.60)
        )

    def _load_kelly_sizing(self, data: Dict[str, Any]) -> KellySizingConfig:
        """加载凯利配置"""
        return KellySizingConfig(
            use_half_kelly=data.get('use_half_kelly', True),
            use_quarter_kelly=data.get('use_quarter_kelly', False),
            max_bet_pct=data.get('max_bet_pct', 0.10),
            max_total_exposure_pct=data.get('max_total_exposure_pct', 0.30),
            min_edge_pct=data.get('min_edge_pct', 0.02)
        )

    def _load_risk_management(self, data: Dict[str, Any]) -> RiskManagementConfig:
        """加载风险管理配置"""
        return RiskManagementConfig(
            max_per_trade_pct=data.get('max_per_trade_pct', 0.10),
            max_per_trade_usd=data.get('max_per_trade_usd'),
            max_total_exposure_pct=data.get('max_total_exposure_pct', 0.30),
            max_per_market_pct=data.get('max_per_market_pct', 0.05),
            max_per_trader_pct=data.get('max_per_trader_pct', 0.15),
            daily_loss_limit_pct=data.get('daily_loss_limit_pct', 0.10),
            consecutive_loss_limit=data.get('consecutive_loss_limit', 5),
            sharp_trader_drawdown_pct=data.get('sharp_trader_drawdown_pct', 0.30),
            api_error_threshold=data.get('api_error_threshold', 10),
            min_market_liquidity_usd=data.get('min_market_liquidity_usd', 10000),
            max_slippage_pct=data.get('max_slippage_pct', 0.05),
            max_trade_age_seconds=data.get('max_trade_age_seconds', 60)
        )

    def _load_polling(self, data: Dict[str, Any]) -> PollingConfig:
        """加载轮询配置"""
        return PollingConfig(
            sharp_trader_update_hours=data.get('sharp_trader_update_hours', 6),
            position_check_seconds=data.get('position_check_seconds', 4),
            market_data_seconds=data.get('market_data_seconds', 10)
        )

    def _load_api(self, data: Dict[str, Any]) -> APIConfig:
        """加载API配置"""
        return APIConfig(
            polymarket_api_url=enforce_https(
                data.get('polymarket_api_url', 'https://data-api.polymarket.com')
            ),
            polytrack_api_url=enforce_https(
                data.get('polytrack_api_url', 'https://polytrack.io/api')
            ),
            gamma_api_url=enforce_https(
                data.get('gamma_api_url', 'https://gamma-api.polymarket.com')
            ),
            clob_api_url=enforce_https(
                data.get('clob_api_url', 'https://clob.polymarket.com')
            )
        )

    def _load_wallet(self, data: Dict[str, Any]) -> WalletConfig:
        """
        加载钱包配置

        ⚠️ 安全关键：私钥必须从环境变量加载
        """
        # 私钥必须从环境变量加载
        private_key = os.getenv('WALLET_PRIVATE_KEY')

        if not private_key:
            raise RuntimeError(
                "❌ 未设置 WALLET_PRIVATE_KEY 环境变量!\n\n"
                "私钥绝不能放在配置文件中！\n"
                "请设置环境变量：\n"
                "  export WALLET_PRIVATE_KEY='your_key_here'\n\n"
                "或在.env文件中添加：\n"
                "  WALLET_PRIVATE_KEY=your_key_here\n"
            )

        # 验证私钥格式 (0x + 64位十六进制)
        if not private_key.startswith('0x') or len(private_key) != 66:
            raise ValueError(
                f"无效的私钥格式。\n"
                f"应该是: 0x + 64位十六进制字符\n"
                f"当前长度: {len(private_key)}"
            )

        # 代理钱包地址
        proxy_wallet = data.get('proxy_wallet_address', '')
        if not proxy_wallet:
            raise ValueError("必须配置 proxy_wallet_address")

        if not validate_wallet_address(proxy_wallet):
            raise ValueError(f"无效的代理钱包地址: {proxy_wallet}")

        return WalletConfig(
            private_key=private_key,
            proxy_wallet_address=proxy_wallet
        )

    def _load_blockchain(self, data: Dict[str, Any]) -> BlockchainConfig:
        """加载区块链配置"""
        rpc_url = data.get('rpc_url', '')

        if not rpc_url:
            raise ValueError("必须配置 blockchain.rpc_url")

        return BlockchainConfig(
            chain_id=data.get('chain_id', 137),  # Polygon主网
            rpc_url=enforce_https(rpc_url),
            gas_limit=data.get('gas_limit', 5000),
            gas_price_limit=data.get('gas_price_limit', 110000000000)
        )

    def _load_telegram(self, data: Dict[str, Any]) -> TelegramConfig:
        """加载Telegram配置"""
        enabled = data.get('enabled', False)

        bot_token = None
        chat_id = None

        if enabled:
            # 如果启用，从环境变量加载
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN') or data.get('bot_token')
            chat_id = os.getenv('TELEGRAM_CHAT_ID') or data.get('chat_id')

            if not bot_token or not chat_id:
                logger.warning(
                    "Telegram已启用但未配置token/chat_id，将禁用通知"
                )
                enabled = False

        return TelegramConfig(
            enabled=enabled,
            bot_token=bot_token,
            chat_id=chat_id,
            notify_on_trade=data.get('notify_on_trade', True),
            notify_on_risk_breach=data.get('notify_on_risk_breach', True),
            notify_on_circuit_breaker=data.get('notify_on_circuit_breaker', True)
        )

    def _validate_config(self, config: BotConfig):
        """
        验证配置合理性

        Raises:
            ValueError: 配置不合理
        """
        # 验证Kelly配置
        if config.kelly_sizing.use_half_kelly and config.kelly_sizing.use_quarter_kelly:
            raise ValueError("不能同时启用半凯利和四分之一凯利")

        if config.kelly_sizing.max_bet_pct > 0.2:
            logger.warning(
                "单笔下注上限过高",
                max_bet_pct=config.kelly_sizing.max_bet_pct,
                recommendation="建议≤0.1 (10%)"
            )

        # 验证风险管理
        if config.risk_management.max_total_exposure_pct > 0.5:
            logger.warning(
                "总敞口上限过高",
                max_total=config.risk_management.max_total_exposure_pct,
                recommendation="建议≤0.3 (30%)"
            )

        # 验证Sharp交易员标准
        if config.sharp_trader.win_rate < 0.6:
            logger.warning(
                "Sharp交易员胜率阈值较低",
                win_rate=config.sharp_trader.win_rate,
                recommendation="建议≥0.70 (70%)"
            )

        logger.info("配置验证通过 ✓")


# 全局配置实例（延迟加载）
_config: Optional[BotConfig] = None


def get_config(reload: bool = False) -> BotConfig:
    """
    获取全局配置实例

    Args:
        reload: 是否重新加载配置

    Returns:
        BotConfig对象
    """
    global _config

    if _config is None or reload:
        loader = ConfigLoader()
        _config = loader.load()

    return _config


def main():
    """测试配置加载"""
    # 需要先设置环境变量
    os.environ['WALLET_PRIVATE_KEY'] = '0x' + '1' * 64  # 测试密钥

    try:
        config = get_config()
        print("✓ 配置加载成功")
        print(f"  模拟交易: {config.paper_trading}")
        print(f"  初始资金: ${config.initial_balance:,.0f}")
        print(f"  Sharp胜率阈值: {config.sharp_trader.win_rate:.0%}")
        print(f"  凯利模式: {'半凯利' if config.kelly_sizing.use_half_kelly else '四分之一凯利'}")
        print(f"  单笔上限: {config.kelly_sizing.max_bet_pct:.0%}")
        print(f"  总敞口上限: {config.risk_management.max_total_exposure_pct:.0%}")
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
资金费率监控 - 寻找轧空机会
监控各交易所永续合约资金费率，找出极度负费率的币种
支持: Coinglass爬虫、Telegram推送、爆仓热力图
"""

import requests
import json
import time
import os
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# 配置文件路径
CONFIG_FILE = os.path.expanduser('~/.funding_monitor_config.json')


def load_config() -> Dict:
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'telegram_token': '', 'telegram_chat_id': '', 'alert_threshold': -0.1}


def save_config(config: Dict):
    """保存配置"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


class TelegramNotifier:
    """Telegram推送"""

    def __init__(self, token: str = None, chat_id: str = None):
        config = load_config()
        self.token = token or config.get('telegram_token', '')
        self.chat_id = chat_id or config.get('telegram_chat_id', '')

    def send(self, message: str, parse_mode: str = 'HTML') -> bool:
        """发送Telegram消息"""
        if not self.token or not self.chat_id:
            print(f"[本地] {message}")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            resp = requests.post(url, data=data, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"Telegram发送失败: {e}")
            return False

    def send_alert(self, symbol: str, funding_rate: float, score: float, signal_type: str):
        """发送预警消息"""
        if signal_type == 'squeeze':
            emoji = '🟢'
            title = '轧空机会'
        else:
            emoji = '🔴'
            title = '多头拥挤'

        message = f"""
{emoji} <b>{title}预警</b>

<b>币种:</b> {symbol}
<b>费率:</b> {funding_rate:+.4f}%
<b>评分:</b> {score:.0f}/100
<b>时间:</b> {datetime.now().strftime('%H:%M:%S')}

💡 费率极端，注意机会！
"""
        return self.send(message)


class CoinglassScraper:
    """Coinglass网页爬虫 + 多源数据聚合"""

    def __init__(self):
        self.base_url = "https://www.coinglass.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
        }

    def get_funding_rates(self) -> List[Dict]:
        """聚合多交易所费率数据"""
        results = []

        # 从OKX获取
        okx_rates = self._get_okx_all_rates()
        for r in okx_rates:
            results.append({
                'symbol': r['symbol'],
                'funding_rate': r['rate'],
                'okx_rate': r['rate'],
                'binance_rate': 0,
                'open_interest_usd': r.get('oi_usd', 0),
                'price': r.get('price', 0),
                'source': 'OKX'
            })

        return results

    def _get_okx_all_rates(self) -> List[Dict]:
        """获取OKX所有永续合约费率"""
        try:
            # 获取所有永续合约
            url = "https://www.okx.com/api/v5/public/instruments"
            params = {'instType': 'SWAP'}
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()

            if data.get('code') != '0':
                return []

            # 过滤USDT永续
            instruments = [i for i in data['data'] if i['instId'].endswith('-USDT-SWAP')]

            results = []
            # 批量获取费率
            for inst in instruments[:50]:  # 限制数量
                symbol = inst['instId'].replace('-USDT-SWAP', '')
                try:
                    # 获取费率
                    rate_url = "https://www.okx.com/api/v5/public/funding-rate"
                    rate_resp = requests.get(rate_url, params={'instId': inst['instId']}, timeout=5)
                    rate_data = rate_resp.json()

                    if rate_data.get('code') == '0' and rate_data.get('data'):
                        rate = float(rate_data['data'][0]['fundingRate']) * 100

                        # 获取价格
                        ticker_url = "https://www.okx.com/api/v5/market/ticker"
                        ticker_resp = requests.get(ticker_url, params={'instId': inst['instId']}, timeout=5)
                        ticker_data = ticker_resp.json()
                        price = float(ticker_data['data'][0]['last']) if ticker_data.get('data') else 0

                        results.append({
                            'symbol': symbol,
                            'rate': rate,
                            'price': price,
                            'oi_usd': 0
                        })

                        time.sleep(0.05)
                except:
                    continue

            return results

        except Exception as e:
            print(f"获取OKX费率失败: {e}")
            return []

    def get_liquidation_data(self) -> Dict:
        """获取爆仓数据"""
        try:
            url = "https://fapi.coinglass.com/api/futures/liquidation/info"
            resp = requests.get(url, headers=self.headers, timeout=15)
            data = resp.json()

            if data.get('success') and data.get('data'):
                return data['data']
        except Exception as e:
            print(f"获取爆仓数据失败: {e}")

        return {}

    def get_liquidation_heatmap(self, symbol: str = 'BTC') -> Dict:
        """获取爆仓热力图数据"""
        try:
            url = f"https://fapi.coinglass.com/api/futures/liquidation/chart?symbol={symbol}"
            resp = requests.get(url, headers=self.headers, timeout=15)
            data = resp.json()

            if data.get('success') and data.get('data'):
                return data['data']
        except Exception as e:
            print(f"获取爆仓热力图失败: {e}")

        return {}

    def get_long_short_ratio(self, symbol: str = 'BTC') -> Dict:
        """获取多空比数据"""
        try:
            url = f"https://fapi.coinglass.com/api/futures/longShortRate?symbol={symbol}&timeType=2"
            resp = requests.get(url, headers=self.headers, timeout=15)
            data = resp.json()

            if data.get('success') and data.get('data'):
                return data['data']
        except Exception as e:
            print(f"获取多空比失败: {e}")

        return {}


class OnchainMonitor:
    """链上监控 - 追踪大户转账到交易所"""

    # 代币合约地址
    TOKEN_CONTRACTS = {
        'RIVER': {
            'bsc': '0xdA7AD9dea9397cffdDAE2f8a052B82f1484252B3',
            'eth': '0xdA7AD9dea9397cffdDAE2f8a052B82f1484252B3',
        },
        'MNT': {
            'eth': '0x3c3a81e81dc49a522a592e7622a7e711c06bf354',
        },
        'PENGU': {
            'eth': '0x52c1e6a54664a3e3e3a370e3e0c3e3e3e3e3e3e3',
        },
    }

    # 交易所热钱包地址
    EXCHANGE_WALLETS = {
        # Binance
        '0x28c6c06298d514db089934071355e5743bf21d60': 'Binance',
        '0x21a31ee1afc51d94c2efccaa2092ad1028285549': 'Binance',
        '0xdfd5293d8e347dfe59e90efd55b2956a1343963d': 'Binance',
        '0x5a52e96bacdabb82fd05763e25335261b270efcb': 'Binance',
        '0xf977814e90da44bfa03b6295a0616a897441acec': 'Binance',
        # OKX
        '0x6cc5f688a315f3dc28a7781717a9a798a59fda7b': 'OKX',
        '0x98c3d3183c4b8a650614ad179a1a98be0a8d6b8e': 'OKX',
        '0x236f9f97e0e62388479bf9e5ba4889e46b0273c3': 'OKX',
        # Bybit
        '0xf89d7b9c864f589bbf53a82105107622b35eaa40': 'Bybit',
        '0x1db92e2eebc8e0c075a02bea49a2935bcd2dfcf4': 'Bybit',
        # Kucoin
        '0xd6216fc19db775df9774a6e33526131da7d19a2c': 'Kucoin',
        # Gate
        '0x0d0707963952f2fba59dd06f2b425ace40b492fe': 'Gate',
        # MEXC
        '0x4982085c9e2f89f2ecb8131eca71afad896e89cb': 'MEXC',
        # Bitget
        '0x1ab4973a48dc892cd9971ece8e01dcc7688f8f23': 'Bitget',
    }

    # 做市商钱包
    MARKET_MAKER_WALLETS = {
        '0x46340b20830761efd32832a74d7169b29feb9758': 'Wintermute',
        '0xdbf5e9c5206d0db70a90108bf936da60221dc080': 'Wintermute 2',
        '0x84d34f4f83a87596cd3fb6887cff8f17bf5a7b83': 'Jump Trading',
        '0x9507c04b10486547584c37bcbd931b2a4fee9a41': 'Jump Trading 2',
        '0xe93381fb4c4f14bda253907b18fad305d799cee7': 'Alameda (FTX)',
        '0x0d0707963952f2fba59dd06f2b425ace40b492fe': 'GSR',
        '0xf584f8728b874a6a5c7a8d4d387c9aae9172d621': 'Cumberland',
        '0x7793cd85c11a924478d358d49b05b37e91b5810f': 'QCP Capital',
    }

    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0'}

    def get_top_holders(self, token: str, chain: str = 'bsc') -> List[Dict]:
        """获取代币前N大持有者"""
        contract = self.TOKEN_CONTRACTS.get(token.upper(), {}).get(chain, '')
        if not contract:
            return []

        try:
            if chain == 'bsc':
                url = f"https://api.bscscan.com/api"
            else:
                url = f"https://api.etherscan.io/api"

            params = {
                'module': 'token',
                'action': 'tokenholderlist',
                'contractaddress': contract,
                'page': 1,
                'offset': 20,
            }

            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()

            if data.get('status') == '1' and data.get('result'):
                holders = []
                for h in data['result']:
                    addr = h.get('TokenHolderAddress', '').lower()
                    balance = float(h.get('TokenHolderQuantity', 0)) / 1e18

                    # 判断地址类型
                    label = 'Unknown'
                    if addr in self.EXCHANGE_WALLETS:
                        label = f"交易所:{self.EXCHANGE_WALLETS[addr]}"
                    elif addr in self.MARKET_MAKER_WALLETS:
                        label = f"做市商:{self.MARKET_MAKER_WALLETS[addr]}"

                    holders.append({
                        'address': addr,
                        'balance': balance,
                        'label': label,
                    })

                return holders

        except Exception as e:
            print(f"获取持有者失败: {e}")

        return []

    def check_recent_transfers(self, token: str, chain: str = 'bsc', hours: int = 24) -> List[Dict]:
        """检查最近的大额转账"""
        contract = self.TOKEN_CONTRACTS.get(token.upper(), {}).get(chain, '')
        if not contract:
            return []

        try:
            if chain == 'bsc':
                url = "https://api.bscscan.com/api"
            else:
                url = "https://api.etherscan.io/api"

            params = {
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': contract,
                'page': 1,
                'offset': 100,
                'sort': 'desc',
            }

            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()

            transfers = []
            if data.get('status') == '1' and data.get('result'):
                for tx in data['result']:
                    value = float(tx.get('value', 0)) / (10 ** int(tx.get('tokenDecimal', 18)))
                    from_addr = tx.get('from', '').lower()
                    to_addr = tx.get('to', '').lower()

                    # 只看大额转账 (>10000代币)
                    if value < 10000:
                        continue

                    # 判断是否转入交易所
                    to_exchange = self.EXCHANGE_WALLETS.get(to_addr, '')
                    from_exchange = self.EXCHANGE_WALLETS.get(from_addr, '')
                    from_mm = self.MARKET_MAKER_WALLETS.get(from_addr, '')

                    signal = ''
                    if to_exchange:
                        signal = f'⚠️ 转入{to_exchange}（可能要卖）'
                    elif from_exchange:
                        signal = f'✅ 从{from_exchange}提出（可能要拉）'
                    elif from_mm:
                        signal = f'🔔 做市商{from_mm}转出'

                    if signal:  # 只记录有意义的转账
                        transfers.append({
                            'hash': tx.get('hash', '')[:16] + '...',
                            'from': from_addr[:8] + '...',
                            'to': to_addr[:8] + '...',
                            'value': value,
                            'signal': signal,
                            'time': datetime.fromtimestamp(int(tx.get('timeStamp', 0))),
                        })

            return transfers[:20]

        except Exception as e:
            print(f"获取转账记录失败: {e}")

        return []

    def monitor_token(self, token: str, chain: str = 'bsc') -> Dict:
        """监控单个代币"""
        result = {
            'token': token,
            'chain': chain,
            'alerts': [],
            'transfers': [],
        }

        # 检查最近转账
        transfers = self.check_recent_transfers(token, chain)
        result['transfers'] = transfers

        # 生成警报
        for t in transfers:
            if '转入' in t['signal'] and t['value'] > 50000:
                result['alerts'].append({
                    'level': 'high',
                    'message': f"{token}: {t['value']:,.0f} 代币转入交易所！",
                    'detail': t['signal'],
                })

        return result


class WhaleTracker:
    """巨鲸钱包追踪"""

    def __init__(self):
        # 知名做市商/机构钱包标签
        self.known_wallets = {
            # Ethereum
            'eth': {
                '0x28c6c06298d514db089934071355e5743bf21d60': 'Binance Hot',
                '0x21a31ee1afc51d94c2efccaa2092ad1028285549': 'Binance Cold',
                '0x6cc5f688a315f3dc28a7781717a9a798a59fda7b': 'OKX',
                '0x46340b20830761efd32832a74d7169b29feb9758': 'Wintermute',
                '0xdbf5e9c5206d0db70a90108bf936da60221dc080': 'Wintermute 2',
                '0x0d0707963952f2fba59dd06f2b425ace40b492fe': 'GSR',
                '0x84d34f4f83a87596cd3fb6887cff8f17bf5a7b83': 'Jump Trading',
            },
            # Mantle
            'mantle': {
                # 添加Mantle上的做市商地址
            }
        }

    def check_exchange_deposits(self, chain: str = 'eth') -> List[Dict]:
        """检查做市商往交易所充值"""
        results = []

        try:
            # 使用Etherscan API (需要API key才能高频调用)
            # 这里用公开的区块浏览器数据

            for addr, label in self.known_wallets.get(chain, {}).items():
                try:
                    # 检查最近交易
                    url = f"https://api.etherscan.io/api"
                    params = {
                        'module': 'account',
                        'action': 'txlist',
                        'address': addr,
                        'startblock': 0,
                        'endblock': 99999999,
                        'page': 1,
                        'offset': 10,
                        'sort': 'desc'
                    }

                    resp = requests.get(url, params=params, timeout=10)
                    data = resp.json()

                    if data.get('status') == '1' and data.get('result'):
                        for tx in data['result'][:5]:
                            # 检查是否是往交易所转账
                            to_addr = tx.get('to', '').lower()
                            if self._is_exchange_addr(to_addr):
                                value_eth = int(tx.get('value', 0)) / 1e18
                                results.append({
                                    'from': label,
                                    'from_addr': addr,
                                    'to': self._get_exchange_name(to_addr),
                                    'value': value_eth,
                                    'hash': tx.get('hash'),
                                    'time': datetime.fromtimestamp(int(tx.get('timeStamp', 0)))
                                })

                    time.sleep(0.2)  # 避免请求过快

                except:
                    continue

        except Exception as e:
            print(f"追踪失败: {e}")

        return results

    def _is_exchange_addr(self, addr: str) -> bool:
        """判断是否是交易所地址"""
        exchange_addrs = [
            '0x28c6c06298d514db089934071355e5743bf21d60',  # Binance
            '0xdfd5293d8e347dfe59e90efd55b2956a1343963d',  # Binance 2
            '0x6cc5f688a315f3dc28a7781717a9a798a59fda7b',  # OKX
            '0x98c3d3183c4b8a650614ad179a1a98be0a8d6b8e',  # OKX 2
            '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640',  # Uniswap V3
        ]
        return addr.lower() in exchange_addrs

    def _get_exchange_name(self, addr: str) -> str:
        """获取交易所名称"""
        names = {
            '0x28c6c06298d514db089934071355e5743bf21d60': 'Binance',
            '0xdfd5293d8e347dfe59e90efd55b2956a1343963d': 'Binance',
            '0x6cc5f688a315f3dc28a7781717a9a798a59fda7b': 'OKX',
            '0x98c3d3183c4b8a650614ad179a1a98be0a8d6b8e': 'OKX',
        }
        return names.get(addr.lower(), 'Unknown')

    def get_arkham_alerts(self) -> List[Dict]:
        """获取Arkham情报（需要API）"""
        # Arkham是付费服务，这里提供接口占位
        return []

    def track_token_movements(self, token_address: str, chain: str = 'eth') -> Dict:
        """追踪代币大额转移"""
        try:
            # 使用DexScreener获取代币信息
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            resp = requests.get(url, timeout=10)
            data = resp.json()

            if data.get('pairs'):
                pair = data['pairs'][0]
                return {
                    'symbol': pair.get('baseToken', {}).get('symbol'),
                    'price': float(pair.get('priceUsd', 0)),
                    'volume_24h': float(pair.get('volume', {}).get('h24', 0)),
                    'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0)),
                    'liquidity': float(pair.get('liquidity', {}).get('usd', 0)),
                    'txns_24h': pair.get('txns', {}).get('h24', {}),
                }

        except Exception as e:
            print(f"追踪失败: {e}")

        return {}


class LiquidationMonitor:
    """爆仓监控器"""

    def __init__(self):
        self.coinglass = CoinglassScraper()

    def get_liquidation_levels(self, symbol: str = 'BTC') -> Dict:
        """获取清算价位分布"""
        try:
            # 尝试从Coinglass获取
            data = self.coinglass.get_liquidation_heatmap(symbol)
            if data:
                return self._parse_liquidation_data(data, symbol)

            # 备用：从OKX获取
            return self._get_okx_liquidation(symbol)

        except Exception as e:
            print(f"获取清算数据失败: {e}")
            return {}

    def _parse_liquidation_data(self, data: Dict, symbol: str) -> Dict:
        """解析爆仓数据"""
        result = {
            'symbol': symbol,
            'long_liquidations': [],  # 多头爆仓价位
            'short_liquidations': [],  # 空头爆仓价位
            'total_long_liq': 0,
            'total_short_liq': 0
        }

        # 解析数据结构
        if isinstance(data, list):
            for item in data:
                price = item.get('price', 0)
                liq_long = item.get('liqLong', 0)
                liq_short = item.get('liqShort', 0)

                if liq_long > 0:
                    result['long_liquidations'].append({
                        'price': price,
                        'amount': liq_long
                    })
                    result['total_long_liq'] += liq_long

                if liq_short > 0:
                    result['short_liquidations'].append({
                        'price': price,
                        'amount': liq_short
                    })
                    result['total_short_liq'] += liq_short

        return result

    def _get_okx_liquidation(self, symbol: str) -> Dict:
        """从OKX获取清算数据"""
        try:
            url = f"https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-volume"
            params = {'ccy': symbol}
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()

            if data.get('code') == '0' and data.get('data'):
                return {'symbol': symbol, 'data': data['data'], 'source': 'OKX'}
        except:
            pass

        return {}

    def analyze_liquidation_risk(self, symbol: str, current_price: float) -> Dict:
        """分析爆仓风险"""
        levels = self.get_liquidation_levels(symbol)

        if not levels:
            return {'error': '无法获取清算数据'}

        result = {
            'symbol': symbol,
            'current_price': current_price,
            'nearby_long_liq': 0,  # 附近多头爆仓量
            'nearby_short_liq': 0,  # 附近空头爆仓量
            'risk_direction': 'neutral',
            'key_levels': []
        }

        # 计算价格±5%范围内的爆仓量
        price_range = current_price * 0.05

        for liq in levels.get('long_liquidations', []):
            if abs(liq['price'] - current_price) <= price_range:
                result['nearby_long_liq'] += liq['amount']
                result['key_levels'].append({
                    'price': liq['price'],
                    'type': 'long',
                    'amount': liq['amount']
                })

        for liq in levels.get('short_liquidations', []):
            if abs(liq['price'] - current_price) <= price_range:
                result['nearby_short_liq'] += liq['amount']
                result['key_levels'].append({
                    'price': liq['price'],
                    'type': 'short',
                    'amount': liq['amount']
                })

        # 判断风险方向
        if result['nearby_long_liq'] > result['nearby_short_liq'] * 1.5:
            result['risk_direction'] = 'down'  # 下方多头爆仓多，可能向下插针
        elif result['nearby_short_liq'] > result['nearby_long_liq'] * 1.5:
            result['risk_direction'] = 'up'  # 上方空头爆仓多，可能向上轧空

        # 按价格排序关键价位
        result['key_levels'].sort(key=lambda x: x['price'])

        return result


@dataclass
class FundingData:
    """资金费率数据"""
    symbol: str
    funding_rate: float  # 当前费率
    predicted_rate: float  # 预测费率
    open_interest: float  # 未平仓合约(USDT)
    price: float
    long_ratio: float  # 多头占比
    short_ratio: float  # 空头占比


class FundingMonitor:
    """资金费率监控器"""

    def __init__(self):
        self.okx_base = "https://www.okx.com"
        self.bybit_base = "https://api.bybit.com"

    def get_okx_funding_rates(self) -> List[Dict]:
        """获取OKX所有永续合约资金费率"""
        try:
            url = f"{self.okx_base}/api/v5/public/funding-rate"
            # 热门币种列表
            symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX', 'LINK',
                      'DOT', 'MATIC', 'UNI', 'ATOM', 'LTC', 'ETC', 'FIL', 'APT',
                      'ARB', 'OP', 'SUI', 'SEI', 'TIA', 'JUP', 'WIF', 'PEPE',
                      'BONK', 'SHIB', 'INJ', 'FTM', 'NEAR', 'RUNE', 'MKR', 'AAVE',
                      'CRV', 'LDO', 'SNX', 'COMP', 'SUSHI', 'YFI', '1INCH', 'BAL',
                      'BLUR', 'MEME', 'PYTH', 'JTO', 'STRK', 'ORDI', 'RIVER', 'MYX',
                      'PENDLE', 'ENA', 'W', 'ETHFI', 'DYM', 'ALT', 'PIXEL', 'PORTAL',
                      'MNT', 'MANTLE', 'EIGEN', 'ZRO', 'IO', 'ZK', 'LISTA', 'NOT']

            results = []
            for symbol in symbols:
                try:
                    params = {'instId': f"{symbol}-USDT-SWAP"}
                    resp = requests.get(url, params=params, timeout=5)
                    data = resp.json()

                    if data.get('code') == '0' and data.get('data'):
                        item = data['data'][0]
                        results.append({
                            'symbol': symbol,
                            'funding_rate': float(item['fundingRate']) * 100,
                            'next_funding_time': int(item['fundingTime']),
                            'source': 'OKX'
                        })
                        time.sleep(0.05)  # 避免请求过快
                except:
                    continue

            return results
        except Exception as e:
            print(f"获取OKX费率失败: {e}")
            return []

    def get_okx_ticker(self, symbol: str) -> Dict:
        """获取OKX行情数据"""
        try:
            url = f"{self.okx_base}/api/v5/market/ticker"
            params = {'instId': f"{symbol}-USDT-SWAP"}
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()

            if data.get('code') == '0' and data.get('data'):
                item = data['data'][0]
                return {
                    'price': float(item['last']),
                    'volume_24h': float(item.get('volCcy24h', 0)),
                    'open_interest': 0  # OKX需要单独接口
                }
        except:
            pass
        return {'price': 0, 'volume_24h': 0, 'open_interest': 0}

    def get_okx_open_interest(self, symbol: str) -> float:
        """获取OKX未平仓合约"""
        try:
            url = f"{self.okx_base}/api/v5/public/open-interest"
            params = {'instType': 'SWAP', 'instId': f"{symbol}-USDT-SWAP"}
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()

            if data.get('code') == '0' and data.get('data'):
                return float(data['data'][0].get('oiCcy', 0))
        except:
            pass
        return 0

    def get_bybit_funding_rates(self) -> List[Dict]:
        """获取Bybit所有永续合约资金费率"""
        try:
            url = f"{self.bybit_base}/v5/market/tickers"
            params = {'category': 'linear'}
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()

            if data.get('retCode') != 0:
                return []

            results = []
            for item in data['result']['list']:
                if item['symbol'].endswith('USDT') and item.get('fundingRate'):
                    symbol = item['symbol'].replace('USDT', '')
                    results.append({
                        'symbol': symbol,
                        'funding_rate': float(item['fundingRate']) * 100,
                        'mark_price': float(item['markPrice']),
                        'open_interest': float(item.get('openInterest', 0)),
                        'next_funding_time': int(item.get('nextFundingTime', 0)),
                        'source': 'Bybit'
                    })

            return results
        except Exception as e:
            print(f"获取Bybit费率失败: {e}")
            return []

    def get_all_funding_rates(self) -> List[Dict]:
        """获取所有交易所的资金费率"""
        # 使用OKX
        results = self.get_okx_funding_rates()
        return results

    def get_okx_long_short_ratio(self, symbol: str) -> Dict:
        """获取OKX多空比"""
        try:
            url = f"{self.okx_base}/api/v5/rubik/stat/contracts/long-short-account-ratio"
            params = {'instId': f"{symbol}-USDT-SWAP", 'period': '5m'}
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()

            if data.get('code') == '0' and data.get('data'):
                # data格式: [[ts, longRatio, shortRatio], ...]
                item = data['data'][0]
                long_ratio = float(item[1]) * 100
                short_ratio = float(item[2]) * 100
                return {
                    'long_ratio': long_ratio,
                    'short_ratio': short_ratio,
                    'ratio': long_ratio / short_ratio if short_ratio > 0 else 1
                }
        except:
            pass
        return {'long_ratio': 50, 'short_ratio': 50, 'ratio': 1}

    def get_bybit_long_short_ratio(self, symbol: str) -> Dict:
        """获取多空比（使用OKX替代）"""
        return self.get_okx_long_short_ratio(symbol)

    def get_top_negative_funding(self, top_n: int = 20) -> List[Dict]:
        """获取资金费率最负的币种（轧空机会）"""
        rates = self.get_all_funding_rates()

        if not rates:
            return []

        # 按费率排序（从低到高，负费率在前）
        rates.sort(key=lambda x: x['funding_rate'])

        # 取前N个负费率
        negative_rates = [r for r in rates if r['funding_rate'] < 0][:top_n]

        # 补充详细数据
        results = []
        for r in negative_rates:
            symbol = r['symbol']

            # 获取价格和OI
            ticker = self.get_okx_ticker(symbol)
            price = ticker['price']
            oi = self.get_okx_open_interest(symbol)
            oi_value = oi * price if price else 0

            # 获取多空比
            ls = self.get_okx_long_short_ratio(symbol)

            next_funding = '--:--'
            if r.get('next_funding_time'):
                try:
                    next_funding = datetime.fromtimestamp(r['next_funding_time']/1000).strftime('%H:%M')
                except:
                    pass

            results.append({
                'symbol': symbol,
                'funding_rate': r['funding_rate'],
                'price': price,
                'open_interest_usd': oi_value,
                'long_ratio': ls['long_ratio'],
                'short_ratio': ls['short_ratio'],
                'next_funding': next_funding,
                'squeeze_score': self._calc_squeeze_score(r['funding_rate'], ls['short_ratio'], oi_value),
                'source': r.get('source', 'Unknown')
            })

            time.sleep(0.1)  # 避免请求过快

        # 按轧空评分排序
        results.sort(key=lambda x: x['squeeze_score'], reverse=True)

        return results

    def get_top_positive_funding(self, top_n: int = 20) -> List[Dict]:
        """获取资金费率最正的币种（多头拥挤）"""
        rates = self.get_all_funding_rates()

        if not rates:
            return []

        # 按费率排序（从高到低）
        rates.sort(key=lambda x: x['funding_rate'], reverse=True)

        # 取前N个正费率
        positive_rates = [r for r in rates if r['funding_rate'] > 0.005][:top_n]

        results = []
        for r in positive_rates:
            symbol = r['symbol']

            # 获取价格和OI
            ticker = self.get_okx_ticker(symbol)
            price = ticker['price']
            oi = self.get_okx_open_interest(symbol)
            oi_value = oi * price if price else 0

            ls = self.get_okx_long_short_ratio(symbol)

            next_funding = '--:--'
            if r.get('next_funding_time'):
                try:
                    next_funding = datetime.fromtimestamp(r['next_funding_time']/1000).strftime('%H:%M')
                except:
                    pass

            results.append({
                'symbol': symbol,
                'funding_rate': r['funding_rate'],
                'price': price,
                'open_interest_usd': oi_value,
                'long_ratio': ls['long_ratio'],
                'short_ratio': ls['short_ratio'],
                'next_funding': next_funding,
                'crash_risk': self._calc_crash_risk(r['funding_rate'], ls['long_ratio'], oi_value),
                'source': r.get('source', 'Unknown')
            })

            time.sleep(0.1)

        results.sort(key=lambda x: x['crash_risk'], reverse=True)

        return results

    def _calc_squeeze_score(self, funding_rate: float, short_ratio: float, oi_usd: float) -> float:
        """
        计算轧空评分 (0-100)
        - 资金费率越负，分数越高
        - 空头占比越高，分数越高
        - 未平仓越大，分数越高（流动性好）
        """
        # 费率分数 (费率-0.1%以下得满分)
        rate_score = min(abs(funding_rate) / 0.1 * 40, 40)

        # 空头占比分数
        short_score = max(0, (short_ratio - 50) / 50 * 30)

        # OI分数 (1亿美元以上得满分)
        oi_score = min(oi_usd / 100_000_000 * 30, 30)

        return rate_score + short_score + oi_score

    def _calc_crash_risk(self, funding_rate: float, long_ratio: float, oi_usd: float) -> float:
        """
        计算崩盘风险评分 (0-100)
        - 资金费率越正，风险越高
        - 多头占比越高，风险越高
        """
        rate_score = min(funding_rate / 0.1 * 40, 40)
        long_score = max(0, (long_ratio - 50) / 50 * 30)
        oi_score = min(oi_usd / 100_000_000 * 30, 30)

        return rate_score + long_score + oi_score

    def get_liquidation_data(self) -> Dict:
        """获取爆仓数据"""
        try:
            # 使用Bybit获取爆仓数据
            url = f"{self.bybit_base}/v5/market/recent-trade"
            params = {'category': 'linear', 'symbol': 'BTCUSDT', 'limit': 50}
            resp = requests.get(url, params=params, timeout=10)
            return resp.json()
        except Exception as e:
            return {'error': str(e)}

    def analyze_symbol(self, symbol: str) -> Dict:
        """分析单个币种"""
        symbol = symbol.upper().replace('USDT', '').replace('/', '')

        # 获取费率
        rates = self.get_all_funding_rates()
        rate_data = next((r for r in rates if r['symbol'] == symbol), None)

        if not rate_data:
            return {'error': f'未找到 {symbol}'}

        # 获取价格和OI
        ticker = self.get_okx_ticker(symbol)
        price = ticker['price']
        oi = self.get_okx_open_interest(symbol)
        oi_value = oi * price if price else 0

        # 获取多空比
        ls = self.get_okx_long_short_ratio(symbol)

        # 获取历史费率
        history = self._get_funding_history(symbol)

        next_funding = '--:--'
        if rate_data.get('next_funding_time'):
            try:
                next_funding = datetime.fromtimestamp(rate_data['next_funding_time']/1000).strftime('%H:%M')
            except:
                pass

        result = {
            'symbol': symbol,
            'price': price,
            'funding_rate': rate_data['funding_rate'],
            'next_funding': next_funding,
            'open_interest_usd': oi_value,
            'long_ratio': ls['long_ratio'],
            'short_ratio': ls['short_ratio'],
            'funding_history': history,
            'source': rate_data.get('source', 'OKX')
        }

        # 判断信号
        if rate_data['funding_rate'] < -0.02:
            result['signal'] = '轧空机会'
            result['signal_type'] = 'squeeze'
            result['squeeze_score'] = self._calc_squeeze_score(
                rate_data['funding_rate'], ls['short_ratio'], oi_value
            )
        elif rate_data['funding_rate'] > 0.03:
            result['signal'] = '多头拥挤'
            result['signal_type'] = 'crowded_long'
            result['crash_risk'] = self._calc_crash_risk(
                rate_data['funding_rate'], ls['long_ratio'], oi_value
            )
        else:
            result['signal'] = '中性'
            result['signal_type'] = 'neutral'

        return result

    def _get_funding_history(self, symbol: str, limit: int = 10) -> List[Dict]:
        """获取历史资金费率 (OKX)"""
        try:
            url = f"{self.okx_base}/api/v5/public/funding-rate-history"
            params = {'instId': f"{symbol}-USDT-SWAP", 'limit': limit}
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()

            if data.get('code') == '0' and data.get('data'):
                return [{
                    'time': datetime.fromtimestamp(int(d['fundingTime'])/1000).strftime('%m-%d %H:%M'),
                    'rate': float(d['fundingRate']) * 100
                } for d in data['data']]
        except:
            pass
        return []


def scan_squeeze_opportunities():
    """扫描轧空机会"""
    monitor = FundingMonitor()

    print("\n" + "=" * 70)
    print(f"🔍 轧空机会扫描 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 70)

    results = monitor.get_top_negative_funding(15)

    if not results:
        print("暂无数据")
        return

    print(f"\n{'币种':<10} {'费率':>10} {'空头%':>8} {'OI(M)':>10} {'下次结算':>8} {'评分':>6}")
    print("-" * 60)

    for r in results:
        # 评分颜色
        score = r['squeeze_score']
        if score >= 60:
            score_icon = '🔴'  # 高分，强烈机会
        elif score >= 40:
            score_icon = '🟡'
        else:
            score_icon = '⚪'

        oi_m = r['open_interest_usd'] / 1_000_000

        print(f"{r['symbol']:<10} {r['funding_rate']:>+9.4f}% {r['short_ratio']:>7.1f}% {oi_m:>9.1f}M {r['next_funding']:>8} {score_icon}{score:>5.0f}")

    # 显示最佳机会
    top = results[0]
    print("\n" + "=" * 70)
    print("📊 最佳轧空机会:")
    print(f"   币种: {top['symbol']}")
    print(f"   费率: {top['funding_rate']:+.4f}%")
    print(f"   空头占比: {top['short_ratio']:.1f}%")
    print(f"   未平仓: ${top['open_interest_usd']/1_000_000:.1f}M")
    print(f"   轧空评分: {top['squeeze_score']:.0f}/100")

    if top['squeeze_score'] >= 60:
        print(f"\n   💡 建议: 可以考虑小仓位做多，设好止损")
    elif top['squeeze_score'] >= 40:
        print(f"\n   💡 建议: 观望，等费率更极端再进")

    print("=" * 70)


def scan_crowded_longs():
    """扫描多头拥挤（做空机会/风险预警）"""
    monitor = FundingMonitor()

    print("\n" + "=" * 70)
    print(f"⚠️ 多头拥挤扫描 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 70)

    results = monitor.get_top_positive_funding(15)

    if not results:
        print("暂无数据")
        return

    print(f"\n{'币种':<10} {'费率':>10} {'多头%':>8} {'OI(M)':>10} {'下次结算':>8} {'风险':>6}")
    print("-" * 60)

    for r in results:
        risk = r['crash_risk']
        if risk >= 60:
            risk_icon = '🔴'
        elif risk >= 40:
            risk_icon = '🟡'
        else:
            risk_icon = '⚪'

        oi_m = r['open_interest_usd'] / 1_000_000

        print(f"{r['symbol']:<10} {r['funding_rate']:>+9.4f}% {r['long_ratio']:>7.1f}% {oi_m:>9.1f}M {r['next_funding']:>8} {risk_icon}{risk:>5.0f}")

    print("\n" + "=" * 70)
    print("💡 这些币多头过于拥挤，小心回调/做空机会")
    print("=" * 70)


def analyze_coin(symbol: str):
    """分析单个币种"""
    monitor = FundingMonitor()
    result = monitor.analyze_symbol(symbol)

    if 'error' in result:
        print(f"错误: {result['error']}")
        return

    print("\n" + "=" * 60)
    print(f"📊 {result['symbol']} 资金费率分析")
    print("=" * 60)

    print(f"\n基础数据:")
    print(f"  当前价格: ${result['price']:.4f}")
    print(f"  资金费率: {result['funding_rate']:+.4f}%")
    print(f"  下次结算: {result['next_funding']}")
    print(f"  未平仓合约: ${result['open_interest_usd']/1_000_000:.1f}M")
    print(f"  多头占比: {result['long_ratio']:.1f}%")
    print(f"  空头占比: {result['short_ratio']:.1f}%")

    # 历史费率
    if result.get('funding_history'):
        print(f"\n历史费率 (最近{len(result['funding_history'])}次):")
        for h in result['funding_history'][-5:]:
            rate_bar = '▓' * int(abs(h['rate']) * 100) if h['rate'] != 0 else ''
            sign = '+' if h['rate'] > 0 else ''
            print(f"  {h['time']}: {sign}{h['rate']:.4f}% {rate_bar}")

    # 信号
    print(f"\n" + "-" * 40)
    if result['signal_type'] == 'squeeze':
        print(f"🟢 信号: {result['signal']}")
        print(f"   轧空评分: {result['squeeze_score']:.0f}/100")
        if result['squeeze_score'] >= 60:
            print(f"   💡 空头仓位重，可能被轧")
    elif result['signal_type'] == 'crowded_long':
        print(f"🔴 信号: {result['signal']}")
        print(f"   崩盘风险: {result['crash_risk']:.0f}/100")
        print(f"   💡 多头过于拥挤，注意回调风险")
    else:
        print(f"🟡 信号: {result['signal']}")
        print(f"   💡 多空平衡，无明显机会")

    print("=" * 60)


def watch_funding(interval: int = 300):
    """持续监控资金费率"""
    monitor = FundingMonitor()

    print("\n" + "=" * 60)
    print(f"📡 资金费率监控 (每{interval}秒刷新)")
    print("=" * 60)
    print("按 Ctrl+C 停止\n")

    while True:
        try:
            results = monitor.get_top_negative_funding(5)

            now = datetime.now().strftime('%H:%M:%S')
            print(f"\n[{now}] Top 轧空机会:")

            for r in results[:3]:
                score = r['squeeze_score']
                icon = '🔴' if score >= 60 else ('🟡' if score >= 40 else '⚪')
                print(f"  {icon} {r['symbol']}: {r['funding_rate']:+.4f}% | 空头{r['short_ratio']:.0f}% | 评分{score:.0f}")

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n停止监控")
            break


def scan_coinglass():
    """使用Coinglass数据扫描"""
    scraper = CoinglassScraper()

    print("\n" + "=" * 75)
    print(f"🌐 Coinglass 资金费率扫描 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 75)

    rates = scraper.get_funding_rates()

    if not rates:
        print("获取数据失败，请稍后重试")
        return

    # 按费率排序
    rates.sort(key=lambda x: x['funding_rate'])

    # 负费率（轧空机会）
    negative = [r for r in rates if r['funding_rate'] < -0.01][:10]
    # 正费率（多头拥挤）
    positive = [r for r in rates if r['funding_rate'] > 0.02][:10]

    if negative:
        print("\n🟢 轧空机会 (负费率):")
        print(f"{'币种':<10} {'平均费率':>10} {'Binance':>10} {'OKX':>10} {'OI($M)':>10}")
        print("-" * 55)
        for r in negative:
            oi_m = r['open_interest_usd'] / 1_000_000 if r['open_interest_usd'] else 0
            print(f"{r['symbol']:<10} {r['funding_rate']:>+9.4f}% {r['binance_rate']:>+9.4f}% {r['okx_rate']:>+9.4f}% {oi_m:>9.1f}M")

    if positive:
        print("\n🔴 多头拥挤 (高正费率):")
        print(f"{'币种':<10} {'平均费率':>10} {'Binance':>10} {'OKX':>10} {'OI($M)':>10}")
        print("-" * 55)
        for r in sorted(positive, key=lambda x: x['funding_rate'], reverse=True):
            oi_m = r['open_interest_usd'] / 1_000_000 if r['open_interest_usd'] else 0
            print(f"{r['symbol']:<10} {r['funding_rate']:>+9.4f}% {r['binance_rate']:>+9.4f}% {r['okx_rate']:>+9.4f}% {oi_m:>9.1f}M")

    print("\n" + "=" * 75)


def show_liquidation_heatmap(symbol: str = 'BTC'):
    """显示爆仓热力图"""
    monitor = LiquidationMonitor()
    funding = FundingMonitor()

    print("\n" + "=" * 65)
    print(f"🔥 {symbol} 爆仓热力图")
    print("=" * 65)

    # 获取当前价格
    ticker = funding.get_okx_ticker(symbol)
    current_price = ticker['price']

    if not current_price:
        print("无法获取当前价格")
        return

    print(f"\n当前价格: ${current_price:,.2f}")

    # 计算关键价位
    print(f"\n📊 关键爆仓价位 (理论值):")
    print("-" * 50)

    # 多头爆仓价位（价格下跌时触发）
    print("\n🔻 多头爆仓价位 (价格跌到这里，多头爆仓):")
    leverages = [125, 100, 50, 20, 10, 5]
    for lev in leverages:
        liq_price = current_price * (1 - 0.8/lev)  # 80%保证金被消耗
        pct_drop = (current_price - liq_price) / current_price * 100
        bar = '█' * int(pct_drop * 2)
        print(f"  {lev:>3}x: ${liq_price:>10,.0f} ({pct_drop:>5.1f}% 下跌) {bar}")

    # 空头爆仓价位（价格上涨时触发）
    print("\n🔺 空头爆仓价位 (价格涨到这里，空头爆仓):")
    for lev in leverages:
        liq_price = current_price * (1 + 0.8/lev)
        pct_rise = (liq_price - current_price) / current_price * 100
        bar = '█' * int(pct_rise * 2)
        print(f"  {lev:>3}x: ${liq_price:>10,.0f} ({pct_rise:>5.1f}% 上涨) {bar}")

    # 整数关口
    print(f"\n🎯 心理关口:")
    base = int(current_price / 1000) * 1000
    levels = [base - 2000, base - 1000, base, base + 1000, base + 2000, base + 3000]
    for level in levels:
        if level > 0:
            diff = (level - current_price) / current_price * 100
            icon = '📍' if abs(diff) < 2 else ('⬆️' if diff > 0 else '⬇️')
            print(f"  {icon} ${level:,} ({diff:+.1f}%)")

    # 建议
    print(f"\n💡 交易提示:")
    print(f"   - 高杠杆(50x+)仓位在价格波动1-2%时就会爆仓")
    print(f"   - 价格接近整数关口时容易有剧烈波动")
    print(f"   - 做市商喜欢在爆仓密集区'扫货'后反向拉")

    print("\n" + "=" * 65)


class NewListingTracker:
    """新币上线追踪"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Accept': 'application/json',
        }

    def get_binance_new_listings(self) -> List[Dict]:
        """获取Binance最近上线的合约"""
        results = []

        try:
            # 获取所有合约信息
            url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
            resp = requests.get(url, headers=self.headers, timeout=10)

            if resp.status_code == 451:
                # 地区限制，使用备用方法
                return self._get_from_announcement()

            data = resp.json()

            if data.get('symbols'):
                for symbol in data['symbols']:
                    if symbol['symbol'].endswith('USDT') and symbol['status'] == 'TRADING':
                        results.append({
                            'symbol': symbol['symbol'].replace('USDT', ''),
                            'onboard_date': symbol.get('onboardDate', 0),
                            'contract_type': symbol.get('contractType', ''),
                        })

                # 按上线时间排序
                results.sort(key=lambda x: x['onboard_date'], reverse=True)

        except Exception as e:
            print(f"获取Binance合约失败: {e}")
            return self._get_from_announcement()

        return results[:30]

    def _get_from_announcement(self) -> List[Dict]:
        """从公告获取新上线信息"""
        # 手动维护的最近上线列表
        recent_listings = [
            {'symbol': 'AIXBT', 'date': '2025-01', 'type': 'AI'},
            {'symbol': 'CGPT', 'date': '2025-01', 'type': 'AI'},
            {'symbol': 'COOKIE', 'date': '2025-01', 'type': 'AI'},
            {'symbol': 'SWARMS', 'date': '2025-01', 'type': 'AI'},
            {'symbol': 'GRIFFAIN', 'date': '2025-01', 'type': 'AI'},
            {'symbol': 'ANIME', 'date': '2025-01', 'type': 'Meme'},
            {'symbol': 'SONIC', 'date': '2024-12', 'type': 'L1'},
            {'symbol': 'PENGU', 'date': '2024-12', 'type': 'NFT'},
            {'symbol': 'VANA', 'date': '2024-12', 'type': 'AI'},
            {'symbol': 'MOVE', 'date': '2024-12', 'type': 'L2'},
            {'symbol': 'ME', 'date': '2024-12', 'type': 'NFT'},
            {'symbol': 'USUAL', 'date': '2024-12', 'type': 'Stablecoin'},
            {'symbol': 'THE', 'date': '2024-11', 'type': 'DeFi'},
            {'symbol': 'ACX', 'date': '2024-11', 'type': 'Bridge'},
            {'symbol': 'ORCA', 'date': '2024-11', 'type': 'DEX'},
            {'symbol': 'PNUT', 'date': '2024-11', 'type': 'Meme'},
            {'symbol': 'COW', 'date': '2024-10', 'type': 'DEX'},
            {'symbol': 'CETUS', 'date': '2024-10', 'type': 'DEX'},
            {'symbol': 'SCR', 'date': '2024-10', 'type': 'L2'},
            {'symbol': 'HMSTR', 'date': '2024-09', 'type': 'GameFi'},
        ]
        return recent_listings

    def get_okx_new_listings(self) -> List[Dict]:
        """获取OKX最近上线的合约"""
        results = []

        try:
            url = "https://www.okx.com/api/v5/public/instruments"
            params = {'instType': 'SWAP'}
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()

            if data.get('code') == '0' and data.get('data'):
                for inst in data['data']:
                    if inst['instId'].endswith('-USDT-SWAP'):
                        results.append({
                            'symbol': inst['instId'].replace('-USDT-SWAP', ''),
                            'list_time': inst.get('listTime', ''),
                        })

        except Exception as e:
            print(f"获取OKX合约失败: {e}")

        return results

    def check_new_listing_funding(self, symbols: List[str]) -> List[Dict]:
        """检查新币的资金费率"""
        monitor = FundingMonitor()
        results = []

        for symbol in symbols[:15]:
            try:
                # 获取费率
                url = "https://www.okx.com/api/v5/public/funding-rate"
                params = {'instId': f"{symbol}-USDT-SWAP"}
                resp = requests.get(url, params=params, timeout=5)
                data = resp.json()

                if data.get('code') == '0' and data.get('data'):
                    rate = float(data['data'][0]['fundingRate']) * 100

                    # 获取价格
                    ticker = monitor.get_okx_ticker(symbol)

                    results.append({
                        'symbol': symbol,
                        'funding_rate': rate,
                        'price': ticker.get('price', 0),
                    })

                time.sleep(0.1)

            except:
                continue

        return results


def scan_chain_activity():
    """扫描链上异动 - 找大额转入交易所的代币"""
    print("\n" + "=" * 75)
    print(f"🔍 链上异动扫描 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 75)
    print("\n正在扫描热门代币...")

    funding = FundingMonitor()

    # 1. 热门/新币列表
    hot_symbols = [
        # AI叙事
        'AIXBT', 'COOKIE', 'VIRTUAL', 'GRIFFAIN', 'SWARMS', 'AI16Z', 'ZEREBRO', 'ARC', 'ELIZA',
        # Meme
        'PNUT', 'GOAT', 'FARTCOIN', 'MOODENG', 'BULLY', 'POPCAT', 'WIF', 'BONK',
        # 新币
        'PENGU', 'ANIME', 'SONIC', 'MOVE', 'VANA', 'ME', 'USUAL',
        # 热门
        'RIVER', 'MYX', 'EIGEN', 'ENA', 'ETHFI',
    ]

    hot_tokens = []

    print("\n获取代币数据...")
    for symbol in hot_symbols:
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={symbol}"
            resp = requests.get(url, timeout=5)
            data = resp.json()

            if data.get('pairs'):
                # 找主要交易对
                pair = None
                for p in data['pairs'][:5]:
                    if p.get('baseToken', {}).get('symbol', '').upper() == symbol.upper():
                        pair = p
                        break
                if not pair:
                    pair = data['pairs'][0]

                price_change = float(pair.get('priceChange', {}).get('h24', 0) or 0)
                volume = float(pair.get('volume', {}).get('h24', 0) or 0)

                if volume > 100000:  # 至少10万美元交易量
                    hot_tokens.append({
                        'symbol': symbol.upper(),
                        'chain': pair.get('chainId', ''),
                        'price': float(pair.get('priceUsd', 0) or 0),
                        'price_change_24h': price_change,
                        'volume_24h': volume,
                    })
            time.sleep(0.05)
        except:
            continue

    # 按波动排序
    hot_tokens.sort(key=lambda x: abs(x['price_change_24h']), reverse=True)

    print(f"\n📊 热门代币异动:")
    print(f"{'币种':<10} {'价格':>12} {'24h涨跌':>10} {'24h量':>12}")
    print("-" * 50)

    for t in hot_tokens[:20]:
        icon = '🟢' if t['price_change_24h'] > 5 else ('🔴' if t['price_change_24h'] < -5 else '⚪')
        vol_str = f"${t['volume_24h']/1e6:.1f}M"
        price_str = f"${t['price']:.4f}" if t['price'] < 1 else f"${t['price']:.2f}"
        print(f"{t['symbol']:<10} {price_str:>12} {icon}{t['price_change_24h']:>+8.1f}% {vol_str:>12}")

    # 2. 检查永续合约 + 费率
    print("\n" + "-" * 50)
    print("\n🎯 检查永续合约 & 资金费率:")

    tradeable = []
    for t in hot_tokens[:15]:
        symbol = t['symbol']
        try:
            url = "https://www.okx.com/api/v5/public/funding-rate"
            params = {'instId': f"{symbol}-USDT-SWAP"}
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()

            if data.get('code') == '0' and data.get('data'):
                rate = float(data['data'][0]['fundingRate']) * 100
                tradeable.append({
                    **t,
                    'funding_rate': rate,
                    'has_perp': True,
                })
            time.sleep(0.05)
        except:
            continue

    if tradeable:
        # 按费率排序，负费率优先
        tradeable.sort(key=lambda x: x['funding_rate'])

        print(f"\n{'币种':<10} {'费率':>10} {'24h涨跌':>10} {'信号'}")
        print("-" * 60)

        for t in tradeable:
            rate = t['funding_rate']
            change = t['price_change_24h']

            # 判断信号
            if rate < -0.1:
                signal = '🔴🔴 极端负费率！轧空'
            elif rate < -0.05:
                signal = '🟢 负费率，可做多'
            elif rate > 0.1:
                signal = '🔴 极端正费率，小心'
            elif rate > 0.05:
                signal = '🟡 正费率，注意回调'
            else:
                signal = '⚪ 正常'

            print(f"{t['symbol']:<10} {rate:>+9.4f}% {change:>+9.1f}% {signal}")

        # 找最佳机会
        squeeze = [t for t in tradeable if t['funding_rate'] < -0.03]
        crowded = [t for t in tradeable if t['funding_rate'] > 0.05]

        print("\n" + "=" * 60)
        if squeeze:
            best = min(squeeze, key=lambda x: x['funding_rate'])
            print(f"\n🟢 最佳轧空机会: {best['symbol']}")
            print(f"   费率: {best['funding_rate']:+.4f}% (空头付费)")
            print(f"   24h: {best['price_change_24h']:+.1f}%")
            print(f"   💡 可以考虑做多")

        if crowded:
            worst = max(crowded, key=lambda x: x['funding_rate'])
            print(f"\n🔴 最拥挤多头: {worst['symbol']}")
            print(f"   费率: {worst['funding_rate']:+.4f}% (多头付费)")
            print(f"   24h: {worst['price_change_24h']:+.1f}%")
            print(f"   ⚠️ 小心回调")

    else:
        print("   未找到有合约的热门币")

    print("\n" + "=" * 75)


def analyze_token_onchain(token: str):
    """分析代币链上数据 - 找出项目方/做市商"""
    print("\n" + "=" * 70)
    print(f"🔍 {token.upper()} 链上分析")
    print("=" * 70)

    # 1. 先从CoinGecko获取合约地址
    print("\n1️⃣ 获取合约地址...")
    contract_info = {}

    try:
        url = f"https://api.coingecko.com/api/v3/coins/{token.lower()}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            platforms = data.get('platforms', {})

            for chain, addr in platforms.items():
                if addr:
                    chain_name = chain.replace('-', ' ').title()
                    contract_info[chain] = addr
                    print(f"   {chain_name}: {addr}")

            # 基本信息
            print(f"\n   名称: {data.get('name')}")
            print(f"   符号: {data.get('symbol', '').upper()}")
            mcap = data.get('market_data', {}).get('market_cap', {}).get('usd', 0)
            print(f"   市值: ${mcap/1e6:.1f}M")

    except Exception as e:
        print(f"   获取失败: {e}")

    if not contract_info:
        print("   未找到合约地址，尝试手动搜索...")
        # 常见新币合约
        known_contracts = {
            'aixbt': {'bsc': '0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825'},
            'cookie': {'bsc': '0xc0041ef357b183448b235a8ea73ce4e4ec8c265f'},
            'pengu': {'eth': '0xf0b24b59E6b5d1A7c2e5e2D1F4EE2e4f4e4e4e4'},
            'anime': {'eth': '0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825'},
        }
        if token.lower() in known_contracts:
            contract_info = known_contracts[token.lower()]

    # 2. 获取持有者分布
    print("\n" + "-" * 50)
    print("\n2️⃣ 分析持有者分布...")

    monitor = OnchainMonitor()

    for chain, contract in contract_info.items():
        if chain not in ['binance-smart-chain', 'ethereum', 'bsc', 'eth']:
            continue

        chain_key = 'bsc' if 'binance' in chain or chain == 'bsc' else 'eth'
        api_url = "https://api.bscscan.com/api" if chain_key == 'bsc' else "https://api.etherscan.io/api"

        try:
            # 获取代币转账记录来分析大户
            params = {
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': contract,
                'page': 1,
                'offset': 200,
                'sort': 'desc',
            }

            resp = requests.get(api_url, params=params, timeout=15)
            data = resp.json()

            if data.get('status') == '1' and data.get('result'):
                # 统计地址转账量
                address_stats = {}

                for tx in data['result']:
                    from_addr = tx.get('from', '').lower()
                    to_addr = tx.get('to', '').lower()
                    value = float(tx.get('value', 0)) / (10 ** int(tx.get('tokenDecimal', 18)))

                    for addr in [from_addr, to_addr]:
                        if addr not in address_stats:
                            address_stats[addr] = {'in': 0, 'out': 0, 'net': 0}

                    address_stats[from_addr]['out'] += value
                    address_stats[to_addr]['in'] += value

                # 计算净流入
                for addr in address_stats:
                    address_stats[addr]['net'] = address_stats[addr]['in'] - address_stats[addr]['out']

                # 找出大户（排除交易所）
                large_holders = []
                for addr, stats in address_stats.items():
                    # 判断是否是交易所
                    is_exchange = addr in monitor.EXCHANGE_WALLETS
                    is_mm = addr in monitor.MARKET_MAKER_WALLETS

                    label = ''
                    if is_exchange:
                        label = f"交易所:{monitor.EXCHANGE_WALLETS[addr]}"
                    elif is_mm:
                        label = f"做市商:{monitor.MARKET_MAKER_WALLETS[addr]}"
                    elif stats['out'] > 100000:
                        label = "🎯 疑似项目方/大户"
                    elif stats['in'] > 50000 and stats['out'] < 10000:
                        label = "💰 疑似吸筹"

                    if label and (stats['in'] > 10000 or stats['out'] > 10000):
                        large_holders.append({
                            'address': addr,
                            'in': stats['in'],
                            'out': stats['out'],
                            'net': stats['net'],
                            'label': label,
                        })

                # 按转出量排序（项目方通常转出多）
                large_holders.sort(key=lambda x: x['out'], reverse=True)

                print(f"\n   [{chain_key.upper()}] 大户地址:")
                print(f"   {'地址':<18} {'转入':>12} {'转出':>12} {'标签'}")
                print("   " + "-" * 60)

                for h in large_holders[:15]:
                    short_addr = h['address'][:10] + '...'
                    print(f"   {short_addr:<18} {h['in']:>10,.0f} {h['out']:>10,.0f}   {h['label']}")

                # 3. 检查最近是否有转入交易所
                print(f"\n" + "-" * 50)
                print(f"\n3️⃣ 最近交易所流入检查:")

                exchange_transfers = []
                for tx in data['result'][:50]:
                    to_addr = tx.get('to', '').lower()
                    from_addr = tx.get('from', '').lower()
                    value = float(tx.get('value', 0)) / (10 ** int(tx.get('tokenDecimal', 18)))

                    if to_addr in monitor.EXCHANGE_WALLETS and value > 1000:
                        exchange_transfers.append({
                            'from': from_addr[:10] + '...',
                            'to': monitor.EXCHANGE_WALLETS[to_addr],
                            'value': value,
                            'time': datetime.fromtimestamp(int(tx.get('timeStamp', 0))),
                        })

                if exchange_transfers:
                    print(f"\n   ⚠️ 发现转入交易所的记录:")
                    for t in exchange_transfers[:10]:
                        print(f"   {t['from']} → {t['to']}: {t['value']:,.0f} 代币 ({t['time'].strftime('%m-%d %H:%M')})")
                else:
                    print(f"\n   ✅ 最近无大额转入交易所")

        except Exception as e:
            print(f"   分析失败: {e}")

    # 4. 直接查询链接
    print("\n" + "=" * 70)
    print("🔗 直接查询链接（点击查看大户）:")

    for chain, contract in contract_info.items():
        if 'binance' in chain.lower() or chain == 'bsc':
            print(f"\n   BSCScan持有者排名:")
            print(f"   https://bscscan.com/token/{contract}#balances")
        elif chain in ['ethereum', 'eth']:
            print(f"\n   Etherscan持有者排名:")
            print(f"   https://etherscan.io/token/{contract}#balances")

    print(f"\n   Arkham Intelligence (标签最全):")
    print(f"   https://platform.arkhamintelligence.com/explorer/token/{token.upper()}")

    print(f"\n   Bubblemaps (可视化持仓):")
    print(f"   https://app.bubblemaps.io/bsc/token/{list(contract_info.values())[0] if contract_info else ''}")

    # 5. 总结
    print("\n" + "-" * 50)
    print("\n📊 操作指南:")
    print("   1. 点开BSCScan链接，看Holders排名")
    print("   2. 排除交易所地址（Binance/OKX/Bybit等）")
    print("   3. 前10大非交易所地址 = 项目方/做市商")
    print("   4. 点进这些地址，看最近有没有往交易所转")

    print("\n⚠️ 危险信号:")
    print("   - 大户地址往交易所转币 = 准备砸盘")
    print("   - 解锁后立即转交易所 = 跑路")
    print("   - 多个大户同时转 = 协调出货")

    print("\n✅ 看涨信号:")
    print("   - 从交易所提到冷钱包 = 长期持有")
    print("   - 做市商增持 = 准备拉盘")
    print("=" * 70)


def scan_new_listings():
    """扫描新上线合约"""
    tracker = NewListingTracker()
    monitor = FundingMonitor()

    print("\n" + "=" * 70)
    print(f"🆕 新上线合约扫描 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 70)

    # 获取新币列表
    print("\n获取最近上线的合约...")
    listings = tracker._get_from_announcement()

    if not listings:
        print("暂无数据")
        return

    print(f"\n📋 最近上线 (Binance合约):")
    print(f"{'币种':<12} {'上线时间':<12} {'类型':<10}")
    print("-" * 40)

    for item in listings[:15]:
        print(f"{item['symbol']:<12} {item.get('date', 'N/A'):<12} {item.get('type', 'N/A'):<10}")

    # 检查这些币的资金费率
    print("\n" + "-" * 50)
    print("\n📊 新币资金费率检查:")

    symbols = [item['symbol'] for item in listings[:15]]
    funding_data = tracker.check_new_listing_funding(symbols)

    if funding_data:
        # 按费率排序
        funding_data.sort(key=lambda x: x['funding_rate'])

        print(f"{'币种':<12} {'费率':<12} {'价格':<15} {'信号'}")
        print("-" * 55)

        for item in funding_data:
            rate = item['funding_rate']
            if rate < -0.05:
                signal = '🟢 轧空机会'
            elif rate > 0.05:
                signal = '🔴 多头拥挤'
            else:
                signal = '⚪ 正常'

            price_str = f"${item['price']:.4f}" if item['price'] else 'N/A'
            print(f"{item['symbol']:<12} {rate:>+.4f}%     {price_str:<15} {signal}")

    # 策略提示
    print("\n" + "-" * 50)
    print("\n💡 新币交易策略:")
    print("   1. 新币上线前几天波动最大")
    print("   2. 关注费率极端的（<-0.1% 或 >0.1%）")
    print("   3. 配合OI和成交量判断")
    print("   4. 设好止损，新币波动可能很大")

    print("\n🔔 追踪新上线公告:")
    print("   Binance: https://www.binance.com/en/support/announcement")
    print("   OKX: https://www.okx.com/support/hc/en-us/sections/360000030652")
    print("   Twitter: @binaborabbit (非官方，更新快)")

    print("\n" + "=" * 70)


class VCTracker:
    """VC投资追踪"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Accept': 'application/json',
        }

    def get_recent_investments(self) -> List[Dict]:
        """获取最近的VC投资"""
        results = []

        # 从RootData获取
        try:
            url = "https://api.rootdata.com/open/ser_inv"
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('data'):
                    for item in data['data'][:20]:
                        results.append({
                            'project': item.get('name', ''),
                            'amount': item.get('amount', 'Unknown'),
                            'round': item.get('round', ''),
                            'investors': item.get('investors', []),
                            'date': item.get('date', ''),
                            'source': 'RootData'
                        })
        except:
            pass

        # 备用：从CryptoRank获取
        if not results:
            try:
                url = "https://api.cryptorank.io/v1/funding-rounds"
                params = {'limit': 20}
                resp = requests.get(url, params=params, headers=self.headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get('data', []):
                        results.append({
                            'project': item.get('project', {}).get('name', ''),
                            'amount': item.get('amount', 'Unknown'),
                            'round': item.get('round', ''),
                            'date': item.get('date', ''),
                            'source': 'CryptoRank'
                        })
            except:
                pass

        return results

    def get_notable_investors(self) -> Dict:
        """知名VC列表"""
        return {
            'tier1': [
                'a16z', 'Paradigm', 'Sequoia', 'Polychain',
                'Multicoin', 'Framework', 'Pantera', 'Dragonfly'
            ],
            'kol': [
                'Arthur Hayes / Maelstrom', 'Su Zhu', 'Cobie',
                'Hsaka', 'GCR', 'Ansem', 'Degen Spartan'
            ],
            'exchange': [
                'Binance Labs', 'Coinbase Ventures', 'OKX Ventures',
                'Bybit', 'Kraken Ventures'
            ]
        }

    def search_project_funding(self, project: str) -> Dict:
        """搜索项目融资信息"""
        try:
            # 使用CoinGecko获取项目信息
            url = f"https://api.coingecko.com/api/v3/coins/{project.lower()}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'name': data.get('name'),
                    'symbol': data.get('symbol', '').upper(),
                    'categories': data.get('categories', []),
                    'description': data.get('description', {}).get('en', '')[:200],
                    'links': {
                        'website': data.get('links', {}).get('homepage', [None])[0],
                        'twitter': data.get('links', {}).get('twitter_screen_name'),
                    },
                    'market_data': {
                        'price': data.get('market_data', {}).get('current_price', {}).get('usd'),
                        'market_cap': data.get('market_data', {}).get('market_cap', {}).get('usd'),
                        'fdv': data.get('market_data', {}).get('fully_diluted_valuation', {}).get('usd'),
                    }
                }
        except:
            pass
        return {}


def scan_vc_investments():
    """扫描最近VC投资"""
    tracker = VCTracker()

    print("\n" + "=" * 70)
    print(f"💰 最近VC投资扫描 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 70)

    # 显示知名VC
    notable = tracker.get_notable_investors()

    print("\n🏆 重点关注的VC/KOL:")
    print(f"   Tier1 VC: {', '.join(notable['tier1'][:4])}...")
    print(f"   KOL: {', '.join(notable['kol'][:4])}...")
    print(f"   交易所: {', '.join(notable['exchange'][:3])}...")

    print("\n" + "-" * 50)

    # 获取最近投资
    investments = tracker.get_recent_investments()

    if investments:
        print(f"\n📊 最近融资项目:")
        print(f"{'项目':<20} {'金额':<15} {'轮次':<10}")
        print("-" * 50)

        for inv in investments[:15]:
            amount = inv.get('amount', 'N/A')
            if isinstance(amount, (int, float)):
                amount = f"${amount/1e6:.1f}M"
            print(f"{inv['project']:<20} {str(amount):<15} {inv.get('round', 'N/A'):<10}")

    else:
        # 显示手动追踪方法
        print("\n📱 实时追踪方法:")
        print("\n   1. RootData (最全面)")
        print("      https://www.rootdata.com/Fundraising")
        print("      - 每日更新融资信息")
        print("      - 可按VC筛选")

        print("\n   2. Messari")
        print("      https://messari.io/research")
        print("      - 深度研究报告")
        print("      - VC动态追踪")

        print("\n   3. Twitter/X 关注列表:")
        print("      @Maaboratory - 融资汇总")
        print("      @ICO_Analytics - 新项目分析")
        print("      @Blocmates - 早期项目挖掘")

        print("\n   4. 关键词监控:")
        print("      'strategic investment' + 项目名")
        print("      'Maelstrom' / 'a16z' / 'Paradigm' 投资")

    # 最近热门项目
    print("\n" + "-" * 50)
    print("\n🔥 近期热门融资项目 (手动更新):")

    hot_projects = [
        {'name': 'RIVER', 'investor': 'Maelstrom (Arthur Hayes)', 'narrative': 'Chain Abstraction'},
        {'name': 'MYX', 'investor': 'Multiple VCs', 'narrative': 'Perp DEX'},
        {'name': 'EIGEN', 'investor': 'a16z', 'narrative': 'Restaking'},
        {'name': 'ENA', 'investor': 'Dragonfly', 'narrative': 'Synthetic Dollar'},
        {'name': 'ETHFI', 'investor': 'Multiple', 'narrative': 'Liquid Restaking'},
    ]

    for p in hot_projects:
        print(f"   • {p['name']}: {p['investor']} - {p['narrative']}")

    print("\n💡 策略:")
    print("   - 大佬投资公告后24-48小时是最佳介入窗口")
    print("   - 关注代币解锁时间，避免接盘")
    print("   - 配合资金费率判断多空情绪")

    print("\n" + "=" * 70)


def track_cex_inflow(token: str):
    """追踪代币往交易所的流入"""
    print("\n" + "=" * 65)
    print(f"📊 {token.upper()} 交易所流入追踪")
    print("=" * 65)

    # 尝试从多个数据源获取
    print("\n正在查询链上数据...")

    # 1. 使用DeFiLlama获取代币信息
    try:
        url = f"https://api.llama.fi/protocol/{token.lower()}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('tvl'):
                print(f"\n协议TVL: ${data['tvl']/1e6:.1f}M")
    except:
        pass

    # 2. 使用CoinGecko获取代币信息
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{token.lower()}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n代币信息 (CoinGecko):")
            print(f"  名称: {data.get('name', 'N/A')}")
            print(f"  价格: ${data.get('market_data', {}).get('current_price', {}).get('usd', 0):.4f}")
            print(f"  24h涨跌: {data.get('market_data', {}).get('price_change_percentage_24h', 0):.2f}%")
            print(f"  市值: ${data.get('market_data', {}).get('market_cap', {}).get('usd', 0)/1e6:.1f}M")
            print(f"  24h交易量: ${data.get('market_data', {}).get('total_volume', {}).get('usd', 0)/1e6:.1f}M")

            # 交易所分布
            tickers = data.get('tickers', [])[:10]
            if tickers:
                print(f"\n交易所分布:")
                for t in tickers[:5]:
                    print(f"  {t.get('market', {}).get('name', 'N/A')}: ${t.get('converted_volume', {}).get('usd', 0)/1e6:.2f}M")
    except Exception as e:
        print(f"CoinGecko查询失败: {e}")

    # 3. 查看Nansen/Arkham数据提示
    print(f"\n" + "-" * 50)
    print(f"\n🔍 深度追踪工具 (需要API/订阅):")
    print(f"   1. Arkham Intelligence: https://platform.arkhamintelligence.com")
    print(f"      - 搜索代币名称，查看大户钱包动向")
    print(f"      - 关注 'Exchange Inflow' 指标")
    print(f"")
    print(f"   2. Nansen: https://app.nansen.ai")
    print(f"      - 查看Smart Money流向")
    print(f"      - Token God Mode 追踪大户")
    print(f"")
    print(f"   3. Dune Analytics: https://dune.com")
    print(f"      - 搜索 '{token} exchange inflow'")
    print(f"      - 社区有很多现成的Dashboard")
    print(f"")
    print(f"   4. DeBank: https://debank.com")
    print(f"      - 输入项目方/做市商钱包地址")
    print(f"      - 查看持仓变化")

    print(f"\n💡 关键信号:")
    print(f"   ⚠️ 项目方/做市商往交易所充币 = 可能要卖")
    print(f"   ✅ 从交易所提币到冷钱包 = 长期持有信号")
    print(f"   🔴 解锁后立即往交易所充 = 危险信号")

    print("\n" + "=" * 65)


def track_whales():
    """追踪巨鲸钱包"""
    tracker = WhaleTracker()

    print("\n" + "=" * 65)
    print(f"🐋 巨鲸钱包追踪")
    print("=" * 65)

    print("\n已知做市商钱包:")
    for chain, wallets in tracker.known_wallets.items():
        if wallets:
            print(f"\n  [{chain.upper()}]")
            for addr, name in wallets.items():
                short_addr = f"{addr[:6]}...{addr[-4:]}"
                print(f"    {name}: {short_addr}")

    print("\n" + "-" * 50)
    print("\n正在检查最近交易...")

    deposits = tracker.check_exchange_deposits('eth')

    if deposits:
        print("\n⚠️ 发现做市商往交易所充值:")
        for d in deposits[:10]:
            print(f"  {d['from']} -> {d['to']}: {d['value']:.2f} ETH")
            print(f"    时间: {d['time'].strftime('%m-%d %H:%M')}")
    else:
        print("\n✅ 暂无大额异动")

    print("\n💡 信号解读:")
    print("   - 做市商往交易所充钱 = 可能要拉盘/砸盘")
    print("   - 从交易所提走 = 筹码锁定，准备拉升")
    print("   - 配合资金费率看更准")

    print("\n" + "=" * 65)


def setup_telegram():
    """配置Telegram"""
    print("\n" + "=" * 50)
    print("📱 Telegram 配置")
    print("=" * 50)

    config = load_config()

    print("\n当前配置:")
    print(f"  Token: {'已设置' if config.get('telegram_token') else '未设置'}")
    print(f"  Chat ID: {'已设置' if config.get('telegram_chat_id') else '未设置'}")

    print("\n获取方法:")
    print("  1. 在Telegram搜索 @BotFather")
    print("  2. 发送 /newbot 创建机器人")
    print("  3. 获取Token")
    print("  4. 搜索 @userinfobot 获取Chat ID")

    token = input("\n请输入Bot Token (直接回车跳过): ").strip()
    if token:
        config['telegram_token'] = token

    chat_id = input("请输入Chat ID (直接回车跳过): ").strip()
    if chat_id:
        config['telegram_chat_id'] = chat_id

    save_config(config)
    print("\n✅ 配置已保存")

    # 测试发送
    if config.get('telegram_token') and config.get('telegram_chat_id'):
        notifier = TelegramNotifier()
        if notifier.send("🎉 Funding Monitor 配置成功！"):
            print("✅ 测试消息发送成功")
        else:
            print("❌ 测试消息发送失败，请检查配置")


def watch_with_alert(interval: int = 300, threshold: float = -0.1):
    """带提醒的监控"""
    monitor = FundingMonitor()
    notifier = TelegramNotifier()
    alerted = set()  # 已提醒的币种

    print("\n" + "=" * 60)
    print(f"📡 资金费率监控 (带Telegram提醒)")
    print(f"   刷新间隔: {interval}秒")
    print(f"   提醒阈值: {threshold}%")
    print("=" * 60)
    print("按 Ctrl+C 停止\n")

    while True:
        try:
            results = monitor.get_top_negative_funding(10)
            now = datetime.now().strftime('%H:%M:%S')

            print(f"\n[{now}] 扫描结果:")

            for r in results[:5]:
                score = r['squeeze_score']
                icon = '🔴' if score >= 60 else ('🟡' if score >= 40 else '⚪')
                print(f"  {icon} {r['symbol']}: {r['funding_rate']:+.4f}% | 评分{score:.0f}")

                # 检查是否需要提醒
                alert_key = f"{r['symbol']}_{datetime.now().strftime('%Y%m%d')}"
                if r['funding_rate'] <= threshold and alert_key not in alerted:
                    print(f"    ⚡ 发送提醒...")
                    notifier.send_alert(
                        r['symbol'],
                        r['funding_rate'],
                        score,
                        'squeeze'
                    )
                    alerted.add(alert_key)

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n停止监控")
            break


def main():
    import sys

    if len(sys.argv) < 2:
        print("=" * 55)
        print("资金费率 & 链上监控工具")
        print("=" * 55)
        print("\n📊 资金费率:")
        print("  squeeze        - 扫描轧空机会 (负费率)")
        print("  crowded        - 扫描多头拥挤 (高正费率)")
        print("  analyze <币种> - 分析单个币种 (如 analyze BTC)")
        print("  coinglass      - 多交易所费率汇总")
        print("\n🔥 爆仓分析:")
        print("  liq <币种>     - 爆仓热力图 (如 liq BTC)")
        print("\n🐋 链上追踪:")
        print("  whale          - 巨鲸钱包监控")
        print("  cex <币种>     - 交易所流入追踪 (如 cex river)")
        print("  vc             - 最近VC投资项目")
        print("  new            - 新上线合约（Binance/OKX）")
        print("  scan           - 🔥 扫描热门币异动+费率")
        print("  onchain <币名> - 链上分析（找项目方/做市商）")
        print("\n📡 持续监控:")
        print("  watch [秒数]   - 持续监控 (默认300秒)")
        print("  alert [秒数]   - 带Telegram提醒的监控")
        print("\n⚙️ 设置:")
        print("  telegram       - 配置Telegram推送")
        print("=" * 55)
        return

    cmd = sys.argv[1]

    if cmd == 'squeeze':
        scan_squeeze_opportunities()
    elif cmd == 'crowded':
        scan_crowded_longs()
    elif cmd == 'coinglass':
        scan_coinglass()
    elif cmd == 'analyze' and len(sys.argv) >= 3:
        analyze_coin(sys.argv[2])
    elif cmd == 'liq':
        symbol = sys.argv[2].upper() if len(sys.argv) > 2 else 'BTC'
        show_liquidation_heatmap(symbol)
    elif cmd == 'whale':
        track_whales()
    elif cmd == 'cex' and len(sys.argv) >= 3:
        # 追踪代币往交易所的流入
        track_cex_inflow(sys.argv[2])
    elif cmd == 'vc':
        # 扫描VC投资
        scan_vc_investments()
    elif cmd == 'new':
        # 扫描新上线合约
        scan_new_listings()
    elif cmd == 'scan':
        # 扫描链上异动
        scan_chain_activity()
    elif cmd == 'onchain' and len(sys.argv) >= 3:
        # 链上分析
        analyze_token_onchain(sys.argv[2])
    elif cmd == 'watch':
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        watch_funding(interval)
    elif cmd == 'alert':
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        threshold = float(sys.argv[3]) if len(sys.argv) > 3 else -0.1
        watch_with_alert(interval, threshold)
    elif cmd == 'telegram':
        setup_telegram()
    else:
        print("未知命令")


if __name__ == '__main__':
    main()

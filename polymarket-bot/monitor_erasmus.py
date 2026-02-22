#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控Erasmus的新仓位 - 实时跟单辅助工具

每4秒检查一次他的持仓变化，发现新仓位立即提醒

使用方法:
    python monitor_erasmus.py
"""

import httpx
import asyncio
import json
from datetime import datetime
from typing import Set, Dict, List

# Erasmus钱包地址
ERASMUS_ADDRESS = "0xc6587b11a2209e46dfe3928b31c5514a8e33b784"

# Polymarket API
API_URL = "https://data-api.polymarket.com/positions"

class ErasmusMonitor:
    """监控Erasmus的新开仓"""

    def __init__(self):
        self.known_positions: Set[str] = set()
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_current_positions(self) -> List[Dict]:
        """获取当前所有仓位"""
        url = f"{API_URL}?user={ERASMUS_ADDRESS}&sortBy=CURRENT&sortDirection=DESC"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            print(f"❌ API错误: {e}")
            return []

    def get_position_id(self, position: Dict) -> str:
        """生成仓位唯一ID"""
        market_slug = position.get('market', {}).get('slug', '')
        outcome = position.get('outcome', '')
        return f"{market_slug}:{outcome}"

    async def check_for_new_positions(self):
        """检查新仓位"""
        positions = await self.get_current_positions()

        new_positions = []

        for pos in positions:
            pos_id = self.get_position_id(pos)

            # 只关注规模>$1000的仓位
            current_value = float(pos.get('currentValue', 0))
            if current_value < 1000:
                continue

            # 检查是否为新仓位
            if pos_id not in self.known_positions:
                new_positions.append(pos)
                self.known_positions.add(pos_id)

        return new_positions

    def display_new_position(self, position: Dict):
        """显示新仓位提醒"""
        market_title = position.get('market', {}).get('question', 'Unknown Market')
        outcome = position.get('outcome', '')
        size = float(position.get('size', 0))
        current_price = float(position.get('curPrice', 0))
        initial_value = float(position.get('initialValue', 0))
        current_value = float(position.get('currentValue', 0))
        pnl_pct = ((current_value - initial_value) / initial_value * 100) if initial_value > 0 else 0

        print("\n" + "="*80)
        print(f"🚨 Erasmus新开仓！")
        print("="*80)
        print(f"📊 市场: {market_title}")
        print(f"📈 方向: {outcome}")
        print(f"💰 规模: ${current_value:,.0f}")
        print(f"💵 入场价: ${current_price:.4f}")
        print(f"📈 当前P&L: {pnl_pct:+.2f}%")
        print(f"⏰ 检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        print(f"\n🔗 查看市场: https://polymarket.com/event/{position.get('market', {}).get('slug', '')}")
        print("\n💡 建议:")
        print("   1. 访问上方链接查看市场详情")
        print("   2. 评估风险和流动性")
        print("   3. 计算凯利仓位")
        print("   4. 决定是否跟单\n")

    async def start(self):
        """启动监控"""
        print("="*80)
        print("  🔍 Erasmus跟单监控启动")
        print(f"  👤 监控地址: {ERASMUS_ADDRESS[:10]}...{ERASMUS_ADDRESS[-8:]}")
        print("  ⏱️  轮询间隔: 4秒")
        print("  📊 仓位阈值: $1,000+")
        print("="*80)

        # 首次加载：标记所有现有仓位为已知
        print("\n📥 初始化已知仓位...")
        initial_positions = await self.check_for_new_positions()
        print(f"✅ 已标记 {len(self.known_positions)} 个现有仓位")
        print("\n🎯 开始监控新仓位...\n")

        # 主循环
        check_count = 0
        while True:
            try:
                check_count += 1

                # 检查新仓位
                new_positions = await self.check_for_new_positions()

                if new_positions:
                    for pos in new_positions:
                        self.display_new_position(pos)
                else:
                    # 每分钟显示一次心跳
                    if check_count % 15 == 0:
                        print(f"⏳ {datetime.now().strftime('%H:%M:%S')} - 监控中...（已检查{check_count}次）")

                await asyncio.sleep(4)

            except KeyboardInterrupt:
                print("\n\n👋 停止监控")
                break
            except Exception as e:
                print(f"❌ 错误: {e}")
                await asyncio.sleep(10)

    async def close(self):
        """关闭资源"""
        await self.client.aclose()


async def main():
    monitor = ErasmusMonitor()
    try:
        await monitor.start()
    finally:
        await monitor.close()


if __name__ == '__main__':
    asyncio.run(main())

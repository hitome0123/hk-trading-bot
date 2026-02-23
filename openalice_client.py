#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAlice AI Agent 客户端
通过 HTTP API 与 OpenAlice 交互

功能：
1. 发送消息给 AI Agent
2. 获取交易建议
3. 执行策略分析
4. 查询持仓状态

使用前确保 OpenAlice 运行中：
  cd ~/OpenAlice && pnpm dev
"""

import json
import urllib.request
import urllib.parse
from typing import Dict, List, Optional, Any


class OpenAliceClient:
    """OpenAlice AI Agent 客户端"""

    def __init__(self, api_url: str = "http://127.0.0.1:3000",
                 chat_url: str = "http://127.0.0.1:3002"):
        self.api_url = api_url    # HTTP API (健康检查等)
        self.chat_url = chat_url  # Web UI API (聊天)

    def _request(self, endpoint: str, method: str = "GET",
                 data: Dict = None, use_chat: bool = False) -> Dict:
        """发送 API 请求"""
        base = self.chat_url if use_chat else self.api_url
        url = f"{base}{endpoint}"

        try:
            if method == "POST" and data:
                body = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(url, data=body, method="POST")
                req.add_header('Content-Type', 'application/json')
            else:
                req = urllib.request.Request(url)

            req.add_header('Accept', 'application/json')

            with urllib.request.urlopen(req, timeout=120) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return {"error": str(e)}

    def health_check(self) -> bool:
        """检查 OpenAlice 是否可用"""
        try:
            url = f"{self.api_url}/health"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("ok", False)
        except:
            return False

    def chat(self, message: str, session_id: str = "hk-trading-bot") -> Dict:
        """
        发送消息给 AI Agent

        Args:
            message: 消息内容
            session_id: 会话ID

        Returns:
            {'response': 'AI 回复', 'session_id': '...'}
        """
        result = self._request("/api/chat", method="POST", data={
            "message": message,
            "sessionId": session_id,
        }, use_chat=True)

        return result

    def analyze_stock(self, symbol: str) -> str:
        """
        请求 AI 分析股票

        Args:
            symbol: 股票代码 (如 9988.HK)

        Returns:
            AI 的分析结果
        """
        message = f"""请分析港股 {symbol}:
1. 当前估值是否合理
2. 技术面趋势
3. 近期利好/利空
4. 买入/卖出建议

请用中文回复。"""

        result = self.chat(message)
        return result.get("response", result.get("error", "无响应"))

    def get_trade_advice(self, stock: str, action: str = "buy") -> str:
        """
        获取交易建议

        Args:
            stock: 股票代码
            action: 'buy' 或 'sell'

        Returns:
            AI 的交易建议
        """
        if action == "buy":
            message = f"""我想买入 {stock}，请帮我分析：
1. 当前价格是否合适
2. 建议的买入价位
3. 止损点设在哪里
4. 仓位建议

我的策略是日内交易，止损2%，目标300-500港元日收益。"""
        else:
            message = f"""我持有 {stock}，想了解：
1. 当前是否应该卖出
2. 建议的卖出价位
3. 继续持有的风险
4. 止盈点建议"""

        result = self.chat(message)
        return result.get("response", result.get("error", "无响应"))

    def morning_brief(self) -> str:
        """
        获取每日早报

        Returns:
            今日市场概况和交易建议
        """
        message = """请给我今日港股早报：
1. 隔夜美股表现
2. 今日港股关注点
3. 热门板块预测
4. 推荐关注的个股

重点关注：AI芯片、人形机器人、创新药板块。"""

        result = self.chat(message)
        return result.get("response", result.get("error", "无响应"))

    def sector_scan(self, sector: str) -> str:
        """
        板块扫描

        Args:
            sector: 板块名称 (如 'AI芯片', '人形机器人')

        Returns:
            板块分析结果
        """
        message = f"""请分析港股 {sector} 板块：
1. 板块整体趋势
2. 龙头股表现
3. 资金流向
4. 最值得关注的2-3只股票及理由"""

        result = self.chat(message)
        return result.get("response", result.get("error", "无响应"))


# ==================== 便捷函数 ====================

_client = None

def get_alice() -> OpenAliceClient:
    """获取全局客户端实例"""
    global _client
    if _client is None:
        _client = OpenAliceClient()
    return _client


def ask_alice(question: str) -> str:
    """快速提问"""
    result = get_alice().chat(question)
    return result.get("response", str(result))


# ==================== 命令行入口 ====================

def main():
    import sys

    if len(sys.argv) < 2:
        print("""
OpenAlice AI Agent 客户端
========================

用法:
  python openalice_client.py check              # 检查API状态
  python openalice_client.py chat <消息>        # 发送消息
  python openalice_client.py analyze <股票>     # 分析股票
  python openalice_client.py advice <股票>      # 交易建议
  python openalice_client.py brief              # 早报
  python openalice_client.py sector <板块>      # 板块扫描

示例:
  python openalice_client.py analyze 9988.HK
  python openalice_client.py sector AI芯片
        """)
        return

    cmd = sys.argv[1]
    client = OpenAliceClient()

    if cmd == "check":
        if client.health_check():
            print("✅ OpenAlice 正常运行")
        else:
            print("❌ OpenAlice 不可用，请确保已启动:")
            print("   cd ~/OpenAlice && pnpm dev")

    elif cmd == "chat" and len(sys.argv) > 2:
        message = " ".join(sys.argv[2:])
        print(f"🤖 发送: {message}\n")
        result = client.chat(message)
        print(f"📝 回复:\n{result.get('response', result)}")

    elif cmd == "analyze" and len(sys.argv) > 2:
        symbol = sys.argv[2]
        print(f"🔍 分析 {symbol}...\n")
        result = client.analyze_stock(symbol)
        print(result)

    elif cmd == "advice" and len(sys.argv) > 2:
        symbol = sys.argv[2]
        action = sys.argv[3] if len(sys.argv) > 3 else "buy"
        print(f"💡 获取 {symbol} {action} 建议...\n")
        result = client.get_trade_advice(symbol, action)
        print(result)

    elif cmd == "brief":
        print("📰 获取今日早报...\n")
        result = client.morning_brief()
        print(result)

    elif cmd == "sector" and len(sys.argv) > 2:
        sector = sys.argv[2]
        print(f"📊 扫描 {sector} 板块...\n")
        result = client.sector_scan(sector)
        print(result)

    else:
        print(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()

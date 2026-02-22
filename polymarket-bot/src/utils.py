#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用工具函数

包含：
- 钱包地址验证
- API限流器
- 日志清理
"""

import re
from typing import Optional
from datetime import datetime, timedelta
from collections import deque
import structlog

logger = structlog.get_logger()


def validate_wallet_address(address: str) -> bool:
    """
    验证以太坊钱包地址格式

    格式: 0x + 40位十六进制字符
    示例: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb

    Args:
        address: 钱包地址字符串

    Returns:
        True如果格式正确，否则False
    """
    if not isinstance(address, str):
        return False

    # 以太坊地址: 0x + 40个十六进制字符
    pattern = r'^0x[a-fA-F0-9]{40}$'
    return bool(re.match(pattern, address))


def to_checksum_address(address: str) -> str:
    """
    转换为校验和地址（需要web3库）

    Args:
        address: 钱包地址

    Returns:
        校验和地址

    Raises:
        ValueError: 如果地址无效
    """
    try:
        from web3 import Web3
        return Web3.to_checksum_address(address)
    except ValueError as e:
        raise ValueError(f"无效的钱包地址: {address}") from e
    except ImportError:
        # 如果没有web3，至少验证格式
        if validate_wallet_address(address):
            return address
        raise ValueError(f"无效的钱包地址: {address}")


def sanitize_for_log(value: str, max_len: int = 100) -> str:
    """
    清理用户输入，使其可安全记录到日志

    防止：
    - 日志注入（换行符）
    - 日志膨胀（长字符串）

    Args:
        value: 要清理的字符串
        max_len: 最大长度

    Returns:
        清理后的字符串
    """
    # 移除换行符（防止日志注入）
    value = value.replace('\n', ' ').replace('\r', ' ')

    # 截断
    if len(value) > max_len:
        value = value[:max_len] + '...'

    return value


def truncate_wallet(address: str, show_start: int = 8, show_end: int = 6) -> str:
    """
    截断钱包地址用于显示

    Args:
        address: 完整钱包地址
        show_start: 显示开头几位
        show_end: 显示结尾几位

    Returns:
        截断后的地址，如 "0xABC123...89DEF0"
    """
    if len(address) < show_start + show_end + 2:  # 2 for "0x"
        return address

    return f"{address[:show_start]}...{address[-show_end:]}"


class APIRateLimiter:
    """
    API限流器 - 防止超出API调用限制

    使用滑动窗口算法追踪API调用
    """

    def __init__(
        self,
        max_calls: int = 1000,  # 每小时最大调用数
        window_seconds: int = 3600,  # 时间窗口（秒）
        warn_threshold: float = 0.9  # 警告阈值（90%）
    ):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.warn_threshold = warn_threshold
        self.calls: deque = deque()  # 存储调用时间戳
        self._warned = False

    def can_call(self) -> bool:
        """
        检查当前是否可以发起API调用

        Returns:
            True如果在限制内，否则False
        """
        self._cleanup_old_calls()
        return len(self.calls) < self.max_calls

    def record_call(self):
        """记录一次API调用"""
        self._cleanup_old_calls()
        self.calls.append(datetime.now())

        # 检查是否接近限制
        usage = len(self.calls) / self.max_calls
        if usage >= self.warn_threshold and not self._warned:
            logger.warning(
                "接近API限流上限",
                current_calls=len(self.calls),
                max_calls=self.max_calls,
                usage_pct=f"{usage:.1%}"
            )
            self._warned = True
        elif usage < self.warn_threshold:
            self._warned = False

    def _cleanup_old_calls(self):
        """清理时间窗口外的旧调用记录"""
        cutoff = datetime.now() - timedelta(seconds=self.window_seconds)
        while self.calls and self.calls[0] < cutoff:
            self.calls.popleft()

    def get_usage(self) -> dict:
        """
        获取当前使用情况

        Returns:
            包含使用统计的字典
        """
        self._cleanup_old_calls()
        return {
            'current_calls': len(self.calls),
            'max_calls': self.max_calls,
            'usage_pct': len(self.calls) / self.max_calls if self.max_calls > 0 else 0,
            'remaining': self.max_calls - len(self.calls),
            'window_seconds': self.window_seconds
        }

    def wait_time(self) -> float:
        """
        如果需要等待，返回等待秒数

        Returns:
            需要等待的秒数，如果可以立即调用则返回0
        """
        if self.can_call():
            return 0.0

        # 返回直到最老的调用过期的时间
        if self.calls:
            oldest_call = self.calls[0]
            expires_at = oldest_call + timedelta(seconds=self.window_seconds)
            wait_seconds = (expires_at - datetime.now()).total_seconds()
            return max(0.0, wait_seconds)

        return 0.0


def enforce_https(url: str) -> str:
    """
    确保URL使用HTTPS

    Args:
        url: 要检查的URL

    Returns:
        HTTPS URL

    Raises:
        ValueError: 如果URL使用HTTP
    """
    if not url.startswith('https://'):
        if url.startswith('http://'):
            raise ValueError(
                f"URL必须使用HTTPS，不安全: {url}\n"
                f"HTTP对金融数据不安全"
            )
        raise ValueError(f"无效的URL格式: {url}")

    return url


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    计算百分比变化

    Args:
        old_value: 旧值
        new_value: 新值

    Returns:
        变化百分比（0.0-1.0）
    """
    if old_value == 0:
        return 0.0 if new_value == 0 else float('inf')

    return (new_value - old_value) / abs(old_value)


# 测试函数
def main():
    """测试工具函数"""
    print("=== 钱包地址验证 ===")
    test_addresses = [
        "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",  # 有效
        "0xINVALID",  # 无效
        "'; DROP TABLE users; --",  # SQL注入尝试
        "0x123",  # 太短
    ]

    for addr in test_addresses:
        valid = validate_wallet_address(addr)
        print(f"{truncate_wallet(addr, 10, 6)}: {'✓' if valid else '✗'}")

    print("\n=== API限流测试 ===")
    limiter = APIRateLimiter(max_calls=5, window_seconds=10)

    for i in range(7):
        if limiter.can_call():
            limiter.record_call()
            print(f"调用 #{i+1}: ✓ 成功")
        else:
            wait = limiter.wait_time()
            print(f"调用 #{i+1}: ✗ 限流 (需等待{wait:.1f}秒)")

    usage = limiter.get_usage()
    print(f"\n使用情况: {usage['current_calls']}/{usage['max_calls']} ({usage['usage_pct']:.1%})")

    print("\n=== 日志清理测试 ===")
    dangerous_input = "用户输入\n恶意换行\r回车" + "A" * 200
    cleaned = sanitize_for_log(dangerous_input, max_len=50)
    print(f"原始长度: {len(dangerous_input)}")
    print(f"清理后: {cleaned}")


if __name__ == '__main__':
    main()

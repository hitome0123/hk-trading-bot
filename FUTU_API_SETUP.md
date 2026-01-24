# 富途 OpenAPI 接入指南

本指南帮助你配置和使用富途 OpenAPI 获取港股实时行情数据。

## 📋 目录

1. [为什么使用富途 OpenAPI](#为什么使用富途-openapi)
2. [前置要求](#前置要求)
3. [安装步骤](#安装步骤)
4. [使用方法](#使用方法)
5. [常见问题](#常见问题)

---

## 为什么使用富途 OpenAPI

### 🔥 优势

相比 Yahoo Finance API，富途 OpenAPI 提供：

- **✅ 稳定可靠**: 专业的港股数据源，不会被限流
- **✅ 实时数据**: 真实的实时行情数据
- **✅ 数据全面**: 支持港股、美股、A股
- **✅ 低延迟**: 订单执行最快 0.0014 秒
- **✅ 免费使用**: 无额外交易费用

### ⚠️ Yahoo Finance 的问题

- **限流严重**: `Too Many Requests. Rate limited`
- **连接不稳定**: `Connection reset by peer`
- **数据延迟**: 非实时数据
- **不可靠**: 经常无法获取港股数据

---

## 前置要求

### 1. 富途账号

- **富途牛牛账号**（牛牛号）或 **moomoo 账号**（moomoo号）
- 注册地址：
  - 富途牛牛: https://www.futunn.com/
  - moomoo: https://www.moomoo.com/

### 2. 系统要求

- **操作系统**: Windows / macOS / Linux
- **Python**: 3.7 或更高版本
- **网络**: 稳定的互联网连接

---

## 安装步骤

### 步骤 1: 下载并安装 FutuOpenD

FutuOpenD 是一个网关客户端，负责中转 API 请求到富途服务器。

#### 下载地址

- **官方下载**: https://www.futuhk.com/download/openAPI
- **GitHub Releases**: https://github.com/FutunnOpen/futu-api-doc/releases

#### 安装说明

1. **Windows**: 下载 `.exe` 安装包，双击安装
2. **macOS**: 下载 `.dmg` 文件，拖拽到 Applications
3. **Linux**: 下载对应版本的压缩包并解压

### 步骤 2: 启动 FutuOpenD

1. 打开 FutuOpenD 应用
2. 使用富途牛牛账号登录
3. 确保端口设置为 **11111**（默认）
4. 保持 FutuOpenD 运行（不要关闭）

### 步骤 3: 安装 Python SDK

在项目目录下运行：

```bash
pip install futu-api
```

或者安装所有依赖：

```bash
pip install -r requirements.txt
```

---

## 使用方法

### 方法 1: 运行测试脚本

测试富途 API 连接和数据获取：

```bash
python test_futu_api.py
```

测试菜单选项：
- **选项 1**: 测试连接
- **选项 2**: 测试股票数据获取（1801.HK）
- **选项 3**: 分析信达生物（1801.HK）
- **选项 4**: 全部测试（推荐）

### 方法 2: 在代码中使用

#### 基本用法

```python
from hk_trading_bot.data_providers.futu_provider import FutuProvider

# 创建数据提供器
provider = FutuProvider(host="127.0.0.1", port=11111)

# 连接
provider.connect()

# 获取当前价格
current_price = provider.get_current_price("1801.HK")
print(f"当前价格: {current_price} HKD")

# 获取历史数据（60天）
price_data = provider.get_price_data("1801.HK", days=60)

# 获取股票信息
stock_info = provider.get_stock_info("1801.HK")

# 断开连接
provider.disconnect()
```

#### 使用上下文管理器（推荐）

```python
from hk_trading_bot.data_providers.futu_provider import FutuProvider

# 自动连接和断开
with FutuProvider() as provider:
    current_price = provider.get_current_price("1801.HK")
    price_data = provider.get_price_data("1801.HK", days=60)
    stock_info = provider.get_stock_info("1801.HK")
```

### 方法 3: 分析信达生物

使用富途 API 分析信达生物（1801.HK）：

```bash
python test_futu_api.py
# 选择选项 3
```

或者在代码中：

```python
from hk_trading_bot.data_providers.futu_provider import FutuProvider
from hk_trading_bot.modules.indicators import TechnicalIndicators
from hk_trading_bot.modules.entry_pricing import EntryStrategy

with FutuProvider() as provider:
    ticker = "1801.HK"

    # 获取当前价格
    current_price = provider.get_current_price(ticker)

    # 获取历史数据
    price_data = provider.get_price_data(ticker, days=60)

    # 计算技术指标
    indicators_calc = TechnicalIndicators()
    indicators = indicators_calc.calculate_all_indicators(price_data)

    # 入场策略分析
    entry_strategy = EntryStrategy()
    entry_analysis = entry_strategy.calculate_entry_price(current_price, indicators)

    print(f"当前价格: {current_price} HKD")
    print(f"EMA20: {indicators['ema20']}")
    print(f"RSI14: {indicators['rsi14']}")
    print(f"交易信号: {entry_analysis['signal']}")
```

---

## 常见问题

### Q1: 无法连接到 FutuOpenD

**错误信息**: `❌ 连接 FutuOpenD 失败`

**解决方法**:
1. 确保 FutuOpenD 应用正在运行
2. 检查端口号是否为 11111
3. 确认已使用富途账号登录
4. 检查防火墙设置，允许 FutuOpenD 通信

### Q2: 无法获取数据

**错误信息**: `❌ 获取数据失败` 或 `订阅失败`

**解决方法**:
1. 确认股票代码格式正确（如 `1801.HK` 或 `01801.HK`）
2. 检查网络连接
3. 确认富途账号权限（部分数据需要开通权限）
4. 查看 FutuOpenD 日志获取详细错误信息

### Q3: FutuOpenD 闪退或崩溃

**解决方法**:
1. 重新启动 FutuOpenD
2. 更新到最新版本
3. 检查系统兼容性
4. 联系富途客服支持

### Q4: 数据延迟或不准确

**解决方法**:
1. 检查网络速度
2. 确认市场是否开盘（港股：9:30-16:00，周一至周五）
3. 使用实时订阅而非轮询
4. 升级到更快的网络连接

### Q5: 想要获取美股或A股数据

**解决方法**:

修改股票代码格式：
- **港股**: `HK.00700`（腾讯）
- **美股**: `US.AAPL`（苹果）
- **A股**: `SH.600000`（浦发银行）

在代码中使用相应格式即可。

---

## 📚 相关资源

- **富途 OpenAPI 官方文档**: https://openapi.futunn.com/futu-api-doc/
- **Python SDK GitHub**: https://github.com/FutunnOpen/py-futu-api
- **FutuOpenD 下载**: https://www.futuhk.com/download/openAPI
- **富途开发者社区**: https://openapi.futunn.com/

---

## 💡 技术支持

如有问题，可以：
1. 查看富途官方文档
2. 在项目 GitHub Issues 提问
3. 联系富途客服

---

## ⚠️ 免责声明

- 本项目仅用于学习和研究目的
- 使用富途 API 需遵守富途服务条款
- 交易有风险，投资需谨慎
- 不构成任何投资建议

---

**祝你使用愉快！** 🎉

# 富途OpenD API 启动指南

## 当前状态
- ✅ 富途OpenD应用已启动
- ❌ API服务未启动（端口11111未监听）
- ✅ 配置文件正确（127.0.0.1:11111）

## 手动启动步骤（推荐）

### 方法1：通过富途OpenD界面启动（最简单）

1. **打开富途OpenD应用**
   - 应该已经在 Dock 栏或应用列表中
   - 如果没看到窗口，点击 Dock 图标

2. **登录账号**
   - 使用您的富途账号登录
   - 如果已登录，跳过此步骤

3. **启用API服务**
   - 点击右上角的 **"设置"** 或 **齿轮图标**
   - 找到 **"API接入"** 或 **"开发者选项"**
   - 勾选 **"启用API"** 或 **"允许API连接"**
   - 端口保持 **11111** 不变
   - 点击 **"确定"** 或 **"保存"**

4. **验证启动成功**
   - 界面底部应该显示 **"API已启用"** 或类似提示
   - 状态栏应该显示绿色小点

### 方法2：重启富途OpenD（备选）

如果界面中找不到API设置：

1. **完全退出富途OpenD**
   ```bash
   killall FutuOpenD
   ```

2. **重新启动**
   ```bash
   open -a FutuOpenD
   ```

3. **等待5秒后检查端口**
   ```bash
   lsof -nP -iTCP:11111 | grep LISTEN
   ```

4. **如果仍然没有监听，需要在界面中手动启用（参考方法1）**

## 验证连接

启动成功后，运行以下命令测试：

```bash
cd ~/hk-trading-bot
python3 test_futu_api.py
```

预期输出：
```
✅ 富途OpenD连接成功
港股市场状态: ...
```

## 常见问题

### Q1: 找不到"API接入"选项
**A**: 不同版本的富途OpenD界面可能不同，请查找：
- "设置" → "API设置"
- "偏好设置" → "开发者"
- "更多" → "API管理"

### Q2: 提示"未登录"
**A**: 需要先登录富途账号才能使用API

### Q3: 端口被占用
**A**: 检查是否有其他程序使用11111端口
```bash
lsof -nP -iTCP:11111
```

### Q4: 仍然连接失败
**A**: 尝试：
1. 重启富途OpenD
2. 检查防火墙设置
3. 确认富途账号有API权限

## 自动检测脚本

运行此脚本检查连接状态：

```bash
cd ~/hk-trading-bot
python3 << 'EOF'
import socket

def check_futu_api():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', 11111))
        sock.close()

        if result == 0:
            print("✅ 富途OpenD API 已启动（端口11111可连接）")
            return True
        else:
            print("❌ 富途OpenD API 未启动（端口11111无法连接）")
            print("\n请按照以下步骤操作：")
            print("1. 打开富途OpenD应用")
            print("2. 登录账号")
            print("3. 设置 → API接入 → 启用API")
            return False
    except Exception as e:
        print(f"❌ 检测失败: {e}")
        return False

check_futu_api()
EOF
```

## 启动后可用功能

API启动成功后，您可以：

1. **实时获取股票数据**
   ```bash
   python3 quick_analysis.py 1024
   ```

2. **全市场扫描**
   ```bash
   python3 full_market_scanner.py
   ```

3. **T+0监控**
   ```bash
   python3 t0_check_now.py 1024
   ```

4. **实时盯盘**
   ```bash
   python3 kuaishou_t0_simple.py
   ```

---

**需要帮助？** 启动富途OpenD后，我可以帮您：
- 验证API连接
- 开始实时监控股票
- 设置价格提醒

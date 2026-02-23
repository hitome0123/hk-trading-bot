# 富途App抓包指南 - 获取评论和资讯API

## 目标数据
从你的截图可以看到需要获取：
1. **猜涨跌投票** - 79%看涨 vs 21%看跌
2. **评论列表** - 用户名、时间、内容、点赞数
3. **资讯快讯** - 股票相关新闻

---

## 方案A：Mac上使用Charles抓包（推荐）

### 1. 安装Charles
```bash
# 使用Homebrew安装
brew install --cask charles

# 或者下载：https://www.charlesproxy.com/download/
```

### 2. 配置Charles
1. 打开Charles
2. 菜单 → Proxy → Proxy Settings → 端口设为 `8888`
3. 菜单 → Proxy → SSL Proxying Settings → 添加 `*.futunn.com`

### 3. iPhone连接代理
1. iPhone和Mac连同一WiFi
2. iPhone → 设置 → WiFi → 点击已连接的WiFi → 配置代理 → 手动
   - 服务器：Mac的IP地址（终端输入 `ifconfig | grep inet`）
   - 端口：8888
3. 在iPhone Safari打开 `chls.pro/ssl` 安装证书
4. 设置 → 通用 → 关于本机 → 证书信任设置 → 启用Charles证书

### 4. 抓包操作
1. 打开富途App
2. 进入优必选(09880)的评论区
3. Charles会捕获所有请求
4. 过滤 `futunn.com` 相关请求

### 5. 预期会看到的API
```
# 评论列表
https://api.futunn.com/xxx/comments?stock_code=09880

# 猜涨跌
https://api.futunn.com/xxx/vote?stock_code=09880

# 资讯
https://api.futunn.com/xxx/news?stock_code=09880
```

---

## 方案B：使用mitmproxy（命令行）

### 1. 安装
```bash
pip install mitmproxy
```

### 2. 启动代理
```bash
# 启动Web界面版本
mitmweb -p 8080

# 打开浏览器访问 http://127.0.0.1:8081 查看请求
```

### 3. iPhone配置
同方案A的步骤3，但端口改为 `8080`，证书地址改为 `mitm.it`

### 4. 过滤富途请求
在mitmweb界面，过滤栏输入：`~d futunn.com`

---

## 方案C：使用Proxyman（Mac原生，最简单）

### 1. 安装
```bash
brew install --cask proxyman
```

### 2. 一键配置
Proxyman有自动配置功能：
1. 打开Proxyman
2. 菜单 → Certificate → Install Certificate on iOS → Automatic
3. 按提示操作即可

---

## 抓包后的分析

### 预期API结构
```json
// 评论列表 API 响应示例
{
  "code": 0,
  "data": {
    "list": [
      {
        "user_id": "123456",
        "nickname": "Jimibaby",
        "content": "春晚跟你没关系是吧？天天出货",
        "stock_code": "09880",
        "created_at": "2026-02-23 10:14:00",
        "likes": 0,
        "comments": 0
      }
    ],
    "total": 42000,
    "has_more": true
  }
}

// 猜涨跌 API 响应示例
{
  "code": 0,
  "data": {
    "stock_code": "09880",
    "up_ratio": 79,
    "down_ratio": 21,
    "vote_count": 1234
  }
}
```

### 提取API后的使用
```python
import requests

class FutuComments:
    def __init__(self):
        self.base_url = "https://api.futunn.com"  # 抓包后替换真实地址
        self.headers = {
            "User-Agent": "Futu/xxx",  # 抓包获取
            "Authorization": "Bearer xxx"  # 如果需要token
        }

    def get_comments(self, stock_code, page=1):
        """获取评论列表"""
        url = f"{self.base_url}/xxx/comments"
        params = {
            "stock_code": stock_code,
            "page": page,
            "page_size": 20
        }
        resp = requests.get(url, params=params, headers=self.headers)
        return resp.json()

    def get_vote(self, stock_code):
        """获取猜涨跌数据"""
        url = f"{self.base_url}/xxx/vote"
        params = {"stock_code": stock_code}
        resp = requests.get(url, params=params, headers=self.headers)
        return resp.json()

# 使用
futu = FutuComments()
comments = futu.get_comments("09880")
vote = futu.get_vote("09880")
```

---

## 常见问题

### Q: 抓不到HTTPS请求？
A: 需要安装并信任证书，iOS需要在"证书信任设置"中启用

### Q: 富途App检测到代理拒绝连接？
A: 某些App有反代理检测，可以尝试：
- 使用VPN模式的抓包工具（如Surge、Quantumult）
- 在模拟器中运行App

### Q: 请求需要登录Token？
A: 抓包时需要先登录App，然后从请求Header中提取Token

---

## 抓包成功后告诉我

抓到API后，把以下信息发给我：
1. API的完整URL
2. 请求Header（特别是Authorization）
3. 响应JSON结构

我会帮你写一个完整的富途评论/资讯获取模块。

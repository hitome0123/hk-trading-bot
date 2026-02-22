# 港股智能推荐系统 - n8n自动化配置

## 方案一：通过n8n UI导入（推荐）⭐

### 步骤：

1. **打开n8n控制台**
   ```
   浏览器访问: http://localhost:5678
   ```

2. **导入workflow**
   - 点击右上角 "+" 按钮
   - 选择 "Import from File"
   - 选择文件: `/tmp/hk_stock_workflow.json`
   - 点击 "Import"

3. **激活workflow**
   - 点击右上角的 "Inactive" 切换到 "Active"
   - workflow会每10分钟自动执行一次

4. **测试运行**
   - 点击 "Execute Workflow" 按钮手动测试
   - 查看执行结果

---

## 方案二：添加推送功能（可选）

如果你想把推荐信号推送到钉钉/Telegram，可以在workflow末尾添加：

### 钉钉推送节点

1. 在"过滤空消息"的True分支后添加 **HTTP Request** 节点
2. 配置：
   - Method: POST
   - URL: `你的钉钉Webhook地址`
   - Body:
   ```json
   {
     "msgtype": "text",
     "text": {
       "content": "{{ $json.message }}"
     }
   }
   ```

### Telegram推送节点

1. 添加 **Telegram** 节点
2. 配置：
   - Credential: 添加你的Bot Token
   - Chat ID: 你的Chat ID
   - Text: `{{ $json.message }}`

---

## workflow包含的节点

```
定时触发器 (每10分钟)
    ↓
执行推荐系统 (run_all_signals.sh)
    ↓
读取推荐结果 (final_messages.json)
    ↓
格式化消息 (解析JSON)
    ↓
过滤空消息
    ↓
[可选] 推送到钉钉/Telegram
```

---

## 停用cron任务（可选）

如果使用n8n后想停用cron，执行：

```bash
# 查看当前cron任务
crontab -l

# 编辑cron任务（注释掉港股推荐那一行）
crontab -e

# 或者完全移除
crontab -l | grep -v "run_all_signals.sh" | crontab -
```

---

## 监控和维护

### 查看执行历史
- n8n UI → Executions 标签
- 可以查看每次执行的详细日志

### 查看输出文件
```bash
# 查看最新推荐
cat /Users/mantou/.n8n-files/final_messages.json

# 查看综合信号
cat /Users/mantou/.n8n-files/integrated_signals.json
```

---

## 常见问题

**Q: workflow执行失败？**
A: 检查 `/Users/mantou/hk-trading-bot/run_all_signals.sh` 是否有执行权限：
```bash
chmod +x /Users/mantou/hk-trading-bot/run_all_signals.sh
```

**Q: 没有推荐信号？**
A: 正常情况下，只有高质量信号才会推送。可以查看 `integrated_signals.json` 看完整信号列表。

**Q: 想修改执行频率？**
A: 在"定时触发器"节点中修改 `minutesInterval` 参数（建议5-30分钟）

---

**创建时间**: 2026-02-03
**版本**: 1.0

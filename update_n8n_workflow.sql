-- 更新港股做T智能交易系统工作流
-- 添加实时信号推送功能

UPDATE workflow_entity
SET
  nodes = json('[
    {
      "parameters": {
        "rule": {
          "interval": [{"field": "minutes", "minutesInterval": 5}]
        }
      },
      "name": "每5分钟扫描",
      "type": "n8n-nodes-base.scheduleTrigger",
      "position": [250, 300],
      "id": "node1"
    },
    {
      "parameters": {
        "jsCode": "const { execSync } = require(''child_process'');\\n\\ntry {\\n  const raw = execSync(\\n    ''python3 /Users/mantou/hk-trading-bot/n8n_realtime_signal.py 2>/dev/null'',\\n    { timeout: 120000, encoding: ''utf-8'' }\\n  );\\n\\n  const data = JSON.parse(raw);\\n  return [{ json: data }];\\n\\n} catch(e) {\\n  return [{ json: { error: e.message, signals: [] } }];\\n}"
      },
      "name": "实时信号检测",
      "type": "n8n-nodes-base.code",
      "position": [450, 300],
      "id": "node2"
    },
    {
      "parameters": {
        "conditions": {
          "number": [
            {
              "value1": "={{ $json.buy_signals }}",
              "operation": "larger",
              "value2": 0
            }
          ]
        }
      },
      "name": "有买入信号？",
      "type": "n8n-nodes-base.if",
      "position": [650, 300],
      "id": "node3"
    },
    {
      "parameters": {
        "jsCode": "const data = $input.all()[0].json;\\nconst buySignals = data.signals.filter(s => s.signal.type === ''买入'');\\n\\nconst messages = buySignals.map(stock => {\\n  const signal = stock.signal;\\n  \\n  const emoji = signal.strength === ''强'' ? ''🔥'' : ''✅'';\\n  \\n  return `${emoji} ${signal.strength}买入信号\\n\\n📈 股票: ${stock.name} (${stock.code})\\n🏷️ 板块: ${stock.sector}\\n\\n💰 当前价: ${stock.price} HKD\\n📊 涨幅: ${stock.changePct > 0 ? ''+'' : ''''}${stock.changePct}%\\n\\n📉 RSI: ${signal.rsi} (超卖)\\n📏 位置: 布林带${signal.bollinger_position.toFixed(0)}%\\n🚀 量比: ${signal.vol_ratio}倍\\n\\n💡 建议操作:\\n  • 仓位: ${signal.suggested_position}\\n  • 买入: ${signal.entry_price}\\n  • 止损: ${signal.stop_loss}\\n  • 目标1: ${signal.target1} (日内)\\n  • 目标2: ${signal.target2} (激进)\\n\\n⏰ ${stock.timestamp}`;\\n});\\n\\nreturn messages.map(msg => ({ json: { message: msg } }));"
      },
      "name": "格式化推送消息",
      "type": "n8n-nodes-base.code",
      "position": [850, 200],
      "id": "node4"
    },
    {
      "parameters": {
        "url": "YOUR_WEBHOOK_URL",
        "method": "POST",
        "sendBody": true,
        "bodyParameters": {
          "msgtype": "text",
          "text": {
            "content": "={{ $json.message }}"
          }
        }
      },
      "name": "发送钉钉通知",
      "type": "n8n-nodes-base.httpRequest",
      "position": [1050, 200],
      "id": "node5"
    }
  ]'),
  connections = json('{
    "每5分钟扫描": {
      "main": [[{"node": "实时信号检测", "type": "main", "index": 0}]]
    },
    "实时信号检测": {
      "main": [[{"node": "有买入信号？", "type": "main", "index": 0}]]
    },
    "有买入信号？": {
      "main": [[{"node": "格式化推送消息", "type": "main", "index": 0}], []]
    },
    "格式化推送消息": {
      "main": [[{"node": "发送钉钉通知", "type": "main", "index": 0}]]
    }
  }'),
  active = 1
WHERE id = 'OjAShr4BbxlocAUf';

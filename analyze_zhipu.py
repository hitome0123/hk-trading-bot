#!/usr/bin/env python3
"""
专门分析智谱AI (2513.HK) 的脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.data_providers.yfinance_provider import YFinanceProvider
from hk_trading_bot.modules.indicators import TechnicalIndicators
from datetime import datetime
import numpy as np

def analyze_zhipu_ai():
    """专门分析智谱AI的详细信息"""
    ticker = "2513.HK"
    provider = YFinanceProvider()
    
    print(f"🧠 智谱AI (ZhipuAI) 深度分析")
    print(f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 1. 基本信息
    print(f"📊 获取股票基本信息...")
    stock_info = provider.get_stock_info(ticker)
    current_price = provider.get_current_price(ticker)
    
    print(f"📈 智谱AI股票信息:")
    print(f"   股票代码: {ticker}")
    print(f"   公司全名: {stock_info.get('longName', 'ZhipuAI Corporation')}")
    print(f"   简称: {stock_info.get('shortName', 'ZhipuAI')}")
    print(f"   交易所: {stock_info.get('exchange', 'HKEX')}")
    print(f"   币种: {stock_info.get('currency', 'HKD')}")
    
    # 2. 价格信息
    print(f"\n💰 价格表现:")
    print(f"   当前价格: {current_price:.2f} HKD")
    print(f"   发行价: 116.2 HKD (IPO价格)")
    
    if current_price > 0:
        ipo_return = ((current_price - 116.2) / 116.2) * 100
        print(f"   IPO至今回报: {ipo_return:+.1f}%")
        
        if ipo_return > 0:
            print(f"   🎉 表现: 高于发行价")
        else:
            print(f"   📉 表现: 低于发行价")
    
    print(f"   昨收: {stock_info.get('previous_close', 'N/A')}")
    print(f"   日高: {stock_info.get('day_high', 'N/A')}")
    print(f"   日低: {stock_info.get('day_low', 'N/A')}")
    print(f"   52周高: {stock_info.get('fifty_two_week_high', 'N/A')}")
    print(f"   52周低: {stock_info.get('fifty_two_week_low', 'N/A')}")
    print(f"   成交量: {stock_info.get('volume', 'N/A')}")
    
    # 3. 公司基本面信息
    print(f"\n🏢 公司基本面 (基于公开资料):")
    print(f"   📈 业务: AI大模型开发和服务")
    print(f"   🏆 地位: 全球大模型第一股")
    print(f"   💰 IPO募资: 43.5亿港元")
    print(f"   🏷️ IPO估值: ~511亿港元")
    print(f"   📊 市场份额: 中国独立通用大模型开发商第1位")
    
    # 4. 财务表现
    print(f"\n📊 财务表现 (2024年数据):")
    print(f"   💵 2024年收入: 3.124亿元 (同比+151%)")
    print(f"   📈 2025H1收入: 1.91亿元 (同比+325%)")
    print(f"   📉 2024年净亏损: 29.58亿元")
    print(f"   🔥 收入增长率: 年复合130%")
    print(f"   💡 商业模式: MaaS平台 + B端解决方案")
    
    # 5. 技术指标（如果有历史数据）
    print(f"\n📈 技术分析:")
    price_data = provider.get_price_data(ticker, 30)
    
    if price_data and len(price_data.get('close', [])) > 5:
        indicators_calc = TechnicalIndicators()
        indicators = indicators_calc.calculate_all_indicators(price_data)
        
        print(f"   历史数据: {len(price_data['close'])} 天")
        for name, value in indicators.items():
            if not np.isnan(value):
                print(f"   {name.upper()}: {value:.2f}")
    else:
        print(f"   ⚠️ 上市时间较短，技术指标数据有限")
    
    # 6. 投资亮点与风险
    print(f"\n💡 投资亮点:")
    print(f"   ✅ 全球首家上市的大模型公司")
    print(f"   ✅ 中国大模型市场领导者")
    print(f"   ✅ 收入快速增长 (年复合130%)")
    print(f"   ✅ 头部机构投资背景 (腾讯、阿里、美团等)")
    print(f"   ✅ GLM系列模型技术领先")
    print(f"   ✅ 完整的AI产业链布局")
    
    print(f"\n⚠️ 投资风险:")
    print(f"   🔸 目前仍在亏损阶段 (2024年亏损30亿元)")
    print(f"   🔸 AI行业竞争激烈")
    print(f"   🔸 新股波动性较大")
    print(f"   🔸 监管政策风险")
    print(f"   🔸 技术迭代风险")
    print(f"   🔸 估值较高 (511亿港元)")
    
    # 7. 投资建议
    print(f"\n🎯 投资建议:")
    
    if current_price > 0:
        # 基于价格表现给出建议
        if ipo_return > 20:
            print(f"   📈 短期建议: 谨慎追高，等待回调")
            print(f"   💰 建议价位: 120-130 HKD区间")
        elif ipo_return > 0:
            print(f"   📊 短期建议: 可考虑适量配置")
            print(f"   💰 建议价位: 当前价位附近")
        else:
            print(f"   📉 短期建议: 关注反弹机会")
            print(f"   💰 建议价位: 110-120 HKD区间")
    
    print(f"\n   🔮 长期观点: 看好AI行业发展")
    print(f"   💼 适合投资者: 科技股投资者，能承受高波动")
    print(f"   📊 建议仓位: 不超过组合5-10%")
    print(f"   ⏰ 关注时机: 业绩公布期、AI政策变化")
    
    # 8. 对比分析
    print(f"\n🏆 行业对比:")
    print(f"   vs ChatGPT母公司: 估值相对合理")
    print(f"   vs 国内AI概念股: 纯正AI标的")
    print(f"   vs 传统科技股: 成长性更强但风险更高")
    
    print(f"\n🌟 总结:")
    print(f"智谱AI作为全球首家上市的大模型公司，具有稀缺性价值。")
    print(f"公司在中国市场具有领先地位，收入增长迅速，但目前仍处于")
    print(f"投入期，短期盈利压力较大。适合看好AI长期发展的投资者配置。")

if __name__ == "__main__":
    analyze_zhipu_ai()
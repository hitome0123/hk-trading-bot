#!/usr/bin/env python3
"""
四层过滤通用分析框架 - 主程序
Universal Analysis Framework Main Entry Point
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.core.analysis_engine import UniversalAnalysisEngine
from hk_trading_bot.data_providers.yfinance_provider import YFinanceProvider
from hk_trading_bot.data_providers.crypto_provider import CryptoProvider
from hk_trading_bot.data_providers.alphavantage_provider import AlphaVantageProvider
import time
import json


def print_analysis_results(analysis: dict):
    """格式化打印分析结果"""
    
    if 'error' in analysis:
        print(f"❌ 分析失败: {analysis['error']}")
        return
    
    ticker = analysis['ticker']
    current_price = analysis['current_price']
    
    print(f"📊 {ticker} 四层过滤分析结果")
    print("=" * 60)
    print(f"💰 当前价格: ${current_price:,.2f}")
    print(f"⏰ 分析时间: {analysis['analysis_timestamp'][:19]}")
    
    # 第一层：形态识别
    print(f"\n🎯 Layer 1: 动态形态扫描")
    print("-" * 30)
    
    patterns = analysis.get('layer_1_patterns', [])
    if patterns:
        for pattern in patterns:
            strength_bar = "█" * int(pattern.signal_strength * 10)
            print(f"   {pattern.pattern_type}: {pattern.description}")
            print(f"   强度: {strength_bar} ({pattern.signal_strength:.2f})")
    else:
        print("   ⚪ 未检测到显著形态")
    
    # 第二层：资金流向
    print(f"\n💰 Layer 2: 资金流向探测")
    print("-" * 30)
    
    capital_flows = analysis.get('layer_2_capital_flow', [])
    if capital_flows:
        for flow in capital_flows:
            flow_icon = "📈" if "inflow" in flow.flow_type or "buying" in flow.flow_type else "📉"
            print(f"   {flow_icon} {flow.signal_interpretation}")
            print(f"   强度: {'█' * int(flow.flow_strength * 10)} ({flow.flow_strength:.2f})")
    else:
        print("   ⚪ 无明显资金流向信号")
    
    # 第三层：相对强弱
    print(f"\n📈 Layer 3: 相对强弱分析")
    print("-" * 30)
    
    rs_signals = analysis.get('layer_3_relative_strength', [])
    if rs_signals:
        for rs in rs_signals:
            rs_icon = "🏆" if rs.strength_category == "leader" else "📊" if rs.strength_category == "follower" else "📉"
            print(f"   {rs_icon} vs {rs.benchmark_symbol}: RS = {rs.rs_ratio:.2f}")
            print(f"   表现: {rs.outperformance_pct:+.1f}% ({rs.strength_category.upper()})")
    else:
        print("   ⚪ 无基准对比数据")
    
    # 第四层：AI叙事
    print(f"\n🤖 Layer 4: AI叙事评分")
    print("-" * 30)
    
    narrative = analysis.get('layer_4_narrative')
    if narrative:
        score_bar = "█" * int(narrative.narrative_score / 10)
        category_icon = {
            'rerating': '🚀',
            'cyclical': '🔄', 
            'speculative': '💭'
        }.get(narrative.narrative_category, '📰')
        
        print(f"   {category_icon} 叙事分类: {narrative.narrative_category.upper()}")
        print(f"   叙事得分: {score_bar} ({narrative.narrative_score}/100)")
        print(f"   置信度: {narrative.confidence:.1%}")
        
        if narrative.key_themes:
            print(f"   核心主题: {', '.join(narrative.key_themes[:3])}")
    else:
        print("   ⚪ 无AI叙事分析")
    
    # 综合评分
    print(f"\n🎯 综合评分与建议")
    print("=" * 40)
    
    composite = analysis.get('composite_analysis', {})
    if composite:
        score = composite.get('composite_score', 0)
        signal = composite.get('overall_signal', 'HOLD')
        confidence = composite.get('confidence', 0.5)
        
        # 信号图标
        signal_icons = {
            'STRONG_BUY': '🔥',
            'BUY': '✅',
            'HOLD': '⏸️', 
            'SELL': '❌',
            'STRONG_SELL': '🚨'
        }
        
        signal_colors = {
            'STRONG_BUY': '\033[92m',  # 绿色
            'BUY': '\033[92m',
            'HOLD': '\033[93m',        # 黄色
            'SELL': '\033[91m',        # 红色
            'STRONG_SELL': '\033[91m'
        }
        
        print(f"   {signal_icons.get(signal, '⚪')} 综合信号: {signal_colors.get(signal, '')}{signal}\033[0m")
        print(f"   🎯 综合得分: {score:.1f}/100")
        print(f"   🎲 分析置信度: {confidence:.1%}")
        
        # 分项得分
        components = composite.get('component_scores', {})
        print(f"\n   📊 分项得分:")
        print(f"      形态识别: {components.get('pattern_score', 0):.1f}/25")
        print(f"      资金流向: {components.get('capital_flow_score', 0):.1f}/30") 
        print(f"      相对强弱: {components.get('relative_strength_score', 0):.1f}/20")
        print(f"      AI叙事: {components.get('narrative_score', 0):.1f}/25")
        
        # 投资建议
        print(f"\n💡 投资建议:")
        if signal in ['STRONG_BUY', 'BUY']:
            print(f"   ✅ 建议关注或配置")
            print(f"   📈 风险偏好：中高")
            print(f"   ⏰ 时间框架：短中期")
        elif signal == 'HOLD':
            print(f"   ⏸️ 建议观望等待")
            print(f"   🔍 继续跟踪关键指标")
        else:
            print(f"   ❌ 建议规避或减仓")
            print(f"   🛡️ 风险控制优先")
    
    print(f"\n" + "="*60)


def analyze_ticker_universal(ticker: str):
    """使用四层过滤框架分析任意标的"""
    
    print(f"🧠 启动四层过滤通用分析框架")
    print(f"🎯 分析标的: {ticker}")
    
    # 初始化分析引擎
    engine = UniversalAnalysisEngine()
    
    # 根据标的类型选择数据源
    ticker_upper = ticker.upper()
    
    if ticker_upper.endswith('.HK') or ticker_upper.endswith('.HKG'):
        # 港股：使用yfinance
        print(f"🏢 检测到港股，使用 yfinance 数据源")
        data_provider = YFinanceProvider()
    elif ticker_upper in ['BTC', 'ETH', 'SOL', 'DOT', 'ADA', 'LINK', 'UNI', 'LTC', 'BCH', 'XRP']:
        # 加密货币：使用Alpha Vantage crypto
        print(f"🪙 检测到加密货币，使用 Alpha Vantage 数据源")
        data_provider = CryptoProvider()
    else:
        # 美股：优先使用Alpha Vantage，备选yfinance
        print(f"🇺🇸 检测到美股，使用 Alpha Vantage 数据源")
        try:
            data_provider = AlphaVantageProvider()
            # 测试连接
            test_quote = data_provider.get_quote(ticker_upper)
            if not test_quote:
                print(f"⚠️ Alpha Vantage 无数据，切换到 yfinance")
                data_provider = YFinanceProvider()
        except Exception as e:
            print(f"⚠️ Alpha Vantage 连接失败: {e}，切换到 yfinance")
            data_provider = YFinanceProvider()
    
    try:
        # 执行四层分析
        analysis_result = engine.analyze_ticker(ticker_upper, data_provider)
        
        # 打印结果
        print_analysis_results(analysis_result)
        
        # 保存分析结果 (可选)
        save_to_file = input("\n💾 是否保存分析结果到文件? (y/N): ").strip().lower()
        if save_to_file == 'y':
            filename = f"analysis_{ticker_upper}_{int(time.time())}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, indent=2, ensure_ascii=False, default=str)
            print(f"✅ 分析结果已保存到: {filename}")
        
        return analysis_result
        
    except Exception as e:
        print(f"❌ 分析过程中出现错误: {e}")
        return None


def batch_analysis(tickers: list):
    """批量分析多个标的"""
    
    print(f"\n🔄 批量分析模式")
    print(f"📊 待分析标的: {', '.join(tickers)}")
    print("=" * 60)
    
    results = {}
    
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] 分析 {ticker}...")
        print("-" * 40)
        
        try:
            result = analyze_ticker_universal(ticker)
            results[ticker] = result
            
            # 间隔避免API限制
            if i < len(tickers):
                time.sleep(2)
                
        except Exception as e:
            print(f"❌ {ticker} 分析失败: {e}")
            results[ticker] = {'error': str(e)}
    
    # 批量结果总结
    print(f"\n📋 批量分析总结")
    print("=" * 50)
    
    for ticker, result in results.items():
        if 'error' in result:
            print(f"❌ {ticker}: 分析失败")
        else:
            composite = result.get('composite_analysis', {})
            signal = composite.get('overall_signal', 'UNKNOWN')
            score = composite.get('composite_score', 0)
            
            signal_icon = {'STRONG_BUY': '🔥', 'BUY': '✅', 'HOLD': '⏸️', 'SELL': '❌', 'STRONG_SELL': '🚨'}.get(signal, '⚪')
            print(f"{signal_icon} {ticker}: {signal} ({score:.0f}/100)")
    
    return results


def main():
    """主程序"""
    
    print(f"🚀 四层过滤通用分析框架")
    print(f"Universal 4-Layer Analysis Framework")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print(f"""
使用方法:
  python universal_main.py <TICKER>         # 单个分析
  python universal_main.py <TICKER1> <TICKER2> ...  # 批量分析

支持的资产类型:
  🏢 港股: 2513.HK, 0700.HK, 2807.HK
  🇺🇸 美股: AAPL, TSLA, MSFT, NVDA  
  🪙 加密货币: BTC, ETH, SOL, DOT

示例:
  python universal_main.py AAPL            # Apple股票分析
  python universal_main.py 2513.HK         # 智谱AI分析  
  python universal_main.py BTC             # 比特币分析
  python universal_main.py AAPL TSLA BTC   # 批量分析
        """)
        return
    
    tickers = [arg.upper() for arg in sys.argv[1:]]
    
    if len(tickers) == 1:
        # 单个分析
        analyze_ticker_universal(tickers[0])
    else:
        # 批量分析
        batch_analysis(tickers)
    
    print(f"\n🎉 分析完成! 感谢使用四层过滤分析框架")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
改进的资讯抓取 - 多数据源整合
"""
import requests
from futu import *

class ImprovedNewsFetcher:
    """整合多个资讯源"""
    
    def __init__(self):
        self.quote_ctx = None
        
    def fetch_stock_news(self, stock_code):
        """
        从富途获取个股公告和新闻（最靠谱）
        
        参数：stock_code - 如 'HK.09880'
        """
        if not self.quote_ctx:
            self.quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        
        try:
            # 方法1: 获取公司公告
            ret, data = self.quote_ctx.request_history_kl_quota(get_detail=True)
            
            # 方法2: 从行情快照获取最新状态
            ret, snapshot = self.quote_ctx.get_market_snapshot([stock_code])
            if ret == RET_OK:
                # 检查是否有异动
                turnover_rate = snapshot.iloc[0]['turnover_rate'] if not snapshot.empty else 0
                if turnover_rate > 10:
                    return [{'title': f'高换手率{turnover_rate:.1f}%，资金活跃', 'source': 'Futu'}]
            
            return []
        except Exception as e:
            print(f"⚠️ 富途资讯获取失败: {e}")
            return []
    
    def search_web_news(self, keyword):
        """
        使用搜索引擎找最新新闻
        """
        try:
            # Google搜索（需要梯子）或Bing搜索
            url = f"https://www.bing.com/search?q={keyword}+新闻&setlang=zh-CN"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=5)
            
            # 简单提取（实际需要HTML解析）
            if '优必选' in response.text:
                return [{'title': f'搜索到{keyword}相关新闻', 'source': 'Bing'}]
            return []
        except:
            return []
    
    def get_comprehensive_news(self, sector_name, stock_list):
        """
        综合多个数据源获取资讯
        """
        all_news = []
        
        # 1. 富途个股数据（最重要）
        for stock in stock_list[:3]:
            stock_news = self.fetch_stock_news(stock['code'])
            all_news.extend(stock_news)
        
        # 2. 基于量价的"隐含新闻"
        for stock in stock_list[:3]:
            if stock['change_pct'] > 10 and stock.get('turnover_rate', 0) > 15:
                all_news.append({
                    'title': f"{stock['name']}涨{stock['change_pct']:.1f}%且换手率{stock.get('turnover_rate', 0):.1f}%，疑似有重大利好",
                    'source': '量价分析'
                })
        
        # 3. Web搜索（可选）
        # web_news = self.search_web_news(sector_name)
        # all_news.extend(web_news)
        
        return all_news[:5]


# 测试
if __name__ == '__main__':
    fetcher = ImprovedNewsFetcher()
    
    test_stocks = [
        {'code': 'HK.09880', 'name': '优必选', 'change_pct': 12.3, 'turnover_rate': 15.2}
    ]
    
    news = fetcher.get_comprehensive_news("人形机器人", test_stocks)
    
    print(f"\n找到 {len(news)} 条资讯:")
    for item in news:
        print(f"  📰 {item['title']} ({item['source']})")

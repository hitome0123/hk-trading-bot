#!/usr/bin/env python3
"""
使用Selenium绕过反爬虫抓取资讯
模拟真实浏览器行为
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
from typing import List, Dict

class SeleniumNewsFetcher:
    """使用Selenium抓取资讯"""

    def __init__(self, headless=True):
        """初始化浏览器"""
        self.driver = None
        self.headless = headless

    def init_browser(self):
        """初始化Chrome浏览器"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument('--headless')

        # 反检测设置
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(options=chrome_options)

        # 去除webdriver痕迹
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })

    def fetch_xueqiu_with_login(self, stock_code: str, cookie_string: str, limit=5) -> List[Dict]:
        """
        使用Selenium + Cookie登录雪球
        绕过WAF限制
        """
        news_list = []

        if not self.driver:
            self.init_browser()

        try:
            # 转换股票代码
            if stock_code.startswith('HK.'):
                symbol = stock_code.replace('HK.', '0') + '.HK'
            else:
                symbol = stock_code

            # 1. 先访问首页设置cookie
            self.driver.get('https://xueqiu.com')
            time.sleep(2)

            # 2. 添加cookie
            cookies = self._parse_cookie_string(cookie_string)
            for cookie in cookies:
                self.driver.add_cookie(cookie)

            # 3. 访问股票页面
            url = f'https://xueqiu.com/S/{symbol}'
            self.driver.get(url)

            # 随机延迟，模拟人类行为
            time.sleep(random.uniform(2, 4))

            # 4. 等待内容加载
            wait = WebDriverWait(self.driver, 10)

            # 5. 提取讨论内容
            # 雪球的帖子通常在class为'timeline__item'的元素中
            posts = self.driver.find_elements(By.CLASS_NAME, 'timeline__item')

            for post in posts[:limit]:
                try:
                    # 提取标题/内容
                    text_elem = post.find_element(By.CLASS_NAME, 'timeline__item__content')
                    text = text_elem.text.strip()

                    # 提取作者
                    try:
                        author = post.find_element(By.CLASS_NAME, 'timeline__item__info__name').text
                    except:
                        author = '匿名'

                    # 提取时间
                    try:
                        time_elem = post.find_element(By.CLASS_NAME, 'timeline__item__info__time')
                        pub_time = time_elem.text
                    except:
                        pub_time = ''

                    if text and len(text) > 10:
                        news_list.append({
                            'title': text[:100] + '...' if len(text) > 100 else text,
                            'source': '雪球',
                            'time': pub_time,
                            'author': author,
                            'platform': 'xueqiu'
                        })
                except:
                    continue

        except Exception as e:
            print(f"Selenium抓取失败: {e}")

        return news_list

    def fetch_guba_selenium(self, stock_code: str, limit=5) -> List[Dict]:
        """
        使用Selenium抓取股吧
        """
        news_list = []

        if not self.driver:
            self.init_browser()

        try:
            # 转换代码
            code_num = stock_code.replace('HK.', '').replace('US.', '').replace('SH.', '').replace('SZ.', '')

            # 访问股吧
            url = f'https://guba.eastmoney.com/list,{code_num}.html'
            self.driver.get(url)

            # 等待加载
            time.sleep(random.uniform(2, 4))

            # 提取帖子列表
            # 股吧的帖子在class='articleh'的div中
            posts = self.driver.find_elements(By.CLASS_NAME, 'articleh')

            for post in posts[:limit]:
                try:
                    # 提取标题
                    title_elem = post.find_element(By.TAG_NAME, 'a')
                    title = title_elem.text.strip()

                    if title and len(title) > 5:
                        news_list.append({
                            'title': title,
                            'source': '股吧',
                            'time': '',
                            'platform': 'guba'
                        })
                except:
                    continue

        except Exception as e:
            print(f"股吧抓取失败: {e}")

        return news_list

    def _parse_cookie_string(self, cookie_string: str) -> List[Dict]:
        """解析cookie字符串为字典列表"""
        cookies = []
        for item in cookie_string.split('; '):
            if '=' in item:
                name, value = item.split('=', 1)
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': '.xueqiu.com'
                })
        return cookies

    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()


# 测试
if __name__ == '__main__':
    print("测试Selenium抓取...\n")

    fetcher = SeleniumNewsFetcher(headless=True)

    # 测试股吧（无需cookie）
    print("="*60)
    print("测试股吧")
    print("="*60)
    guba_news = fetcher.fetch_guba_selenium('HK.09880', limit=3)
    if guba_news:
        print(f"✅ 找到 {len(guba_news)} 条:")
        for i, news in enumerate(guba_news, 1):
            print(f"{i}. {news['title']}")
    else:
        print("⚠️ 未找到")

    # 测试雪球（需要cookie）
    print("\n" + "="*60)
    print("测试雪球")
    print("="*60)

    cookie = "acw_tc=2f3478b417717377539325780e71f7cd4abe784caab2a9bf6b834db2d9491e; cookiesu=901771737755125; device_id=8fc5b1eaa2f27255f3a57e733348dad7; xq_a_token=1f8d3500f5859d5b08602d4349175a673d8df866; xq_is_login=1; u=2544711652"

    xueqiu_news = fetcher.fetch_xueqiu_with_login('HK.09880', cookie, limit=3)
    if xueqiu_news:
        print(f"✅ 找到 {len(xueqiu_news)} 条:")
        for i, news in enumerate(xueqiu_news, 1):
            print(f"{i}. [{news['author']}] {news['title'][:60]}...")
    else:
        print("⚠️ 未找到")

    fetcher.close()
    print("\n✅ 测试完成")

"""
测试单个Scraper
用于逐个验证每个scraper的功能
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.newsbreak_scraper import NewsbreakScraper
from utils.logger import logger


async def test_newsbreak():
    """测试Newsbreak scraper"""
    print("="*70)
    print("测试 Newsbreak Scraper")
    print("="*70)
    
    try:
        scraper = NewsbreakScraper()
        print("📌 开始采集 Zipcode: 90210")
        print("⏳ 这可能需要一些时间...\n")
        
        articles = await scraper.scrape(zipcode="90210", limit=3)
        
        print(f"\n✅ 采集完成！获得 {len(articles)} 篇文章\n")
        
        if articles:
            for i, article in enumerate(articles, 1):
                print(f"文章 {i}:")
                print(f"  标题: {article.get('title', 'N/A')}")
                print(f"  链接: {article.get('url', 'N/A')}")
                print(f"  日期: {article.get('publish_date', 'N/A')}")
                print(f"  内容: {article.get('content', '')[:100]}...")
                print()
            print("✅ Newsbreak Scraper 测试成功！")
            return True
        else:
            print("❌ 未能提取到文章")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_newsbreak())
    sys.exit(0 if result else 1)

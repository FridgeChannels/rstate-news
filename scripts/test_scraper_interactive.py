"""
交互式Scraper测试工具
逐个测试每个scraper，验证元素提取
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.newsbreak_scraper import NewsbreakScraper
from scrapers.patch_scraper import PatchScraper
from scrapers.realtor_scraper import RealtorScraper
from scrapers.redfin_scraper import RedfinScraper
from scrapers.nar_scraper import NARScraper
from scrapers.freddiemac_scraper import FreddieMacScraper
from utils.logger import logger


async def test_scraper(scraper_class, name: str, zipcode: str = None):
    """测试单个scraper"""
    print(f"\n{'='*70}")
    print(f"测试: {name}")
    print(f"{'='*70}\n")
    
    try:
        scraper = scraper_class()
        
        if zipcode:
            print(f"📌 使用Zipcode: {zipcode}")
            articles = await scraper.scrape(zipcode=zipcode, limit=5)
        else:
            print("📌 采集房地产新闻")
            articles = await scraper.scrape(limit=5)
        
        print(f"\n✅ 采集结果: {len(articles)} 篇文章\n")
        
        for i, article in enumerate(articles[:3], 1):
            print(f"文章 {i}:")
            print(f"  标题: {article.get('title', 'N/A')[:60]}...")
            print(f"  链接: {article.get('url', 'N/A')[:60]}...")
            print(f"  日期: {article.get('publish_date', 'N/A')}")
            print(f"  内容: {article.get('content', article.get('content_summary', 'N/A'))[:60]}...")
            print()
        
        if len(articles) > 0:
            print(f"✅ {name} 测试成功！能提取到 {len(articles)} 篇文章")
            return True
        else:
            print(f"❌ {name} 测试失败：未能提取到文章")
            return False
            
    except Exception as e:
        print(f"❌ {name} 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("="*70)
    print("交互式Scraper测试工具")
    print("="*70)
    
    test_cases = [
        (NewsbreakScraper, "Newsbreak", "90210"),
        (PatchScraper, "Patch", "90210"),
        (RealtorScraper, "Realtor.com", None),
        (RedfinScraper, "Redfin", None),
        (NARScraper, "NAR", None),
        (FreddieMacScraper, "Freddie Mac", None),
    ]
    
    results = {}
    
    for scraper_class, name, zipcode in test_cases:
        success = await test_scraper(scraper_class, name, zipcode)
        results[name] = success
        await asyncio.sleep(3)  # 网站之间延迟
    
    print("\n" + "="*70)
    print("测试总结:")
    print("="*70)
    for name, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {name}: {status}")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())

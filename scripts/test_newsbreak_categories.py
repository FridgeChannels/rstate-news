"""
测试Newsbreak分类采集功能（跳过zipcode选择，直接测试分类）
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.newsbreak_scraper import NewsbreakScraper
from utils.logger import logger


async def test_categories_directly():
    """直接测试分类采集（假设城市URL已知）"""
    print("\n" + "=" * 70)
    print("Newsbreak 分类采集功能测试（直接测试）")
    print("=" * 70)
    
    scraper = NewsbreakScraper()
    await scraper._setup_browser(headless=True)
    page = await scraper._create_page()
    
    # 直接使用已知的城市URL（Beverly Hills, CA）
    city_url = "/beverly-hills-ca"
    zipcode = "90210"
    
    print(f"\n测试城市: {city_url}")
    print(f"Zipcode: {zipcode}")
    
    try:
        # 测试三个分类
        categories = ['business', 'education', 'poi_housing']
        all_articles = []
        
        for category in categories:
            print(f"\n测试分类: {category}")
            try:
                articles = await scraper._scrape_category(page, city_url, category, zipcode, limit=5)
                print(f"  ✅ 成功: {len(articles)} 篇文章")
                if articles:
                    print(f"  示例: {articles[0].get('title', 'N/A')[:60]}")
                all_articles.extend(articles)
            except Exception as e:
                print(f"  ❌ 失败: {str(e)[:100]}")
                import traceback
                traceback.print_exc()
        
        print(f"\n总共采集: {len(all_articles)} 篇文章")
        
        # 测试去重
        print("\n测试去重功能...")
        deduplicated = scraper._deduplicate_articles(all_articles)
        print(f"去重前: {len(all_articles)} 篇")
        print(f"去重后: {len(deduplicated)} 篇")
        
        # 测试24小时过滤
        print("\n测试24小时过滤...")
        filtered = scraper._filter_24_hours(deduplicated)
        print(f"过滤前: {len(deduplicated)} 篇")
        print(f"过滤后: {len(filtered)} 篇")
        
        # 显示示例
        if filtered:
            print(f"\n示例文章（前3篇）:")
            for i, article in enumerate(filtered[:3], 1):
                print(f"  {i}. {article.get('title', 'N/A')[:60]}")
                print(f"     URL: {article.get('url', 'N/A')[:60]}")
                print(f"     日期: {article.get('publish_date', 'N/A')}")
        
        return {
            'success': True,
            'total': len(all_articles),
            'deduplicated': len(deduplicated),
            'filtered': len(filtered)
        }
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}
    finally:
        await scraper.cleanup()


async def main():
    """主函数"""
    result = await test_categories_directly()
    
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    
    if result.get('success'):
        print("✅ 分类采集功能测试通过")
        print(f"   - 总文章数: {result.get('total', 0)}")
        print(f"   - 去重后: {result.get('deduplicated', 0)}")
        print(f"   - 24小时过滤后: {result.get('filtered', 0)}")
    else:
        print("❌ 分类采集功能测试失败")
        print(f"   错误: {result.get('error', 'Unknown')[:200]}")
    
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

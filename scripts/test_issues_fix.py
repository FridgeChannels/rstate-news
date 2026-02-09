"""
测试Issue修复和功能改进
验证Patch和Newsbreak的修复是否正常工作
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.patch_scraper import PatchScraper
from scrapers.newsbreak_scraper import NewsbreakScraper
from utils.logger import logger


async def test_patch_scraper():
    """测试Patch scraper的修复"""
    print("\n" + "=" * 70)
    print("测试 Patch Scraper 修复")
    print("=" * 70)
    
    scraper = PatchScraper()
    test_zipcodes = ['90210', '10001', '94102', '60601']
    results = {}
    
    for zipcode in test_zipcodes:
        print(f"\n测试 Zipcode: {zipcode}")
        try:
            articles = await scraper.scrape(zipcode=zipcode, limit=5)
            results[zipcode] = {
                'success': True,
                'count': len(articles),
                'articles': articles[:3] if articles else []  # 只保存前3篇用于检查
            }
            print(f"  ✅ 成功: 采集到 {len(articles)} 篇文章")
            if articles:
                print(f"  示例文章标题: {articles[0].get('title', 'N/A')[:60]}")
        except Exception as e:
            results[zipcode] = {
                'success': False,
                'error': str(e),
                'count': 0
            }
            print(f"  ❌ 失败: {str(e)[:100]}")
    
    print("\n" + "=" * 70)
    print("Patch Scraper 测试结果汇总")
    print("=" * 70)
    success_count = sum(1 for r in results.values() if r.get('success') and r.get('count', 0) > 0)
    print(f"成功采集的zipcode: {success_count}/{len(test_zipcodes)}")
    for zipcode, result in results.items():
        status = "✅" if result.get('success') and result.get('count', 0) > 0 else "❌"
        count = result.get('count', 0)
        print(f"  {status} {zipcode}: {count} 篇文章")
        if not result.get('success'):
            print(f"    错误: {result.get('error', 'Unknown')[:80]}")
    
    return results


async def test_newsbreak_scraper():
    """测试Newsbreak scraper的新流程"""
    print("\n" + "=" * 70)
    print("测试 Newsbreak Scraper 新流程")
    print("=" * 70)
    
    scraper = NewsbreakScraper()
    test_zipcode = '90210'  # 使用一个zipcode进行测试
    
    print(f"\n测试 Zipcode: {test_zipcode}")
    print("验证流程: locations页面选择 → 三个分类并行采集 → 去重 → 24小时过滤")
    
    try:
        articles = await scraper.scrape(zipcode=test_zipcode, limit=10)
        
        print(f"\n✅ 采集完成: 共 {len(articles)} 篇文章")
        
        # 验证去重（检查URL是否唯一）
        urls = [a.get('url', '') for a in articles]
        unique_urls = set(urls)
        if len(urls) == len(unique_urls):
            print("  ✅ 去重验证通过: 所有URL都是唯一的")
        else:
            print(f"  ⚠️  去重验证失败: 有 {len(urls) - len(unique_urls)} 个重复URL")
        
        # 验证24小时过滤（检查日期）
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        
        old_articles = []
        for article in articles:
            publish_date_str = article.get('publish_date')
            if publish_date_str:
                try:
                    from dateutil import parser
                    pub_date = parser.parse(publish_date_str)
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                    if pub_date < cutoff:
                        old_articles.append(article)
                except Exception:
                    pass
        
        if not old_articles:
            print("  ✅ 24小时过滤验证通过: 所有文章都在24小时内")
        else:
            print(f"  ⚠️  24小时过滤验证失败: 有 {len(old_articles)} 篇文章超过24小时")
        
        # 显示示例文章
        if articles:
            print(f"\n示例文章（前3篇）:")
            for i, article in enumerate(articles[:3], 1):
                print(f"  {i}. {article.get('title', 'N/A')[:60]}")
                print(f"     URL: {article.get('url', 'N/A')[:60]}")
                print(f"     日期: {article.get('publish_date', 'N/A')}")
        
        return {
            'success': True,
            'count': len(articles),
            'articles': articles[:3]
        }
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'count': 0
        }


async def main():
    """主测试函数"""
    print("\n" + "=" * 70)
    print("Issue修复和功能改进验证测试")
    print("=" * 70)
    
    # 测试Patch
    patch_results = await test_patch_scraper()
    
    # 测试Newsbreak
    newsbreak_results = await test_newsbreak_scraper()
    
    # 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    
    patch_success = sum(1 for r in patch_results.values() if r.get('success') and r.get('count', 0) > 0)
    patch_total = len(patch_results)
    print(f"Patch Scraper: {patch_success}/{patch_total} 个zipcode成功采集")
    
    newsbreak_success = "✅" if newsbreak_results.get('success') and newsbreak_results.get('count', 0) > 0 else "❌"
    newsbreak_count = newsbreak_results.get('count', 0)
    print(f"Newsbreak Scraper: {newsbreak_success} 采集到 {newsbreak_count} 篇文章")
    
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

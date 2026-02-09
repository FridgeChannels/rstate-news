"""
测试Newsbreak完整流程
验证：zipcode选择 → 三个分类并行采集 → 去重 → 24小时过滤
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.newsbreak_scraper import NewsbreakScraper
from utils.logger import logger


async def test_newsbreak_full_flow():
    """测试Newsbreak完整流程"""
    print("\n" + "=" * 70)
    print("Newsbreak 完整流程测试")
    print("=" * 70)
    
    scraper = NewsbreakScraper()
    test_zipcode = '90210'  # Beverly Hills
    
    print(f"\n测试 Zipcode: {test_zipcode}")
    print("预期流程:")
    print("  1. 访问 https://www.newsbreak.com/locations")
    print("  2. 输入zipcode并选择城市")
    print("  3. 并行采集三个分类: business, education, poi_housing")
    print("  4. 合并结果并去重")
    print("  5. 过滤24小时内的文章")
    
    try:
        articles = await scraper.scrape(zipcode=test_zipcode, limit=20)
        
        print(f"\n" + "=" * 70)
        print("测试结果")
        print("=" * 70)
        print(f"✅ 采集完成: 共 {len(articles)} 篇文章")
        
        if len(articles) == 0:
            print("\n⚠️  警告: 未采集到任何文章")
            print("可能原因:")
            print("  - zipcode选择失败")
            print("  - 分类页面没有内容")
            print("  - 所有文章都超过24小时")
            return
        
        # 验证1: 检查URL去重
        print("\n验证1: URL去重检查")
        urls = [a.get('url', '') for a in articles if a.get('url')]
        unique_urls = set(urls)
        if len(urls) == len(unique_urls):
            print(f"  ✅ 通过: {len(urls)} 个URL都是唯一的")
        else:
            duplicates = len(urls) - len(unique_urls)
            print(f"  ❌ 失败: 发现 {duplicates} 个重复URL")
            # 找出重复的URL
            from collections import Counter
            url_counts = Counter(urls)
            duplicates_list = [url for url, count in url_counts.items() if count > 1]
            print(f"  重复URL示例: {duplicates_list[:3]}")
        
        # 验证2: 24小时过滤检查
        print("\n验证2: 24小时过滤检查")
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
                        old_articles.append({
                            'title': article.get('title', '')[:50],
                            'date': publish_date_str,
                            'hours_ago': (now - pub_date).total_seconds() / 3600
                        })
                except Exception as e:
                    logger.debug(f"日期解析失败: {publish_date_str} - {str(e)}")
        
        if not old_articles:
            print(f"  ✅ 通过: 所有 {len(articles)} 篇文章都在24小时内")
        else:
            print(f"  ⚠️  警告: 发现 {len(old_articles)} 篇文章超过24小时")
            for old in old_articles[:3]:
                print(f"    - {old['title']}: {old['hours_ago']:.1f} 小时前")
        
        # 验证3: 数据完整性
        print("\n验证3: 数据完整性检查")
        required_fields = ['title', 'url', 'publish_date']
        incomplete = []
        
        for i, article in enumerate(articles):
            missing = [field for field in required_fields if not article.get(field)]
            if missing:
                incomplete.append({
                    'index': i,
                    'title': article.get('title', 'N/A')[:50],
                    'missing': missing
                })
        
        if not incomplete:
            print(f"  ✅ 通过: 所有 {len(articles)} 篇文章都包含必需字段")
        else:
            print(f"  ⚠️  警告: {len(incomplete)} 篇文章缺少必需字段")
            for inc in incomplete[:3]:
                print(f"    - 文章 {inc['index']}: 缺少 {', '.join(inc['missing'])}")
        
        # 显示示例文章
        print("\n" + "=" * 70)
        print("示例文章（前5篇）")
        print("=" * 70)
        for i, article in enumerate(articles[:5], 1):
            print(f"\n{i}. {article.get('title', 'N/A')[:70]}")
            print(f"   URL: {article.get('url', 'N/A')[:70]}")
            print(f"   日期: {article.get('publish_date', 'N/A')}")
            print(f"   摘要: {article.get('content_summary', article.get('content', 'N/A'))[:80]}")
        
        # 统计信息
        print("\n" + "=" * 70)
        print("统计信息")
        print("=" * 70)
        print(f"总文章数: {len(articles)}")
        print(f"唯一URL数: {len(unique_urls)}")
        print(f"24小时内文章: {len(articles) - len(old_articles)}")
        print(f"超过24小时文章: {len(old_articles)}")
        print(f"数据完整文章: {len(articles) - len(incomplete)}")
        
        return {
            'success': True,
            'total': len(articles),
            'unique_urls': len(unique_urls),
            'within_24h': len(articles) - len(old_articles),
            'old_articles': len(old_articles),
            'incomplete': len(incomplete)
        }
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'total': 0
        }


async def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("Newsbreak 完整流程验证测试")
    print("=" * 70)
    
    result = await test_newsbreak_full_flow()
    
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    
    if result and result.get('success'):
        print("✅ Newsbreak完整流程测试通过")
        print(f"   - 采集文章数: {result.get('total', 0)}")
        print(f"   - 唯一URL数: {result.get('unique_urls', 0)}")
        print(f"   - 24小时内: {result.get('within_24h', 0)}")
    elif result:
        print("❌ Newsbreak完整流程测试失败")
        print(f"   错误: {result.get('error', 'Unknown')[:200]}")
    else:
        print("❌ Newsbreak完整流程测试失败: 未返回结果")
    
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

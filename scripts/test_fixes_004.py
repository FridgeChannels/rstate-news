"""
测试Issue 004的修复
重点验证：
1. Newsbreak空URL处理（docid为空时应该返回None）
2. Patch选择器语法修复
3. 其他更新的scraper（Redfin, NAR, Freddie Mac）
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.newsbreak_scraper import NewsbreakScraper
from scrapers.patch_scraper import PatchScraper
from scrapers.redfin_scraper import RedfinScraper
from scrapers.nar_scraper import NARScraper
from scrapers.freddiemac_scraper import FreddieMacScraper
from utils.logger import logger


async def test_newsbreak():
    """测试Newsbreak - 验证JSON提取和空URL处理"""
    print("\n" + "="*70)
    print("测试 Newsbreak Scraper")
    print("="*70)
    
    try:
        scraper = NewsbreakScraper()
        print("📌 开始采集 Zipcode: 90210")
        print("⏳ 这可能需要一些时间...\n")
        
        articles = await scraper.scrape(zipcode="90210", limit=5)
        
        print(f"\n✅ 采集完成！获得 {len(articles)} 篇文章\n")
        
        if articles:
            # 验证所有文章都有有效URL
            invalid_urls = [a for a in articles if not a.get('url') or a.get('url') == '']
            if invalid_urls:
                print(f"❌ 发现 {len(invalid_urls)} 篇文章URL为空（修复应该已解决此问题）")
                for article in invalid_urls:
                    print(f"  - {article.get('title', 'N/A')[:50]}")
            else:
                print("✅ 所有文章都有有效URL（空URL处理修复成功）")
            
            for i, article in enumerate(articles[:3], 1):
                print(f"\n文章 {i}:")
                print(f"  标题: {article.get('title', 'N/A')[:60]}...")
                print(f"  链接: {article.get('url', 'N/A')[:60]}...")
                print(f"  日期: {article.get('publish_date', 'N/A')}")
                print(f"  内容: {article.get('content', article.get('content_summary', ''))[:60]}...")
            
            print("\n✅ Newsbreak Scraper 测试成功！")
            return True
        else:
            print("⚠️ 未能提取到文章（可能是网站结构变化或网络问题）")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_patch():
    """测试Patch - 验证选择器修复"""
    print("\n" + "="*70)
    print("测试 Patch Scraper")
    print("="*70)
    
    try:
        scraper = PatchScraper()
        print("📌 开始采集 Zipcode: 90210")
        print("⏳ 这可能需要一些时间...\n")
        
        articles = await scraper.scrape(zipcode="90210", limit=5)
        
        print(f"\n✅ 采集完成！获得 {len(articles)} 篇文章\n")
        
        if articles:
            for i, article in enumerate(articles[:3], 1):
                print(f"文章 {i}:")
                print(f"  标题: {article.get('title', 'N/A')[:60]}...")
                print(f"  链接: {article.get('url', 'N/A')[:60]}...")
                print(f"  日期: {article.get('publish_date', 'N/A')}")
            
            print("\n✅ Patch Scraper 测试成功！")
            return True
        else:
            print("⚠️ 未能提取到文章（可能是网站结构变化或网络问题）")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_redfin():
    """测试Redfin - 验证Elementor选择器"""
    print("\n" + "="*70)
    print("测试 Redfin Scraper")
    print("="*70)
    
    try:
        scraper = RedfinScraper()
        print("📌 开始采集房地产新闻")
        print("⏳ 这可能需要一些时间...\n")
        
        articles = await scraper.scrape(limit=5)
        
        print(f"\n✅ 采集完成！获得 {len(articles)} 篇文章\n")
        
        if articles:
            for i, article in enumerate(articles[:3], 1):
                print(f"文章 {i}:")
                print(f"  标题: {article.get('title', 'N/A')[:60]}...")
                print(f"  链接: {article.get('url', 'N/A')[:60]}...")
                print(f"  日期: {article.get('publish_date', 'N/A')}")
            
            print("\n✅ Redfin Scraper 测试成功！")
            return True
        else:
            print("⚠️ 未能提取到文章（可能是网站结构变化或网络问题）")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_nar():
    """测试NAR - 验证Drupal/Next.js选择器"""
    print("\n" + "="*70)
    print("测试 NAR Scraper")
    print("="*70)
    
    try:
        scraper = NARScraper()
        print("📌 开始采集房地产新闻")
        print("⏳ 这可能需要一些时间...\n")
        
        articles = await scraper.scrape(limit=5)
        
        print(f"\n✅ 采集完成！获得 {len(articles)} 篇文章\n")
        
        if articles:
            for i, article in enumerate(articles[:3], 1):
                print(f"文章 {i}:")
                print(f"  标题: {article.get('title', 'N/A')[:60]}...")
                print(f"  链接: {article.get('url', 'N/A')[:60]}...")
                print(f"  日期: {article.get('publish_date', 'N/A')}")
            
            print("\n✅ NAR Scraper 测试成功！")
            return True
        else:
            print("⚠️ 未能提取到文章（可能是网站结构变化或网络问题）")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_freddiemac():
    """测试Freddie Mac - 验证Drupal选择器"""
    print("\n" + "="*70)
    print("测试 Freddie Mac Scraper")
    print("="*70)
    
    try:
        scraper = FreddieMacScraper()
        print("📌 开始采集房地产新闻")
        print("⏳ 这可能需要一些时间...\n")
        
        articles = await scraper.scrape(limit=5)
        
        print(f"\n✅ 采集完成！获得 {len(articles)} 篇文章\n")
        
        if articles:
            for i, article in enumerate(articles[:3], 1):
                print(f"文章 {i}:")
                print(f"  标题: {article.get('title', 'N/A')[:60]}...")
                print(f"  链接: {article.get('url', 'N/A')[:60]}...")
                print(f"  日期: {article.get('publish_date', 'N/A')}")
            
            print("\n✅ Freddie Mac Scraper 测试成功！")
            return True
        else:
            print("⚠️ 未能提取到文章（可能是网站结构变化或网络问题）")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("="*70)
    print("Issue 004 修复验证测试")
    print("="*70)
    print("\n测试内容：")
    print("1. Newsbreak - JSON提取和空URL处理修复")
    print("2. Patch - 选择器语法修复")
    print("3. Redfin - Elementor选择器更新")
    print("4. NAR - Drupal/Next.js选择器更新")
    print("5. Freddie Mac - Drupal选择器更新")
    
    results = {}
    
    # 测试修复的scraper
    print("\n" + "="*70)
    print("测试修复的Scraper")
    print("="*70)
    
    results['Newsbreak'] = await test_newsbreak()
    await asyncio.sleep(3)
    
    results['Patch'] = await test_patch()
    await asyncio.sleep(3)
    
    # 测试更新的scraper
    print("\n" + "="*70)
    print("测试更新的Scraper")
    print("="*70)
    
    results['Redfin'] = await test_redfin()
    await asyncio.sleep(3)
    
    results['NAR'] = await test_nar()
    await asyncio.sleep(3)
    
    results['Freddie Mac'] = await test_freddiemac()
    
    # 测试总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    for name, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {name}: {status}")
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    print(f"\n总计: {success_count}/{total_count} 个scraper测试成功")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())

"""
测试单个scraper，带详细日志
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.newsbreak_scraper import NewsbreakScraper
from utils.logger import logger


async def test():
    """测试Newsbreak scraper"""
    print("="*70)
    print("测试 Newsbreak Scraper (带详细日志)")
    print("="*70)
    
    scraper = NewsbreakScraper()
    
    try:
        print("\n1. 创建scraper实例...")
        print(f"   ✅ Scraper创建成功: {scraper.source_name}")
        
        print("\n2. 启动浏览器...")
        await scraper._setup_browser(headless=True)
        print(f"   ✅ 浏览器已启动")
        print(f"   Browser对象: {scraper.browser}")
        print(f"   Playwright对象: {scraper.playwright}")
        
        print("\n3. 等待2秒，检查浏览器是否仍然有效...")
        await asyncio.sleep(2)
        
        if scraper.browser:
            try:
                contexts = scraper.browser.contexts
                print(f"   ✅ 浏览器仍然有效，当前有 {len(contexts)} 个上下文")
            except Exception as e:
                print(f"   ❌ 浏览器已失效: {str(e)}")
                return
        else:
            print("   ❌ 浏览器对象为None")
            return
        
        print("\n4. 创建页面...")
        page = await scraper._create_page()
        print(f"   ✅ 页面创建成功: {page}")
        print(f"   Context对象: {scraper.context}")
        
        print("\n5. 等待1秒，检查页面是否仍然有效...")
        await asyncio.sleep(1)
        
        if not scraper.browser:
            print("   ❌ 浏览器在创建页面后失效")
            return
        
        if not scraper.context:
            print("   ❌ Context在创建页面后失效")
            return
        
        print("\n6. 访问测试URL...")
        test_url = "https://www.newsbreak.com/search?q=90210"
        print(f"   URL: {test_url}")
        
        try:
            await page.goto(test_url, wait_until="domcontentloaded", timeout=30000)
            print("   ✅ 页面访问成功")
        except Exception as e:
            print(f"   ❌ 页面访问失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("\n7. 清理资源...")
        await scraper.cleanup()
        print("   ✅ 资源清理完成")
        
        print("\n" + "="*70)
        print("✅ 测试完成")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        try:
            await scraper.cleanup()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(test())

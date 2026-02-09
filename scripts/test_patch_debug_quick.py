"""
快速测试Patch调试模式
确保调试日志和截图功能正常工作
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.patch_scraper import PatchScraper


async def test():
    print("="*70)
    print("Patch调试模式快速测试")
    print("="*70)
    print("\n这个测试会:")
    print("  1. 创建调试模式的scraper")
    print("  2. 输出调试信息到控制台")
    print("  3. 保存截图到 logs/patch_debug_screenshots/")
    print("\n" + "="*70 + "\n")
    
    try:
        # 创建调试模式的scraper
        print("创建调试模式的PatchScraper...")
        scraper = PatchScraper(debug_mode=True)
        print("✅ Scraper创建成功\n")
        
        print("开始采集（调试模式）...")
        print("注意：浏览器将以可见模式运行\n")
        
        articles = await scraper.scrape(zipcode="90210", limit=3)
        
        print("\n" + "="*70)
        print(f"采集完成！获得 {len(articles)} 篇文章")
        print("="*70)
        
        # 检查截图目录
        screenshot_dir = Path("logs/patch_debug_screenshots")
        if screenshot_dir.exists():
            screenshots = list(screenshot_dir.glob("*.png"))
            print(f"\n✅ 找到 {len(screenshots)} 张截图:")
            for screenshot in screenshots[:5]:  # 只显示前5个
                print(f"   - {screenshot.name}")
        else:
            print("\n⚠️ 截图目录不存在")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test())

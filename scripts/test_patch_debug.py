"""
Patch Scraper调试测试脚本
用于手动测试验证Patch网站的工作流程

使用方法:
    python3 scripts/test_patch_debug.py

注意:
    - 调试模式会以可见模式运行浏览器（headless=False）
    - 会在 logs/patch_debug_screenshots/ 目录保存截图
    - 会输出详细的调试日志
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.patch_scraper import PatchScraper
from utils.logger import logger


async def test_patch_debug():
    """测试Patch scraper的调试模式"""
    import sys
    # 确保输出立即刷新
    sys.stdout.flush()
    
    print("="*70, flush=True)
    print("Patch Scraper 调试测试", flush=True)
    print("="*70, flush=True)
    print("\n📌 调试模式说明:", flush=True)
    print("  - 浏览器将以可见模式运行（headless=False）", flush=True)
    print("  - 截图将保存到: logs/patch_debug_screenshots/", flush=True)
    print("  - 请观察浏览器窗口，记录实际行为", flush=True)
    print("  - 按Ctrl+C可以中断测试", flush=True)
    print("\n" + "="*70 + "\n", flush=True)
    
    try:
        print("🔍 创建调试模式的scraper...", flush=True)
        # 创建调试模式的scraper
        scraper = PatchScraper(debug_mode=True)
        print("✅ Scraper创建成功\n", flush=True)
        
        zipcode = "90210"  # Beverly Hills, CA
        print(f"🔍 开始测试，Zipcode: {zipcode}", flush=True)
        print("⏳ 请观察浏览器窗口...\n", flush=True)
        sys.stdout.flush()
        
        # 运行采集（调试模式）
        articles = await scraper.scrape(zipcode=zipcode, limit=5)
        
        print("\n" + "="*70)
        print("测试完成")
        print("="*70)
        print(f"\n✅ 采集到 {len(articles)} 篇文章\n")
        
        if articles:
            print("文章列表:")
            for i, article in enumerate(articles, 1):
                print(f"\n文章 {i}:")
                print(f"  标题: {article.get('title', 'N/A')[:60]}...")
                print(f"  链接: {article.get('url', 'N/A')[:60]}...")
                print(f"  日期: {article.get('publish_date', 'N/A')}")
        else:
            print("⚠️ 未采集到文章")
            print("\n请检查:")
            print("  1. 浏览器窗口中的实际行为")
            print("  2. logs/patch_debug_screenshots/ 目录中的截图")
            print("  3. 控制台输出的调试日志")
        
        print("\n" + "="*70)
        print("调试信息:")
        print("="*70)
        print(f"  截图目录: logs/patch_debug_screenshots/")
        print(f"  请查看截图和日志，记录发现的选择器和行为")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_patch_debug())

"""
测试浏览器启动
诊断浏览器启动问题
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from utils.logger import logger


async def test_browser_launch():
    """测试浏览器启动"""
    print("="*70)
    print("测试浏览器启动")
    print("="*70)
    
    playwright = None
    browser = None
    
    try:
        print("\n1. 启动 Playwright...")
        playwright = await async_playwright().start()
        print("   ✅ Playwright 启动成功")
        
        print("\n2. 启动 Chromium 浏览器 (headless=True)...")
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ],
            timeout=60000
        )
        print(f"   ✅ 浏览器启动成功: {browser}")
        
        print("\n3. 检查浏览器状态...")
        contexts = browser.contexts
        print(f"   ✅ 浏览器有效，当前有 {len(contexts)} 个上下文")
        
        print("\n4. 创建浏览器上下文...")
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='en-US'
        )
        print(f"   ✅ 上下文创建成功: {context}")
        
        print("\n5. 创建页面...")
        page = await context.new_page()
        print(f"   ✅ 页面创建成功: {page}")
        
        print("\n6. 访问测试页面...")
        await page.goto("https://www.example.com", wait_until="domcontentloaded", timeout=30000)
        print("   ✅ 页面访问成功")
        
        print("\n7. 获取页面标题...")
        title = await page.title()
        print(f"   ✅ 页面标题: {title}")
        
        print("\n8. 关闭资源...")
        await context.close()
        print("   ✅ 上下文已关闭")
        await browser.close()
        print("   ✅ 浏览器已关闭")
        await playwright.stop()
        print("   ✅ Playwright 已停止")
        
        print("\n" + "="*70)
        print("✅ 所有测试通过！浏览器启动正常")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 清理资源
        try:
            if browser:
                await browser.close()
        except:
            pass
        try:
            if playwright:
                await playwright.stop()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(test_browser_launch())

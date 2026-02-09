"""
手动分析指南脚本
提供交互式分析工具，帮助逐个验证网站
"""
import asyncio
from playwright.async_api import async_playwright


async def analyze_with_browser(name: str, url: str, zipcode: str = None):
    """
    使用浏览器分析网站（非无头模式，便于手动观察）
    """
    print(f"\n{'='*70}")
    print(f"分析: {name}")
    print(f"URL: {url}")
    if zipcode:
        print(f"Zipcode: {zipcode}")
    print(f"{'='*70}\n")
    
    print("📋 分析步骤:")
    print("1. 浏览器将自动打开（非无头模式）")
    print("2. 请使用浏览器开发者工具（F12）检查DOM结构")
    print("3. 找到文章列表的实际选择器")
    print("4. 记录标题、链接、日期、摘要的选择器")
    print("5. 按Enter继续...\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            print(f"🌐 正在打开: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(5)
            
            # 处理弹窗
            close_selectors = [
                "button[aria-label*='close' i]",
                ".close-button",
                "#onetrust-accept-btn-handler"
            ]
            for selector in close_selectors:
                try:
                    btn = await page.query_selector(selector)
                    if btn and await btn.is_visible():
                        await btn.click(timeout=2000)
                        await asyncio.sleep(2)
                except:
                    continue
            
            print("\n✅ 页面已加载！")
            print("📝 请使用浏览器开发者工具分析DOM结构")
            print("   1. 按F12打开开发者工具")
            print("   2. 使用元素选择器找到文章列表")
            print("   3. 检查文章元素的类名、ID、data属性")
            print("   4. 记录实际的选择器\n")
            
            # 等待用户分析
            input("按Enter键继续下一个网站（或Ctrl+C退出）...")
            
        except KeyboardInterrupt:
            print("\n\n用户中断")
        except Exception as e:
            print(f"\n❌ 错误: {str(e)}")
        finally:
            await browser.close()


async def main():
    websites = [
        ("Newsbreak", "https://www.newsbreak.com/search?q=90210", "90210"),
        ("Patch", "https://patch.com/search?q=90210", "90210"),
        ("Realtor.com", "https://www.realtor.com/news/real-estate-news/", None),
        ("Redfin", "https://www.redfin.com/news/all-redfin-reports/", None),
        ("NAR", "https://www.nar.realtor/newsroom", None),
        ("Freddie Mac", "https://freddiemac.gcs-web.com/", None),
    ]
    
    print("="*70)
    print("网站手动分析工具")
    print("="*70)
    print("此工具将逐个打开网站，方便您使用浏览器开发者工具分析DOM结构")
    print("="*70)
    
    for name, url, zipcode in websites:
        await analyze_with_browser(name, url, zipcode)
        print("\n" + "-"*70 + "\n")
    
    print("="*70)
    print("分析完成！")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())

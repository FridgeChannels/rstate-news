"""
网站分析工具
使用Playwright访问目标网站，分析DOM结构，提取真实的选择器
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime

# 目标网站列表
WEBSITES = [
    {
        'name': 'Newsbreak',
        'url': 'https://www.newsbreak.com/search?q=90210',
        'type': 'local_news',
        'needs_zipcode': True
    },
    {
        'name': 'Patch',
        'url': 'https://patch.com/search?q=90210',
        'type': 'local_news',
        'needs_zipcode': True
    },
    {
        'name': 'Realtor.com',
        'url': 'https://www.realtor.com/news/real-estate-news/',
        'type': 'real_estate',
        'needs_zipcode': False
    },
    {
        'name': 'Redfin',
        'url': 'https://www.redfin.com/news/all-redfin-reports/',
        'type': 'real_estate',
        'needs_zipcode': False
    },
    {
        'name': 'NAR',
        'url': 'https://www.nar.realtor/newsroom',
        'type': 'real_estate',
        'needs_zipcode': False
    },
    {
        'name': 'Freddie Mac',
        'url': 'https://freddiemac.gcs-web.com/',
        'type': 'real_estate',
        'needs_zipcode': False
    }
]


async def analyze_website(website_info: dict, output_dir: Path):
    """分析单个网站的DOM结构"""
    name = website_info['name']
    url = website_info['url']
    
    print(f"\n{'='*60}")
    print(f"分析网站: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 非无头模式，便于观察
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            # 访问网站
            print(f"正在访问: {url}")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)  # 等待页面完全加载
            
            # 处理可能的弹窗
            try:
                # 尝试关闭常见的弹窗
                close_selectors = [
                    "button[aria-label*='close']",
                    "button[aria-label*='Close']",
                    ".close-button",
                    "[data-testid='close']",
                    ".modal-close",
                    ".popup-close"
                ]
                for selector in close_selectors:
                    try:
                        close_btn = await page.query_selector(selector)
                        if close_btn:
                            await close_btn.click(timeout=2000)
                            await asyncio.sleep(1)
                            break
                    except:
                        continue
            except:
                pass
            
            # 截图保存
            screenshot_path = output_dir / f"{name.lower().replace(' ', '_')}_screenshot.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"截图已保存: {screenshot_path}")
            
            # 分析文章列表
            print("\n分析文章列表结构...")
            
            # 尝试多种常见的选择器
            article_selectors = [
                "article",
                ".article",
                ".article-card",
                ".news-item",
                ".news-card",
                "[data-testid='article']",
                ".post",
                ".entry",
                ".item"
            ]
            
            found_articles = []
            for selector in article_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"  ✓ 找到 {len(elements)} 个元素使用选择器: {selector}")
                    found_articles = elements[:5]  # 只分析前5个
                    break
            
            if not found_articles:
                print("  ✗ 未找到文章列表，可能需要其他选择器")
                # 尝试查找包含链接的元素
                links = await page.query_selector_all("a[href*='/news'], a[href*='/article']")
                if links:
                    print(f"  → 找到 {len(links)} 个可能的新闻链接")
            
            # 分析第一个文章元素的结构
            if found_articles:
                print("\n分析文章元素结构（第一个）...")
                first_article = found_articles[0]
                
                # 提取HTML结构
                html = await first_article.inner_html()
                html_path = output_dir / f"{name.lower().replace(' ', '_')}_article_structure.html"
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"  HTML结构已保存: {html_path}")
                
                # 尝试提取关键字段
                print("\n尝试提取关键字段...")
                
                # 标题
                title_selectors = ["h1", "h2", "h3", ".title", ".headline", "[data-testid='title']"]
                for selector in title_selectors:
                    title_elem = await first_article.query_selector(selector)
                    if title_elem:
                        title = await title_elem.inner_text()
                        print(f"  ✓ 标题选择器: {selector} -> {title[:50]}...")
                        break
                
                # 链接
                link_elem = await first_article.query_selector("a[href]")
                if link_elem:
                    href = await link_elem.get_attribute("href")
                    print(f"  ✓ 链接: {href}")
                
                # 日期
                date_selectors = [".date", ".publish-date", "time", "[datetime]", ".timestamp"]
                for selector in date_selectors:
                    date_elem = await first_article.query_selector(selector)
                    if date_elem:
                        date_text = await date_elem.inner_text()
                        datetime_attr = await date_elem.get_attribute("datetime")
                        print(f"  ✓ 日期选择器: {selector} -> {date_text or datetime_attr}")
                        break
                
                # 摘要
                summary_selectors = [".summary", ".excerpt", ".description", "p"]
                for selector in summary_selectors:
                    summary_elem = await first_article.query_selector(selector)
                    if summary_elem:
                        summary = await summary_elem.inner_text()
                        if len(summary) > 20:  # 过滤太短的文本
                            print(f"  ✓ 摘要选择器: {selector} -> {summary[:50]}...")
                            break
            
            # 检查是否有Cloudflare或其他反爬机制
            print("\n检查反爬虫机制...")
            cf_check = await page.query_selector("#challenge-form, .cf-browser-verification")
            if cf_check:
                print("  ⚠ 检测到Cloudflare验证")
            else:
                print("  ✓ 未检测到明显的反爬虫机制")
            
            # 等待用户观察（可选）
            print(f"\n页面已加载，请在浏览器中观察 {name} 的结构...")
            print("按 Enter 继续下一个网站...")
            # input()  # 取消注释以手动控制
            
        except Exception as e:
            print(f"  ✗ 分析失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()


async def main():
    """主函数"""
    output_dir = Path(__file__).parent.parent / "analysis_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("网站DOM结构分析工具")
    print("="*60)
    print(f"输出目录: {output_dir}")
    print(f"将分析 {len(WEBSITES)} 个网站\n")
    
    for website in WEBSITES:
        await analyze_website(website, output_dir)
        await asyncio.sleep(2)  # 网站之间延迟
    
    print("\n" + "="*60)
    print("分析完成！")
    print(f"结果保存在: {output_dir}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

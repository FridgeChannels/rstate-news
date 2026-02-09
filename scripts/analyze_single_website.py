"""
单个网站深度分析工具
分析指定网站，提取真实DOM选择器，验证元素提取
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from typing import Dict, List, Any, Optional


async def analyze_single_website(
    name: str,
    url: str,
    zipcode: Optional[str] = None,
    output_dir: Path = None
) -> Dict[str, Any]:
    """
    深度分析单个网站
    
    Args:
        name: 网站名称
        url: 网站URL
        zipcode: 邮政编码（如果需要）
        output_dir: 输出目录
        
    Returns:
        分析结果字典，包含找到的选择器和提取的数据
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "analysis_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"深度分析: {name}")
    print(f"URL: {url}")
    if zipcode:
        print(f"Zipcode: {zipcode}")
    print(f"{'='*70}\n")
    
    result = {
        'name': name,
        'url': url,
        'zipcode': zipcode,
        'article_selector': None,
        'title_selector': None,
        'link_selector': None,
        'date_selector': None,
        'summary_selector': None,
        'extracted_data': [],
        'has_cloudflare': False,
        'needs_special_handling': []
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        try:
            # 访问网站
            print(f"📍 访问网站: {url}")
            try:
                # 先尝试domcontentloaded（最快）
                await page.goto(url, wait_until="domcontentloaded", timeout=90000)
                print("  ✓ 页面DOM已加载")
            except Exception as e1:
                print(f"  ⚠ domcontentloaded超时，尝试load: {str(e1)[:50]}")
                try:
                    await page.goto(url, wait_until="load", timeout=90000)
                    print("  ✓ 页面已加载")
                except Exception as e2:
                    print(f"  ⚠ load超时，尝试commit: {str(e2)[:50]}")
                    try:
                        await page.goto(url, wait_until="commit", timeout=90000)
                        print("  ✓ 页面导航已提交")
                    except Exception as e3:
                        print(f"  ❌ 所有加载策略都失败: {str(e3)[:50]}")
                        raise
            
            # 等待JavaScript执行和内容加载
            print("  ⏳ 等待页面内容加载...")
            await asyncio.sleep(10)  # 增加等待时间，让动态内容加载
            
            # 处理弹窗
            print("🔍 检查弹窗...")
            close_selectors = [
                "button[aria-label*='close' i]",
                "button[aria-label*='Close' i]",
                ".close-button",
                "[data-testid='close']",
                ".modal-close",
                ".popup-close",
                ".cookie-consent button",
                "#onetrust-accept-btn-handler"
            ]
            for selector in close_selectors:
                try:
                    close_btn = await page.query_selector(selector)
                    if close_btn and await close_btn.is_visible():
                        await close_btn.click(timeout=2000)
                        print(f"  ✓ 关闭弹窗: {selector}")
                        await asyncio.sleep(2)
                        break
                except:
                    continue
            
            # 检查Cloudflare
            print("🛡️  检查反爬虫机制...")
            cf_selectors = [
                "#challenge-form",
                ".cf-browser-verification",
                "#cf-wrapper",
                ".cf-im-under-attack"
            ]
            for selector in cf_selectors:
                if await page.query_selector(selector):
                    result['has_cloudflare'] = True
                    print(f"  ⚠ 检测到Cloudflare: {selector}")
                    print("  → 等待Cloudflare验证完成...")
                    await asyncio.sleep(10)  # 等待验证
                    break
            
            # 截图
            screenshot_path = output_dir / f"{name.lower().replace(' ', '_')}_screenshot.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"📸 截图已保存: {screenshot_path}")
            
            # 分析文章列表 - 尝试多种选择器
            print("\n🔎 分析文章列表...")
            article_selectors = [
                "article",
                ".article",
                ".article-card",
                ".article-item",
                ".news-item",
                ".news-card",
                ".post",
                ".post-item",
                ".entry",
                ".entry-item",
                ".item",
                "[data-testid*='article']",
                "[data-testid*='news']",
                "[data-testid*='post']",
                ".card",
                ".story",
                ".story-card",
                "li[class*='article']",
                "div[class*='article']"
            ]
            
            found_articles = []
            working_selector = None
            
            for selector in article_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        # 检查元素是否可见且包含链接
                        visible_count = 0
                        for elem in elements[:10]:  # 检查前10个
                            if await elem.is_visible():
                                # 检查是否包含链接
                                link = await elem.query_selector("a[href]")
                                if link:
                                    visible_count += 1
                        
                        if visible_count >= 3:  # 至少3个可见的文章
                            print(f"  ✓ 找到 {len(elements)} 个元素，{visible_count} 个可见 (选择器: {selector})")
                            found_articles = elements
                            working_selector = selector
                            result['article_selector'] = selector
                            break
                except Exception as e:
                    continue
            
            if not found_articles:
                print("  ✗ 未找到文章列表，尝试其他方法...")
                # 尝试查找所有包含新闻链接的元素
                all_links = await page.query_selector_all("a[href*='/news'], a[href*='/article'], a[href*='/story']")
                if all_links:
                    print(f"  → 找到 {len(all_links)} 个可能的新闻链接")
                    # 尝试找到这些链接的父容器
                    for link in all_links[:10]:
                        parent = await link.evaluate_handle("el => el.closest('article, .card, .item, div[class*=\"article\"], div[class*=\"news\"]')")
                        if parent:
                            found_articles.append(parent)
                    if found_articles:
                        result['article_selector'] = "a[href*='/news'], a[href*='/article'] -> parent"
                        working_selector = "custom"
            
            # 分析前3个文章元素
            if found_articles:
                print(f"\n📝 分析文章元素（前{min(3, len(found_articles))}个）...")
                
                for idx, article in enumerate(found_articles[:3]):
                    print(f"\n  文章 #{idx + 1}:")
                    article_data = {}
                    
                    # 提取HTML结构（第一个）
                    if idx == 0:
                        html = await article.inner_html()
                        html_path = output_dir / f"{name.lower().replace(' ', '_')}_article_structure.html"
                        with open(html_path, 'w', encoding='utf-8') as f:
                            f.write(html)
                        print(f"  📄 HTML结构已保存: {html_path}")
                    
                    # 标题
                    title_selectors = [
                        "h1", "h2", "h3", "h4",
                        ".title", ".headline", ".article-title",
                        "[data-testid*='title']",
                        "a[href] > *:first-child"
                    ]
                    for selector in title_selectors:
                        try:
                            title_elem = await article.query_selector(selector)
                            if title_elem:
                                title_text = await title_elem.inner_text()
                                if title_text and len(title_text.strip()) > 5:
                                    article_data['title'] = title_text.strip()
                                    article_data['title_selector'] = selector
                                    if not result['title_selector']:
                                        result['title_selector'] = selector
                                    print(f"    ✓ 标题: {title_text[:60]}... (选择器: {selector})")
                                    break
                        except:
                            continue
                    
                    # 链接
                    link_selectors = [
                        "a[href]",
                        "a.article-link",
                        "a[href*='/news']",
                        "a[href*='/article']"
                    ]
                    for selector in link_selectors:
                        try:
                            link_elem = await article.query_selector(selector)
                            if link_elem:
                                href = await link_elem.get_attribute("href")
                                if href:
                                    # 转换为绝对URL
                                    if href.startswith('/'):
                                        from urllib.parse import urljoin
                                        href = urljoin(url, href)
                                    elif not href.startswith('http'):
                                        href = f"{url.rstrip('/')}/{href.lstrip('/')}"
                                    article_data['url'] = href
                                    article_data['link_selector'] = selector
                                    if not result['link_selector']:
                                        result['link_selector'] = selector
                                    print(f"    ✓ 链接: {href[:80]}... (选择器: {selector})")
                                    break
                        except:
                            continue
                    
                    # 日期
                    date_selectors = [
                        "time[datetime]",
                        "time",
                        ".date",
                        ".publish-date",
                        ".published-date",
                        "[datetime]",
                        ".timestamp",
                        "[data-testid*='date']"
                    ]
                    for selector in date_selectors:
                        try:
                            date_elem = await article.query_selector(selector)
                            if date_elem:
                                date_text = await date_elem.inner_text()
                                datetime_attr = await date_elem.get_attribute("datetime")
                                date_value = datetime_attr or date_text
                                if date_value:
                                    article_data['publish_date'] = date_value.strip()
                                    article_data['date_selector'] = selector
                                    if not result['date_selector']:
                                        result['date_selector'] = selector
                                    print(f"    ✓ 日期: {date_value} (选择器: {selector})")
                                    break
                        except:
                            continue
                    
                    # 摘要
                    summary_selectors = [
                        ".summary",
                        ".excerpt",
                        ".description",
                        ".article-summary",
                        "p",
                        ".snippet"
                    ]
                    for selector in summary_selectors:
                        try:
                            summary_elem = await article.query_selector(selector)
                            if summary_elem:
                                summary_text = await summary_elem.inner_text()
                                if summary_text and len(summary_text.strip()) > 20:
                                    article_data['summary'] = summary_text.strip()[:200]
                                    article_data['summary_selector'] = selector
                                    if not result['summary_selector']:
                                        result['summary_selector'] = selector
                                    print(f"    ✓ 摘要: {summary_text[:60]}... (选择器: {selector})")
                                    break
                        except:
                            continue
                    
                    if article_data:
                        result['extracted_data'].append(article_data)
                
                # 验证提取结果
                print(f"\n✅ 提取验证:")
                print(f"  文章数量: {len(result['extracted_data'])}")
                for i, data in enumerate(result['extracted_data']):
                    has_title = 'title' in data
                    has_url = 'url' in data
                    has_date = 'publish_date' in data
                    has_summary = 'summary' in data
                    print(f"  文章 {i+1}: 标题={has_title} 链接={has_url} 日期={has_date} 摘要={has_summary}")
            
            # 保存分析结果
            result_path = output_dir / f"{name.lower().replace(' ', '_')}_analysis.json"
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 分析结果已保存: {result_path}")
            
            return result
            
        except Exception as e:
            print(f"\n❌ 分析失败: {str(e)}")
            import traceback
            traceback.print_exc()
            result['error'] = str(e)
            return result
        
        finally:
            print(f"\n⏸️  等待5秒后关闭浏览器...")
            await asyncio.sleep(5)
            await browser.close()


async def main():
    """主函数 - 分析单个网站"""
    import sys
    
    if len(sys.argv) < 3:
        print("用法: python analyze_single_website.py <网站名称> <URL> [zipcode]")
        print("\n示例:")
        print("  python analyze_single_website.py Newsbreak 'https://www.newsbreak.com/search?q=90210' 90210")
        print("  python analyze_single_website.py Realtor 'https://www.realtor.com/news/real-estate-news/'")
        sys.exit(1)
    
    name = sys.argv[1]
    url = sys.argv[2]
    zipcode = sys.argv[3] if len(sys.argv) > 3 else None
    
    result = await analyze_single_website(name, url, zipcode)
    
    print(f"\n{'='*70}")
    print("分析完成！")
    print(f"{'='*70}\n")
    
    # 输出关键信息
    if result.get('article_selector'):
        print("✅ 找到的选择器:")
        print(f"  文章列表: {result['article_selector']}")
        if result.get('title_selector'):
            print(f"  标题: {result['title_selector']}")
        if result.get('link_selector'):
            print(f"  链接: {result['link_selector']}")
        if result.get('date_selector'):
            print(f"  日期: {result['date_selector']}")
        if result.get('summary_selector'):
            print(f"  摘要: {result['summary_selector']}")
    else:
        print("❌ 未能找到有效的文章选择器")


if __name__ == "__main__":
    asyncio.run(main())

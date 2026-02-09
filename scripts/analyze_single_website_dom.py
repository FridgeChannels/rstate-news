"""
分析单个网站的DOM结构并保存
用法: python3 scripts/analyze_single_website_dom.py <网站名称>
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


WEBSITE_CONFIGS = {
    'newsbreak': {
        'name': 'Newsbreak',
        'url': 'https://www.newsbreak.com/search?q=90210',
        'needs_zipcode': True,
    },
    'patch': {
        'name': 'Patch',
        'url': 'https://patch.com/search?q=90210',
        'needs_zipcode': True,
    },
    'realtor': {
        'name': 'Realtor.com',
        'url': 'https://www.realtor.com/news/real-estate-news/',
        'needs_zipcode': False,
    },
    'redfin': {
        'name': 'Redfin',
        'url': 'https://www.redfin.com/news/all-redfin-reports/',
        'needs_zipcode': False,
    },
    'nar': {
        'name': 'NAR',
        'url': 'https://www.nar.realtor/newsroom',
        'needs_zipcode': False,
    },
    'freddiemac': {
        'name': 'Freddie Mac',
        'url': 'https://freddiemac.gcs-web.com/news-releases',
        'needs_zipcode': False,
    },
}


async def analyze_website(website_key: str):
    """分析单个网站"""
    if website_key not in WEBSITE_CONFIGS:
        print(f"❌ 未知网站: {website_key}")
        print(f"可用网站: {', '.join(WEBSITE_CONFIGS.keys())}")
        return
    
    config = WEBSITE_CONFIGS[website_key]
    name = config['name']
    url = config['url']
    needs_zipcode = config['needs_zipcode']
    
    output_dir = Path(__file__).parent.parent / "analysis" / "dom_structures"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"分析: {name}")
    print(f"URL: {url}")
    print(f"需要Zipcode: {needs_zipcode}")
    print(f"{'='*70}\n")
    
    result = {
        'name': name,
        'url': url,
        'needs_zipcode': needs_zipcode,
        'analyzed_at': datetime.now().isoformat(),
        'zipcode_input': None,
        'article_list': None,
        'sample_articles': [],
    }
    
    playwright = None
    browser = None
    context = None
    page = None
    
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        try:
            print(f"📍 访问: {url}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except:
                try:
                    await page.goto(url, wait_until="load", timeout=60000)
                except:
                    await page.goto(url, wait_until="commit", timeout=60000)
            
            print("  ✓ 页面已加载")
            await asyncio.sleep(5)
            
            # 处理弹窗
            close_selectors = [
                "button[aria-label*='close' i]", ".close-button",
                "[data-testid='close']", ".cookie-consent button"
            ]
            for selector in close_selectors:
                try:
                    btn = await page.query_selector(selector)
                    if btn and await btn.is_visible():
                        await btn.click(timeout=2000)
                        await asyncio.sleep(1)
                        break
                except:
                    continue
            
            await asyncio.sleep(3)
            
            # 获取完整DOM
            html_content = await page.content()
            
            # 保存完整HTML
            html_file = output_dir / f"{website_key}_full_dom.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"  ✓ 完整DOM已保存: {html_file}")
            
            # 使用BeautifulSoup解析
            soup = BeautifulSoup(html_content, 'lxml')
            
            # 分析zipcode输入框
            if needs_zipcode:
                print("\n🔍 查找Zipcode输入框...")
                zipcode_selectors = [
                    'input[type="text"][placeholder*="zip" i]',
                    'input[type="text"][placeholder*="postal" i]',
                    'input[name*="zip" i]',
                    'input[id*="zip" i]',
                    'input[type="search"]',
                ]
                
                for selector in zipcode_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element and await element.is_visible():
                            attributes = await element.evaluate('''el => {
                                const attrs = {};
                                for (let attr of el.attributes) {
                                    attrs[attr.name] = attr.value;
                                }
                                return attrs;
                            }''')
                            bounding_box = await element.bounding_box()
                            
                            result['zipcode_input'] = {
                                'selector': selector,
                                'attributes': attributes,
                                'position': bounding_box,
                            }
                            print(f"  ✓ 找到Zipcode输入框: {selector}")
                            break
                    except:
                        continue
            
            # 分析文章列表
            print("\n🔍 查找文章列表...")
            article_selectors = [
                'article', '.article-card', '.news-item', '.story-card',
                '[data-testid*="article" i]', '[class*="article" i]',
                '[class*="news" i]', '.card',
            ]
            
            for selector in article_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    visible_elements = []
                    for elem in elements[:10]:
                        try:
                            if await elem.is_visible():
                                link = await elem.query_selector("a[href]")
                                if link:
                                    visible_elements.append(elem)
                        except:
                            continue
                    
                    if len(visible_elements) >= 3:
                        print(f"  ✓ 找到 {len(visible_elements)} 个文章元素: {selector}")
                        
                        # 分析第一个文章
                        first = visible_elements[0]
                        article_info = {'selector': selector, 'count': len(visible_elements)}
                        
                        # 标题
                        for title_sel in ['h1', 'h2', 'h3', '.title', '.headline', 'a']:
                            try:
                                title_elem = await first.query_selector(title_sel)
                                if title_elem:
                                    title_text = await title_elem.inner_text()
                                    if title_text and len(title_text.strip()) > 10:
                                        article_info['title_selector'] = f"{selector} {title_sel}"
                                        article_info['title_example'] = title_text.strip()[:100]
                                        break
                            except:
                                continue
                        
                        # 链接
                        try:
                            link_elem = await first.query_selector("a[href]")
                            if link_elem:
                                href = await link_elem.get_attribute("href")
                                article_info['link_selector'] = f"{selector} a[href]"
                                article_info['link_example'] = href
                        except:
                            pass
                        
                        # 日期
                        for date_sel in ['time', '.date', '[datetime]']:
                            try:
                                date_elem = await first.query_selector(date_sel)
                                if date_elem:
                                    date_text = await date_elem.inner_text()
                                    datetime_attr = await date_elem.get_attribute("datetime")
                                    if date_text or datetime_attr:
                                        article_info['date_selector'] = f"{selector} {date_sel}"
                                        article_info['date_example'] = date_text or datetime_attr
                                        break
                            except:
                                continue
                        
                        result['article_list'] = article_info
                        
                        # 保存前3个文章的HTML结构
                        for i, elem in enumerate(visible_elements[:3]):
                            try:
                                article_html = await elem.inner_html()
                                result['sample_articles'].append({
                                    'index': i + 1,
                                    'html': article_html[:3000],
                                })
                            except:
                                pass
                        break
                except:
                    continue
            
            # 截图
            screenshot_file = output_dir / f"{website_key}_screenshot.png"
            await page.screenshot(path=str(screenshot_file), full_page=True)
            print(f"  ✓ 截图已保存: {screenshot_file}")
            
            # 保存分析结果
            json_file = output_dir / f"{website_key}_analysis.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"  ✓ 分析结果已保存: {json_file}")
            
            print(f"\n✅ {name} 分析完成")
            
        except Exception as e:
            print(f"\n❌ {name} 分析失败: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # 按正确顺序清理资源
            try:
                if page:
                    await page.close()
            except:
                pass
            try:
                if context:
                    await context.close()
            except:
                pass
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
    if len(sys.argv) < 2:
        print("用法: python3 scripts/analyze_single_website_dom.py <网站名称>")
        print(f"可用网站: {', '.join(WEBSITE_CONFIGS.keys())}")
        sys.exit(1)
    
    website_key = sys.argv[1].lower()
    asyncio.run(analyze_website(website_key))

"""
分析并保存所有网站的DOM结构
标记关键元素位置（zipcode输入框、文章列表等）
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


# 网站配置
WEBSITES = [
    {
        'name': 'Newsbreak',
        'url': 'https://www.newsbreak.com/search?q=90210',
        'needs_zipcode': True,
        'zipcode_input_selector': None,  # 待分析
        'article_list_selector': None,  # 待分析
    },
    {
        'name': 'Patch',
        'url': 'https://patch.com/search?q=90210',
        'needs_zipcode': True,
        'zipcode_input_selector': None,
        'article_list_selector': None,
    },
    {
        'name': 'Realtor.com',
        'url': 'https://www.realtor.com/news/real-estate-news/',
        'needs_zipcode': False,
        'article_list_selector': None,
    },
    {
        'name': 'Redfin',
        'url': 'https://www.redfin.com/news/all-redfin-reports/',
        'needs_zipcode': False,
        'article_list_selector': None,
    },
    {
        'name': 'NAR',
        'url': 'https://www.nar.realtor/newsroom',
        'needs_zipcode': False,
        'article_list_selector': None,
    },
    {
        'name': 'Freddie Mac',
        'url': 'https://freddiemac.gcs-web.com/news-releases',
        'needs_zipcode': False,
        'article_list_selector': None,
    },
]


async def analyze_website(website_info, output_dir: Path):
    """分析单个网站的DOM结构"""
    name = website_info['name']
    url = website_info['url']
    needs_zipcode = website_info['needs_zipcode']
    
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
        'dom_structure': None,
    }
    
    async with async_playwright() as p:
        # 使用headless模式，更稳定
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            print(f"📍 访问: {url}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as e1:
                print(f"  ⚠️  domcontentloaded超时，尝试load: {str(e1)[:50]}")
                try:
                    await page.goto(url, wait_until="load", timeout=60000)
                except Exception as e2:
                    print(f"  ⚠️  load超时，尝试commit: {str(e2)[:50]}")
                    await page.goto(url, wait_until="commit", timeout=60000)
            
            print("  ✓ 页面已加载")
            await asyncio.sleep(5)  # 等待页面完全加载
            
            # 处理可能的弹窗
            try:
                close_selectors = [
                    "button[aria-label*='close' i]",
                    "button[aria-label*='Close' i]",
                    ".close-button",
                    "[data-testid='close']",
                    ".modal-close",
                    ".cookie-consent button",
                    "#onetrust-accept-btn-handler"
                ]
                for selector in close_selectors:
                    try:
                        btn = await page.query_selector(selector)
                        if btn and await btn.is_visible():
                            await btn.click(timeout=2000)
                            await asyncio.sleep(1)
                            print(f"  ✓ 关闭弹窗: {selector}")
                            break
                    except:
                        continue
            except:
                pass
            
            # 等待内容加载
            await asyncio.sleep(3)
            
            # 获取完整DOM
            html_content = await page.content()
            result['dom_structure'] = html_content
            
            # 保存完整HTML
            html_file = output_dir / f"{name.lower().replace(' ', '_')}_full_dom.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"  ✓ 完整DOM已保存: {html_file}")
            
            # 使用BeautifulSoup解析
            soup = BeautifulSoup(html_content, 'lxml')
            
            # 分析zipcode输入框（如果需要）
            if needs_zipcode:
                print("\n🔍 查找Zipcode输入框...")
                zipcode_selectors = [
                    'input[type="text"][placeholder*="zip" i]',
                    'input[type="text"][placeholder*="zipcode" i]',
                    'input[type="text"][placeholder*="postal" i]',
                    'input[name*="zip" i]',
                    'input[id*="zip" i]',
                    'input[class*="zip" i]',
                    'input[type="search"]',
                ]
                
                for selector in zipcode_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element and await element.is_visible():
                            # 获取元素信息
                            tag_name = await element.evaluate('el => el.tagName')
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
                                'tag': tag_name.lower(),
                                'attributes': attributes,
                                'position': bounding_box,
                                'xpath': await element.evaluate('''el => {
                                    let path = '';
                                    while (el && el.nodeType === 1) {
                                        let index = 0;
                                        let sibling = el.previousSibling;
                                        while (sibling) {
                                            if (sibling.nodeType === 1 && sibling.tagName === el.tagName) {
                                                index++;
                                            }
                                            sibling = sibling.previousSibling;
                                        }
                                        let tagName = el.tagName.toLowerCase();
                                        let seg = tagName + (index > 0 ? '[' + (index + 1) + ']' : '');
                                        path = '/' + seg + path;
                                        el = el.parentElement;
                                    }
                                    return path;
                                }''')
                            }
                            print(f"  ✓ 找到Zipcode输入框: {selector}")
                            print(f"    位置: {bounding_box}")
                            break
                    except Exception as e:
                        continue
                
                if not result['zipcode_input']:
                    print("  ⚠️  未找到Zipcode输入框，可能需要手动分析")
            
            # 分析文章列表
            print("\n🔍 查找文章列表...")
            article_selectors = [
                'article',
                '.article-card',
                '.news-item',
                '.story-card',
                '[data-testid*="article" i]',
                '[class*="article" i]',
                '[class*="news" i]',
                '[class*="story" i]',
                '.card',
                'div[class*="item" i]',
            ]
            
            found_articles = []
            for selector in article_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    visible_elements = []
                    for elem in elements[:10]:  # 只检查前10个
                        try:
                            if await elem.is_visible():
                                # 检查是否包含链接（文章通常有链接）
                                link = await elem.query_selector("a[href]")
                                if link:
                                    visible_elements.append(elem)
                        except:
                            continue
                    
                    if len(visible_elements) >= 3:  # 至少找到3个可见的文章元素
                        print(f"  ✓ 找到 {len(visible_elements)} 个文章元素 (选择器: {selector})")
                        
                        # 分析第一个文章元素的结构
                        first_article = visible_elements[0]
                        
                        # 获取元素信息
                        article_info = {
                            'selector': selector,
                            'count': len(visible_elements),
                            'sample_element': {}
                        }
                        
                        # 查找标题
                        title_selectors = ['h1', 'h2', 'h3', 'h4', '.title', '.headline', 'a[href]']
                        for title_sel in title_selectors:
                            try:
                                title_elem = await first_article.query_selector(title_sel)
                                if title_elem:
                                    title_text = await title_elem.inner_text()
                                    if title_text and len(title_text.strip()) > 10:
                                        article_info['sample_element']['title'] = {
                                            'selector': f"{selector} > {title_sel}",
                                            'text': title_text.strip()[:100],
                                        }
                                        break
                            except:
                                continue
                        
                        # 查找链接
                        try:
                            link_elem = await first_article.query_selector("a[href]")
                            if link_elem:
                                href = await link_elem.get_attribute("href")
                                article_info['sample_element']['link'] = {
                                    'selector': f"{selector} > a[href]",
                                    'href': href,
                                }
                        except:
                            pass
                        
                        # 查找日期
                        date_selectors = ['time', '.date', '.publish-date', '[datetime]', '.timestamp']
                        for date_sel in date_selectors:
                            try:
                                date_elem = await first_article.query_selector(date_sel)
                                if date_elem:
                                    date_text = await date_elem.inner_text()
                                    datetime_attr = await date_elem.get_attribute("datetime")
                                    if date_text or datetime_attr:
                                        article_info['sample_element']['date'] = {
                                            'selector': f"{selector} > {date_sel}",
                                            'text': date_text,
                                            'datetime': datetime_attr,
                                        }
                                        break
                            except:
                                continue
                        
                        # 查找摘要
                        summary_selectors = ['.summary', '.excerpt', '.description', 'p']
                        for summary_sel in summary_selectors:
                            try:
                                summary_elem = await first_article.query_selector(summary_sel)
                                if summary_elem:
                                    summary_text = await summary_elem.inner_text()
                                    if summary_text and len(summary_text.strip()) > 20:
                                        article_info['sample_element']['summary'] = {
                                            'selector': f"{selector} > {summary_sel}",
                                            'text': summary_text.strip()[:200],
                                        }
                                        break
                            except:
                                continue
                        
                        result['article_list'] = article_info
                        found_articles = visible_elements
                        break
                except Exception as e:
                    continue
            
            if not result['article_list']:
                print("  ⚠️  未找到文章列表，可能需要手动分析")
            
            # 分析前3个文章元素的详细结构
            if found_articles:
                print(f"\n📝 分析前3个文章元素的详细结构...")
                for i, article_elem in enumerate(found_articles[:3]):
                    try:
                        article_html = await article_elem.inner_html()
                        article_soup = BeautifulSoup(article_html, 'lxml')
                        
                        article_data = {
                            'index': i + 1,
                            'html_structure': str(article_soup.prettify())[:2000],  # 限制长度
                            'text_content': await article_elem.inner_text()[:500],
                        }
                        
                        result['sample_articles'].append(article_data)
                        print(f"  ✓ 文章 {i+1} 结构已分析")
                    except Exception as e:
                        print(f"  ⚠️  分析文章 {i+1} 失败: {str(e)[:50]}")
            
            # 截图
            screenshot_file = output_dir / f"{name.lower().replace(' ', '_')}_screenshot.png"
            await page.screenshot(path=str(screenshot_file), full_page=True)
            print(f"\n  ✓ 截图已保存: {screenshot_file}")
            
            print(f"\n✅ {name} 分析完成")
            
        except Exception as e:
            print(f"\n❌ {name} 分析失败: {str(e)}")
            import traceback
            traceback.print_exc()
            result['error'] = str(e)
        
        finally:
            await browser.close()
    
    return result


async def main():
    """主函数"""
    output_dir = Path(__file__).parent.parent / "analysis" / "dom_structures"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*70)
    print("网站DOM结构分析工具")
    print("="*70)
    print(f"输出目录: {output_dir}")
    print(f"将分析 {len(WEBSITES)} 个网站\n")
    
    all_results = {}
    
    for website in WEBSITES:
        try:
            result = await analyze_website(website, output_dir)
            all_results[website['name']] = result
            
            # 保存单个网站的分析结果
            json_file = output_dir / f"{website['name'].lower().replace(' ', '_')}_analysis.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"  ✓ 分析结果已保存: {json_file}\n")
        except Exception as e:
            print(f"  ❌ {website['name']} 分析失败: {str(e)}")
            all_results[website['name']] = {
                'name': website['name'],
                'url': website['url'],
                'error': str(e)
            }
        
        # 网站之间延迟
        await asyncio.sleep(3)
    
    # 保存汇总结果
    summary_file = output_dir / "all_websites_analysis.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    # 生成标记文档
    generate_markup_document(all_results, output_dir)
    
    print("\n" + "="*70)
    print("✅ 所有网站分析完成！")
    print(f"结果保存在: {output_dir}")
    print("="*70)


def generate_markup_document(results, output_dir: Path):
    """生成元素标记文档"""
    doc_path = output_dir / "ELEMENT_MARKUP.md"
    
    content = """# 网站元素标记文档

本文档记录了所有网站的关键元素位置，用于指导scraper开发。

生成时间: {timestamp}

---

""".format(timestamp=datetime.now().isoformat())
    
    for name, result in results.items():
        content += f"## {name}\n\n"
        content += f"**URL**: {result['url']}\n\n"
        content += f"**需要Zipcode**: {'是' if result['needs_zipcode'] else '否'}\n\n"
        
        if result.get('error'):
            content += f"**错误**: {result['error']}\n\n"
            content += "---\n\n"
            continue
        
        if result['needs_zipcode'] and result.get('zipcode_input'):
            zipcode = result['zipcode_input']
            content += "### Zipcode输入框\n\n"
            content += f"- **选择器**: `{zipcode['selector']}`\n"
            content += f"- **标签**: `{zipcode['tag']}`\n"
            content += f"- **XPath**: `{zipcode.get('xpath', 'N/A')}`\n"
            content += f"- **位置**: {zipcode.get('position', {})}\n"
            if zipcode.get('attributes'):
                content += f"- **属性**:\n"
                for key, value in zipcode['attributes'].items():
                    content += f"  - `{key}`: `{value}`\n"
            content += "\n"
        
        if result.get('article_list'):
            article = result['article_list']
            content += "### 文章列表\n\n"
            content += f"- **选择器**: `{article['selector']}`\n"
            content += f"- **文章数量**: {article['count']}\n\n"
            
            if article.get('sample_element'):
                content += "#### 文章元素结构\n\n"
                sample = article['sample_element']
                
                if sample.get('title'):
                    content += f"**标题**:\n"
                    content += f"- 选择器: `{sample['title']['selector']}`\n"
                    content += f"- 示例文本: `{sample['title']['text']}`\n\n"
                
                if sample.get('link'):
                    content += f"**链接**:\n"
                    content += f"- 选择器: `{sample['link']['selector']}`\n"
                    content += f"- 示例URL: `{sample['link']['href']}`\n\n"
                
                if sample.get('date'):
                    content += f"**日期**:\n"
                    content += f"- 选择器: `{sample['date']['selector']}`\n"
                    if sample['date'].get('text'):
                        content += f"- 文本: `{sample['date']['text']}`\n"
                    if sample['date'].get('datetime'):
                        content += f"- datetime属性: `{sample['date']['datetime']}`\n"
                    content += "\n"
                
                if sample.get('summary'):
                    content += f"**摘要**:\n"
                    content += f"- 选择器: `{sample['summary']['selector']}`\n"
                    content += f"- 示例文本: `{sample['summary']['text']}`\n\n"
        
        content += "---\n\n"
    
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✓ 标记文档已生成: {doc_path}")


if __name__ == "__main__":
    asyncio.run(main())

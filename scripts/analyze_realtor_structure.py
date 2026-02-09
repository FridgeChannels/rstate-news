"""
分析Realtor.com页面结构，提取文章元素的实际选择器
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


async def analyze_realtor_structure():
    """分析Realtor.com的页面结构"""
    url = "https://www.realtor.com/news/real-estate-news/"
    output_dir = Path(__file__).parent.parent / "analysis" / "realtor"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("Realtor.com 页面结构分析")
    print("=" * 70)
    print(f"URL: {url}\n")
    
    result = {
        'url': url,
        'analyzed_at': datetime.now().isoformat(),
        'article_container_selectors': [],
        'title_selectors': [],
        'link_selectors': [],
        'summary_selectors': [],
        'date_selectors': [],
        'sample_articles': [],
        'recommended_selectors': {}
    }
    
    playwright = await async_playwright().start()
    browser = None
    context = None
    page = None
    
    try:
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
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        print("📍 访问页面...")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        print("  ✓ 页面已加载")
        
        # 等待页面完全加载
        await asyncio.sleep(5)
        
        # 处理可能的弹窗
        try:
                close_selectors = [
                    "button[aria-label*='close' i]",
                    "button[aria-label*='Close' i]",
                    ".close-button",
                    "[data-testid='close']",
                    ".modal-close",
                    ".cookie-consent button"
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
        
        # 获取HTML内容
        html_content = await page.content()
        
        # 保存完整HTML
        html_file = output_dir / "realtor_full_dom.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  ✓ HTML已保存: {html_file}")
        
        # 使用BeautifulSoup分析DOM
        soup = BeautifulSoup(html_content, 'html.parser')
        
        print("\n🔍 分析文章结构...")
        
        # 尝试找到文章容器
        # 根据用户提供的HTML，文章容器可能是 div.sc-1ri3r0p-0 或包含Cardstyles的元素
        article_containers = []
        
        # 方法1: 查找包含特定类名的div
        potential_containers = soup.find_all('div', class_=lambda x: x and ('sc-1ri3r0p-0' in str(x) or 'Cardstyles' in str(x)))
        article_containers.extend(potential_containers)
        
        # 方法2: 查找包含新闻链接的容器
        news_links = soup.find_all('a', href=lambda x: x and '/news/real-estate-news/' in str(x))
        for link in news_links[:10]:  # 只取前10个
            container = link.find_parent('div', class_=lambda x: x and ('card' in str(x).lower() or 'article' in str(x).lower()))
            if container and container not in article_containers:
                article_containers.append(container)
        
        print(f"  找到 {len(article_containers)} 个潜在文章容器")
        
        # 分析前5个容器的结构
        for i, container in enumerate(article_containers[:5]):
            print(f"\n  📄 分析文章容器 {i+1}:")
            
            article_info = {
                    'container_index': i,
                    'container_classes': container.get('class', []),
                    'container_id': container.get('id'),
                    'title': None,
                    'title_selector': None,
                    'link': None,
                    'link_selector': None,
                    'summary': None,
                    'summary_selector': None,
                'date': None,
                'date_selector': None
            }
            
            # 分析标题
            title_elements = []
            # 查找 h3.sc-1ewhvwh-0
            h3_elements = container.find_all('h3', class_=lambda x: x and 'sc-1ewhvwh-0' in str(x))
            title_elements.extend(h3_elements)
            # 查找 h3[font-weight="bold"]
            h3_bold = container.find_all('h3', attrs={'font-weight': 'bold'})
            title_elements.extend(h3_bold)
            # 查找所有h3
            if not title_elements:
                title_elements = container.find_all('h3')
            
            if title_elements:
                title_elem = title_elements[0]
                article_info['title'] = title_elem.get_text(strip=True)
                article_info['title_selector'] = _build_selector(title_elem)
                print(f"    标题: {article_info['title'][:60]}...")
                print(f"    标题选择器: {article_info['title_selector']}")
            
            # 分析链接
            link_elements = []
            # 查找包含 /news/real-estate-news/ 的链接
            links = container.find_all('a', href=lambda x: x and '/news/real-estate-news/' in str(x))
            link_elements.extend(links)
            # 查找标题内的链接
            if title_elements:
                title_links = title_elements[0].find_all('a')
                link_elements.extend(title_links)
            
            if link_elements:
                link_elem = link_elements[0]
                article_info['link'] = link_elem.get('href', '')
                article_info['link_selector'] = _build_selector(link_elem)
                print(f"    链接: {article_info['link']}")
                print(f"    链接选择器: {article_info['link_selector']}")
            
            # 分析摘要
            summary_elements = []
            # 查找 p.dsOTPE 或包含 dsOTPE 的p
            p_elements = container.find_all('p', class_=lambda x: x and 'dsOTPE' in str(x))
            summary_elements.extend(p_elements)
            # 查找 card-content 内的段落
            card_content = container.find('div', class_=lambda x: x and 'card-content' in str(x).lower())
            if card_content:
                p_in_content = card_content.find_all('p')
                summary_elements.extend(p_in_content)
            
            if summary_elements:
                summary_elem = summary_elements[0]
                article_info['summary'] = summary_elem.get_text(strip=True)
                article_info['summary_selector'] = _build_selector(summary_elem)
                print(f"    摘要: {article_info['summary'][:60]}...")
                print(f"    摘要选择器: {article_info['summary_selector']}")
            
            # 分析日期
            date_elements = []
            # 查找 time 元素
            time_elements = container.find_all('time')
            date_elements.extend(time_elements)
            # 查找包含日期的元素
            date_patterns = ['date', 'time', 'published', 'publish']
            for pattern in date_patterns:
                date_elems = container.find_all(attrs={'class': lambda x: x and pattern in str(x).lower()})
                date_elements.extend(date_elems)
            
            if date_elements:
                date_elem = date_elements[0]
                article_info['date'] = date_elem.get_text(strip=True) or date_elem.get('datetime', '')
                article_info['date_selector'] = _build_selector(date_elem)
                print(f"    日期: {article_info['date']}")
                print(f"    日期选择器: {article_info['date_selector']}")
            
            result['sample_articles'].append(article_info)
        
        # 汇总推荐的选择器
        print("\n📋 推荐的选择器:")
            
        # 文章容器选择器
        if article_containers:
            container_classes = set()
            for container in article_containers[:5]:
                classes = container.get('class', [])
                container_classes.update(classes)
            
            # 找出最常见的类名模式
            recommended_container = None
            for cls in container_classes:
                if 'sc-' in cls or 'Card' in cls:
                    recommended_container = f"div.{cls}" if cls else "div[class*='Card']"
                    break
            
            if not recommended_container:
                recommended_container = "div[class*='card']"
            
            result['recommended_selectors']['article_container'] = recommended_container
            print(f"  文章容器: {recommended_container}")
        
        # 标题选择器
        title_selectors = [a['title_selector'] for a in result['sample_articles'] if a.get('title_selector')]
        if title_selectors:
            # 找出最常见的
            recommended_title = title_selectors[0]
            result['recommended_selectors']['title'] = recommended_title
            print(f"  标题: {recommended_title}")
        
        # 链接选择器
        link_selectors = [a['link_selector'] for a in result['sample_articles'] if a.get('link_selector')]
        if link_selectors:
            recommended_link = "a[href*='/news/real-estate-news/']"  # 更通用的选择器
            result['recommended_selectors']['link'] = recommended_link
            print(f"  链接: {recommended_link}")
        
        # 摘要选择器
        summary_selectors = [a['summary_selector'] for a in result['sample_articles'] if a.get('summary_selector')]
        if summary_selectors:
            recommended_summary = summary_selectors[0]
            result['recommended_selectors']['summary'] = recommended_summary
            print(f"  摘要: {recommended_summary}")
        
        # 日期选择器
        date_selectors = [a['date_selector'] for a in result['sample_articles'] if a.get('date_selector')]
        if date_selectors:
            recommended_date = date_selectors[0] if date_selectors else "time"
            result['recommended_selectors']['date'] = recommended_date
            print(f"  日期: {recommended_date}")
        
        # 保存分析结果
        json_file = output_dir / "realtor_analysis.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n  ✓ 分析结果已保存: {json_file}")
        
        print("\n" + "=" * 70)
        print("✅ 分析完成！")
        print("=" * 70)
        
        return result
        
    except Exception as e:
        print(f"\n❌ 分析失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return result
    finally:
        if page:
            try:
                await page.close()
            except:
                pass
        if context:
            try:
                await context.close()
            except:
                pass
        if browser:
            try:
                await browser.close()
            except:
                pass
        if playwright:
            try:
                await playwright.stop()
            except:
                pass
    
    return result


def _build_selector(element):
    """构建元素的选择器"""
    if not element:
        return None
    
    # 优先使用ID
    if element.get('id'):
        return f"{element.name}#{element.get('id')}"
    
    # 使用类名
    classes = element.get('class', [])
    if classes:
        class_str = '.'.join(classes)
        return f"{element.name}.{class_str}"
    
    # 使用属性
    if element.get('data-testid'):
        return f"{element.name}[data-testid='{element.get('data-testid')}']"
    
    # 使用部分类名匹配（对于动态类名）
    if classes:
        # 找出包含特殊字符的类名（通常是动态生成的）
        for cls in classes:
            if 'sc-' in cls or '__' in cls:
                return f"{element.name}[class*='{cls.split('-')[0] if '-' in cls else cls[:5]}']"
    
    # 回退到标签名
    return element.name


if __name__ == "__main__":
    asyncio.run(analyze_realtor_structure())

"""
智能分析DOM文件，从JSON数据和HTML中提取元素信息
"""
import json
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup


def extract_json_data(html_content):
    """从HTML中提取JSON数据（如Next.js的__NEXT_DATA__）"""
    json_data = {}
    
    # 查找 __NEXT_DATA__ 脚本
    next_data_match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html_content, re.DOTALL)
    if next_data_match:
        try:
            json_data['__NEXT_DATA__'] = json.loads(next_data_match.group(1))
        except:
            pass
    
    # 查找其他JSON数据
    json_matches = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html_content, re.DOTALL)
    for match in json_matches:
        try:
            data = json.loads(match)
            if isinstance(data, dict):
                json_data.update(data)
        except:
            pass
    
    return json_data


def analyze_newsbreak_dom(html_content):
    """专门分析Newsbreak的DOM"""
    result = {
        'zipcode_input': None,
        'article_list': None,
    }
    
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 从JSON数据中提取文章信息
    json_data = extract_json_data(html_content)
    if '__NEXT_DATA__' in json_data:
        next_data = json_data['__NEXT_DATA__']
        if 'props' in next_data and 'pageProps' in next_data['props']:
            page_props = next_data['props']['pageProps']
            if 'feed' in page_props:
                feed = page_props['feed']
                if feed and len(feed) > 0:
                    result['article_list'] = {
                        'source': 'json_data',
                        'count': len(feed),
                        'sample_articles': feed[:3],
                        'note': '文章数据在__NEXT_DATA__ JSON中，需要通过JavaScript渲染或直接解析JSON'
                    }
    
    # 查找zipcode输入框
    zipcode_input = soup.find('input', {
        'type': lambda x: x in ['text', 'search'],
        'placeholder': lambda x: x and ('zip' in x.lower() or 'postal' in x.lower() or 'location' in x.lower())
    })
    if not zipcode_input:
        zipcode_input = soup.find('input', {'id': lambda x: x and 'search' in x.lower()})
    
    if zipcode_input:
        result['zipcode_input'] = {
            'tag': zipcode_input.name,
            'attributes': dict(zipcode_input.attrs),
            'selector': f"input#{zipcode_input.get('id', '')}" if zipcode_input.get('id') else f"input[placeholder*='zip' i]"
        }
    
    return result


def analyze_patch_dom(html_content):
    """专门分析Patch的DOM"""
    result = {
        'zipcode_input': None,
        'article_list': None,
    }
    
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Zipcode输入框（已找到）
    zipcode_input = soup.find('input', {'id': 'find-your-patch'})
    if zipcode_input:
        result['zipcode_input'] = {
            'tag': zipcode_input.name,
            'attributes': dict(zipcode_input.attrs),
            'selector': '#find-your-patch'
        }
    
    # 文章列表 - 查找包含链接的div或article
    articles = soup.find_all(['article', 'div'], class_=lambda x: x and any(
        word in ' '.join(x).lower() for word in ['article', 'story', 'post', 'card']
    ))
    
    articles_with_links = []
    for article in articles:
        if article.find('a', href=True):
            articles_with_links.append(article)
    
    if len(articles_with_links) >= 3:
        first = articles_with_links[0]
        result['article_list'] = {
            'selector': f"{first.name}.{first.get('class', [])[0] if first.get('class') else ''}",
            'count': len(articles_with_links),
        }
        
        # 分析结构
        title_elem = first.find(['h1', 'h2', 'h3', 'h4']) or first.find('a')
        if title_elem:
            result['article_list']['title_selector'] = title_elem.name
            result['article_list']['title_example'] = title_elem.get_text(strip=True)[:100]
        
        link_elem = first.find('a', href=True)
        if link_elem:
            result['article_list']['link_selector'] = 'a[href]'
            result['article_list']['link_example'] = link_elem.get('href', '')
    
    return result


def analyze_realtor_dom(html_content):
    """专门分析Realtor.com的DOM"""
    result = {
        'article_list': None,
    }
    
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 查找文章 - Realtor.com通常使用article标签
    articles = soup.find_all('article')
    if len(articles) >= 3:
        first = articles[0]
        result['article_list'] = {
            'selector': 'article',
            'count': len(articles),
        }
        
        title_elem = first.find(['h1', 'h2', 'h3', 'h4'])
        if title_elem:
            result['article_list']['title_selector'] = title_elem.name
            result['article_list']['title_example'] = title_elem.get_text(strip=True)[:100]
        
        link_elem = first.find('a', href=True)
        if link_elem:
            result['article_list']['link_selector'] = 'a[href]'
            result['article_list']['link_example'] = link_elem.get('href', '')
    
    return result


def main():
    """主函数"""
    dom_dir = Path(__file__).parent.parent / "analysis" / "dom_structures"
    
    print("="*70)
    print("智能分析DOM文件")
    print("="*70)
    
    # 分析Newsbreak
    newsbreak_file = dom_dir / "newsbreak_full_dom.html"
    if newsbreak_file.exists():
        print("\n分析 Newsbreak...")
        with open(newsbreak_file, 'r', encoding='utf-8') as f:
            html = f.read()
        result = analyze_newsbreak_dom(html)
        
        # 保存结果
        with open(dom_dir / "newsbreak_intelligent_analysis.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("  ✓ Newsbreak分析完成")
    
    # 分析Patch
    patch_file = dom_dir / "patch_full_dom.html"
    if patch_file.exists():
        print("\n分析 Patch...")
        with open(patch_file, 'r', encoding='utf-8') as f:
            html = f.read()
        result = analyze_patch_dom(html)
        
        with open(dom_dir / "patch_intelligent_analysis.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("  ✓ Patch分析完成")
    
    # 分析Realtor（如果文件存在）
    realtor_file = dom_dir / "realtor_full_dom.html"
    if realtor_file.exists():
        print("\n分析 Realtor.com...")
        with open(realtor_file, 'r', encoding='utf-8') as f:
            html = f.read()
        result = analyze_realtor_dom(html)
        
        with open(dom_dir / "realtor_intelligent_analysis.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("  ✓ Realtor.com分析完成")
    
    print("\n" + "="*70)
    print("✅ 智能分析完成！")
    print("="*70)


if __name__ == "__main__":
    main()

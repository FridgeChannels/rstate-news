"""
分析已保存的DOM文件，标记关键元素位置
"""
import json
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup


WEBSITES = {
    'newsbreak': {
        'name': 'Newsbreak',
        'needs_zipcode': True,
        'html_file': 'newsbreak_full_dom.html',
    },
    'patch': {
        'name': 'Patch',
        'needs_zipcode': True,
        'html_file': 'patch_full_dom.html',
    },
    'realtor': {
        'name': 'Realtor.com',
        'needs_zipcode': False,
        'html_file': 'realtor_full_dom.html',
    },
    'redfin': {
        'name': 'Redfin',
        'needs_zipcode': False,
        'html_file': 'redfin_full_dom.html',
    },
    'nar': {
        'name': 'NAR',
        'needs_zipcode': False,
        'html_file': 'nar_full_dom.html',
    },
    'freddiemac': {
        'name': 'Freddie Mac',
        'needs_zipcode': False,
        'html_file': 'freddiemac_full_dom.html',
    },
}


def analyze_dom_file(website_key, website_info, dom_dir):
    """分析单个DOM文件"""
    name = website_info['name']
    needs_zipcode = website_info['needs_zipcode']
    html_file = dom_dir / website_info['html_file']
    
    if not html_file.exists():
        print(f"  ⚠️  {name}: DOM文件不存在: {html_file}")
        return None
    
    print(f"\n{'='*70}")
    print(f"分析: {name}")
    print(f"{'='*70}\n")
    
    result = {
        'name': name,
        'website_key': website_key,
        'needs_zipcode': needs_zipcode,
        'analyzed_at': datetime.now().isoformat(),
        'zipcode_input': None,
        'article_list': None,
        'sample_articles': [],
    }
    
    try:
        # 读取HTML
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 分析zipcode输入框
        if needs_zipcode:
            print("🔍 查找Zipcode输入框...")
            zipcode_patterns = [
                {'tag': 'input', 'attrs': {'type': 'text', 'placeholder': lambda x: x and 'zip' in x.lower()}},
                {'tag': 'input', 'attrs': {'type': 'text', 'placeholder': lambda x: x and 'postal' in x.lower()}},
                {'tag': 'input', 'attrs': {'name': lambda x: x and 'zip' in x.lower()}},
                {'tag': 'input', 'attrs': {'id': lambda x: x and 'zip' in x.lower()}},
                {'tag': 'input', 'attrs': {'type': 'search'}},
            ]
            
            for pattern in zipcode_patterns:
                elements = soup.find_all(pattern['tag'], pattern['attrs'])
                if elements:
                    elem = elements[0]
                    # 构建选择器
                    attrs_list = []
                    for k, v in elem.attrs.items():
                        if k != 'class':
                            if isinstance(v, list):
                                v = ' '.join(v)
                            attrs_list.append(f'{k}="{v}"')
                    selector = f"input[{', '.join(attrs_list)}]" if attrs_list else "input"
                    
                    result['zipcode_input'] = {
                        'tag': elem.name,
                        'attributes': dict(elem.attrs),
                        'selector': selector,
                    }
                    print(f"  ✓ 找到Zipcode输入框")
                    print(f"    标签: {elem.name}")
                    print(f"    属性: {elem.attrs}")
                    break
        
        # 分析文章列表
        print("\n🔍 查找文章列表...")
        article_patterns = [
            {'tag': 'article', 'attrs': {}},
            {'tag': 'div', 'attrs': {'class': lambda x: x and 'article' in ' '.join(x).lower()}},
            {'tag': 'div', 'attrs': {'class': lambda x: x and 'news' in ' '.join(x).lower()}},
            {'tag': 'div', 'attrs': {'class': lambda x: x and 'story' in ' '.join(x).lower()}},
            {'tag': 'div', 'attrs': {'class': lambda x: x and 'card' in ' '.join(x).lower()}},
        ]
        
        for pattern in article_patterns:
            attrs = pattern.get('attrs', {})
            if attrs:
                elements = soup.find_all(pattern['tag'], attrs, limit=20)
            else:
                elements = soup.find_all(pattern['tag'], limit=20)
            if len(elements) >= 3:
                # 检查是否包含链接（文章通常有链接）
                articles_with_links = []
                for elem in elements:
                    if elem.find('a', href=True):
                        articles_with_links.append(elem)
                
                if len(articles_with_links) >= 3:
                    print(f"  ✓ 找到 {len(articles_with_links)} 个文章元素")
                    
                    # 分析第一个文章
                    first_article = articles_with_links[0]
                    
                    article_info = {
                        'selector': f"{pattern['tag']}.{first_article.get('class', [])[0] if first_article.get('class') else ''}",
                        'count': len(articles_with_links),
                    }
                    
                    # 查找标题
                    title_elem = first_article.find(['h1', 'h2', 'h3', 'h4'])
                    if not title_elem:
                        title_elem = first_article.find('a')
                    if title_elem:
                        article_info['title_selector'] = title_elem.name
                        article_info['title_example'] = title_elem.get_text(strip=True)[:100]
                    
                    # 查找链接
                    link_elem = first_article.find('a', href=True)
                    if link_elem:
                        article_info['link_selector'] = 'a[href]'
                        article_info['link_example'] = link_elem.get('href', '')
                    
                    # 查找日期
                    date_elem = first_article.find(['time', 'span'], attrs={'class': lambda x: x and 'date' in ' '.join(x).lower()})
                    if not date_elem:
                        date_elem = first_article.find('time')
                    if date_elem:
                        article_info['date_selector'] = date_elem.name
                        article_info['date_example'] = date_elem.get('datetime') or date_elem.get_text(strip=True)
                    
                    # 查找摘要
                    summary_elem = first_article.find(['p', 'div'], attrs={'class': lambda x: x and any(word in ' '.join(x).lower() for word in ['summary', 'excerpt', 'description'])})
                    if summary_elem:
                        article_info['summary_selector'] = f"{summary_elem.name}.{summary_elem.get('class', [])[0] if summary_elem.get('class') else ''}"
                        article_info['summary_example'] = summary_elem.get_text(strip=True)[:200]
                    
                    result['article_list'] = article_info
                    
                    # 保存前3个文章的HTML结构
                    for i, article in enumerate(articles_with_links[:3]):
                        result['sample_articles'].append({
                            'index': i + 1,
                            'html': str(article.prettify())[:5000],  # 限制长度
                        })
                    
                    break
        
        print(f"\n✅ {name} 分析完成")
        return result
        
    except Exception as e:
        print(f"❌ {name} 分析失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def generate_markup_document(all_results, output_dir):
    """生成元素标记文档"""
    doc_path = output_dir / "ELEMENT_MARKUP.md"
    
    content = f"""# 网站元素标记文档

本文档记录了所有网站的关键元素位置，用于指导scraper开发。

**生成时间**: {datetime.now().isoformat()}

---

"""
    
    for website_key, result in all_results.items():
        if not result:
            continue
        
        content += f"## {result['name']}\n\n"
        content += f"**需要Zipcode**: {'是' if result['needs_zipcode'] else '否'}\n\n"
        
        if result.get('zipcode_input'):
            zipcode = result['zipcode_input']
            content += "### Zipcode输入框\n\n"
            content += f"- **标签**: `{zipcode['tag']}`\n"
            content += f"- **选择器**: `{zipcode.get('selector', 'N/A')}`\n"
            if zipcode.get('attributes'):
                content += f"- **属性**:\n"
                for key, value in zipcode['attributes'].items():
                    if isinstance(value, list):
                        value = ' '.join(value)
                    content += f"  - `{key}`: `{value}`\n"
            content += "\n"
        
        if result.get('article_list'):
            article = result['article_list']
            content += "### 文章列表\n\n"
            content += f"- **选择器**: `{article.get('selector', 'N/A')}`\n"
            content += f"- **文章数量**: {article.get('count', 0)}\n\n"
            
            if article.get('title_selector'):
                content += f"**标题**:\n"
                content += f"- 选择器: `{article['title_selector']}`\n"
                content += f"- 示例: `{article.get('title_example', 'N/A')}`\n\n"
            
            if article.get('link_selector'):
                content += f"**链接**:\n"
                content += f"- 选择器: `{article['link_selector']}`\n"
                content += f"- 示例: `{article.get('link_example', 'N/A')[:80]}`\n\n"
            
            if article.get('date_selector'):
                content += f"**日期**:\n"
                content += f"- 选择器: `{article['date_selector']}`\n"
                content += f"- 示例: `{article.get('date_example', 'N/A')}`\n\n"
            
            if article.get('summary_selector'):
                content += f"**摘要**:\n"
                content += f"- 选择器: `{article['summary_selector']}`\n"
                content += f"- 示例: `{article.get('summary_example', 'N/A')[:100]}`\n\n"
        
        content += "---\n\n"
    
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n  ✓ 标记文档已生成: {doc_path}")


def main():
    """主函数"""
    dom_dir = Path(__file__).parent.parent / "analysis" / "dom_structures"
    
    print("="*70)
    print("分析已保存的DOM文件")
    print("="*70)
    print(f"DOM目录: {dom_dir}\n")
    
    all_results = {}
    
    for website_key, website_info in WEBSITES.items():
        result = analyze_dom_file(website_key, website_info, dom_dir)
        if result:
            all_results[website_key] = result
            
            # 保存单个网站的分析结果
            json_file = dom_dir / f"{website_key}_analysis.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"  ✓ 分析结果已保存: {json_file.name}\n")
    
    # 生成标记文档
    generate_markup_document(all_results, dom_dir)
    
    print("\n" + "="*70)
    print("✅ 所有DOM分析完成！")
    print("="*70)


if __name__ == "__main__":
    main()

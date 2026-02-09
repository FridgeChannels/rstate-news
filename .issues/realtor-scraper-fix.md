# Realtor.com采集器修复：更新选择器以匹配实际DOM结构

**Type:** `bug`  
**Priority:** `normal`  
**Effort:** `medium`

## TL;DR

Realtor.com的页面结构已更新，当前使用的通用选择器无法正确匹配文章元素。需要根据实际DOM结构更新选择器，确保能正确提取标题、链接和摘要。

## Current State

- 使用通用选择器：`article`, `.article-card`, `.news-item`等
- 无法找到或正确提取文章元素
- 代码中有TODO注释提到需要重新保存DOM并分析结构

## Expected Outcome

根据实际DOM结构更新选择器：

1. **文章容器选择器**：
   - 主容器：`div.sc-1ri3r0p-0` 或 `div[class*="sc-1ri3r0p-0"]`
   - 卡片容器：`div.Cardstyles__StyledCard-rui__sc-42t194-0` 或 `div[class*="Cardstyles"]`

2. **标题选择器**：
   - `h3.sc-1ewhvwh-0` 或 `h3[class*="sc-1ewhvwh-0"]`
   - 备选：`h3[font-weight="bold"]`

3. **链接选择器**：
   - 标题链接：`a[href*="/news/real-estate-news/"]`
   - 在标题h3内的链接

4. **摘要选择器**：
   - `p.base__StyledType-rui__sc-18muj27-0.dsOTPE` 或 `p[class*="dsOTPE"]`
   - 在card-content内的段落

5. **提取逻辑**：
   - 从标题h3中提取文本和链接
   - 从card-content中提取摘要段落
   - 处理相对URL转换为绝对URL

## Relevant Files

- `scrapers/realtor_scraper.py` - 更新`_scrape_real_estate_news`和`_extract_article_data`方法
- `scrapers/realtor_scraper.py` - 可能需要重写`extract_article_data_robust`方法以使用Realtor特定选择器

## Implementation Notes

- 使用实际发现的类名（如`sc-1ri3r0p-0`, `sc-1ewhvwh-0`等）
- 同时保留通用fallback选择器作为备选
- 处理动态类名（使用`[class*=""]`部分匹配）
- 确保URL正确转换（相对路径转绝对路径）

## Risks

- Realtor.com可能使用动态类名（hash-based），类名可能变化
- 需要测试多个页面确保选择器稳定性
- Cloudflare验证可能影响页面加载

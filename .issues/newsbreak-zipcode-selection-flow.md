# Newsbreak: 改进Zipcode选择和分类采集流程

**Type:** `improvement`  
**Priority:** `normal`  
**Effort:** `medium`

## TL;DR

当前Newsbreak scraper直接访问搜索URL，需要改为：先通过locations页面选择zipcode对应的城市，然后分别采集business、education、poi_housing三个分类的内容，去重后只保留24小时内的文章。

## Current State

- 直接访问 `https://www.newsbreak.com/search?q={zipcode}`
- 从JSON数据中提取文章
- 没有分类过滤（business/education/housing）
- 没有24小时时间限制

## Expected Outcome

1. **Zipcode选择流程**：
   - 访问 `https://www.newsbreak.com/locations`
   - 找到输入框：`input[placeholder="City name or zip code"]`
   - 输入zipcode
   - 等待自动完成建议出现：`.autocomplete__list-item a.autocomplete__btn`
   - 点击第一个建议项
   - 导航到城市页面（如 `/beverly-hills-ca`）

2. **分类采集**：
   - 分别访问三个URL：
     - `{city_url}-business` (商业)
     - `{city_url}-education` (教育)  
     - `{city_url}-poi_housing` (房地产)
   - 每个分类采集文章

3. **数据处理**：
   - 合并三个分类的结果
   - 按URL去重
   - 只保留近24小时内的文章（超过1天的丢弃）

4. **文章提取**：
   - 从提供的HTML结构中提取：
     - 标题：`h3.text-xl`
     - 链接：`a[aria-label*="/"]` 的href
     - 摘要：`p.text-base.text-gray-light`
     - 时间：相对时间文本（如"5小时"）
     - 城市：从location链接中提取

## Relevant Files

- `scrapers/newsbreak_scraper.py` - 主要修改文件
- `utils/data_cleaner.py` - 可能需要添加24小时过滤逻辑

## Implementation Notes

- 需要处理自动完成建议的等待和选择
- 时间解析需要处理相对时间（"5小时"、"1天"等）转换为绝对时间
- 去重逻辑可以基于URL
- 三个分类的采集可以并行执行以提高效率

## Risks

- 自动完成建议的DOM结构可能变化
- 相对时间解析需要处理多种格式
- 需要确保三个分类的URL格式正确

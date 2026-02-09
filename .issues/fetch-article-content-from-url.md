# 访问文章链接获取真实内容

**Type:** `improvement`  
**Priority:** `high`  
**Effort:** `medium`

## TL;DR

当前所有scraper只从列表页面提取摘要，`content`和`content_summary`都不是链接里对应的真实文章内容。需要添加流程：采集到文章URL后，访问每个链接获取真实文章内容。

## Current State

- 所有scraper（Newsbreak, Patch等）都只从列表页面提取摘要
- `content`和`content_summary`字段都是从列表页面的摘要提取的（如`p.text-base.text-gray-light`）
- 用户发现这些内容不是链接里对应的真实文章内容
- 示例：`output/raw_news_20260128_023754.json`中的文章，content都是列表页摘要，不是实际文章内容

## Expected Outcome

1. **添加文章详情页访问流程**：
   - 在scraper采集到文章URL后，访问每个链接
   - 从详情页提取完整文章内容
   - 更新`content`字段为真实文章内容
   - 保留`content_summary`为摘要（如果详情页有）

2. **实现方式**：
   - 在`BaseScraper`或`RobustScraperMixin`中添加`_fetch_article_content(url)`方法
   - 各scraper可以覆盖此方法以适配不同网站结构
   - 使用Playwright访问文章URL并提取内容

3. **性能考虑**：
   - 可以并行访问多个文章链接（使用`asyncio.gather`）
   - 添加超时和重试机制
   - 如果访问失败，保留原有的摘要作为fallback

4. **内容提取策略**：
   - 优先提取文章正文（`article`, `.content`, `.post-body`等选择器）
   - 清理HTML标签，保留纯文本
   - 如果提取失败，使用列表页摘要作为fallback

## Relevant Files

- `scrapers/base_scraper.py` - 添加基础的文章内容获取方法
- `scrapers/robust_scraper_mixin.py` - 可能添加通用的内容提取逻辑
- `scrapers/newsbreak_scraper.py` - 实现Newsbreak特定的内容提取
- `scrapers/patch_scraper.py` - 实现Patch特定的内容提取
- `scrapers/*_scraper.py` - 其他scraper也需要实现
- `utils/data_cleaner.py` - 可能需要更新内容清理逻辑

## Implementation Notes

- 需要考虑不同网站的文章页面结构差异
- 添加错误处理：如果访问详情页失败，保留列表页摘要
- 性能优化：可以批量并行访问，但要控制并发数避免过载
- 可能需要处理反爬虫机制（如Newsbreak可能有）
- 建议先实现一个scraper（如Patch）作为参考，再推广到其他scraper

## Risks

- **性能影响**：访问每个链接会显著增加采集时间
- **反爬虫**：某些网站可能检测到频繁访问详情页
- **网站结构变化**：不同网站的文章页面结构差异很大
- **失败率**：部分链接可能无法访问，需要graceful fallback

## Implementation Plan

详细实现计划请参考：`.issues/fetch-article-content-implementation-plan.md`

## Decisions Made

- ✅ 集成位置：在`ScraperCoordinator.scrape_source()`中批量处理，不影响现有scraper
- ✅ 并发控制：使用`asyncio.Semaphore(3)`控制3个并发
- ✅ 优先级：trafilatura → newspaper3k → 保留列表页摘要
- ✅ 内容更新：成功时更新`content`字段，替换`content_summary`，不更新`publish_date`
- ✅ 超时设置：30秒超时，不重试
- ✅ 默认开启，不需要配置开关

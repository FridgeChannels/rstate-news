# 去重功能改进

**Type:** `improvement`  
**Priority:** `normal`  
**Effort:** `medium`

## TL;DR

当前系统缺少全局去重机制，导致大量重复内容被插入数据库。需要在多个层面实现去重：采集阶段合并去重、数据库插入前检查、以及数据库唯一约束。

## Current State

- **Newsbreak scraper内部**：有`_deduplicate_articles()`方法，仅基于URL去重，但只在scraper内部生效
- **主流程合并**：不同scraper采集的结果在`all_raw_news`中合并时没有去重
- **数据库插入**：`insert_raw_news()`直接插入，没有检查URL是否已存在
- **数据库约束**：`play_raw_news`表没有URL唯一约束，允许重复插入

## Expected Outcome

1. **主流程去重**：
   - 在`run_scraping_task`中，合并所有scraper结果后统一去重
   - 基于URL去重（保留第一次出现的记录）
   - 在插入数据库前完成去重

2. **数据库插入前检查**：
   - 在`insert_raw_news`中，查询已存在的URL
   - 过滤掉已存在的记录，只插入新记录
   - 记录跳过数量日志

3. **数据库唯一约束**（可选）：
   - 在`play_raw_news`表添加URL唯一索引
   - 或使用`(url, source_id)`组合唯一约束（同一URL可能来自不同源）

## Relevant Files

- `main.py` - 在`run_scraping_task`中添加全局去重逻辑
- `database/supabase_client.py` - 在`insert_raw_news`中添加URL存在性检查
- `database/migrations/000_complete_schema.sql` - 添加唯一约束（如需要）

## Implementation Notes

- 去重策略：基于URL（标准化后，去除查询参数、fragment等）
- 性能考虑：批量查询已存在URL，避免逐条检查
- 日志记录：记录去重数量、跳过数量
- 兼容性：保持现有scraper内部去重逻辑（双重保护）

## Risks

- 批量查询已存在URL可能影响性能（需要索引优化）
- URL标准化规则需要统一（http/https、末尾斜杠、查询参数等）
- 如果使用唯一约束，需要处理插入冲突错误

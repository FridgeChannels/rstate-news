# Patch: 修复浏览器意外关闭导致部分zipcode采集失败

**Type:** `bug`  
**Priority:** `high`  
**Effort:** `medium`

## TL;DR

Patch scraper在采集90210、94102、60601时遇到"Target page, context or browser has been closed"错误，导致返回0篇文章。只有10001成功获取10篇文章。需要分析并修复浏览器意外关闭的问题。

## Current State

- ✅ 10001: 成功获取10篇文章
- ❌ 90210: 0篇文章 - 浏览器关闭错误
- ❌ 94102: 0篇文章 - 浏览器关闭错误  
- ❌ 60601: 0篇文章 - 浏览器关闭错误

**错误日志**:
```
WARNING - Patch: domcontentloaded失败，尝试commit: Target page, context or browser has been closed
ERROR - Patch: 页面导航完全失败: Target page, context or browser has been closed
```

## Expected Outcome

所有4个zipcode（90210, 10001, 94102, 60601）都能成功获取内容，至少每个zipcode返回1篇以上文章。

## Root Cause Analysis Needed

1. **浏览器生命周期管理**：
   - 检查浏览器/context是否在导航前被意外关闭
   - 验证页面创建和浏览器状态检查逻辑

2. **导航时机问题**：
   - 步骤5中从自动完成建议获取URL后导航时，浏览器可能已关闭
   - 可能的原因：等待时间过长、页面交互导致浏览器崩溃

3. **错误处理**：
   - 当前错误处理可能不够健壮，需要添加浏览器状态验证和重试机制

## Relevant Files

- `scrapers/patch_scraper.py` - 主要修复文件（特别是`_scrape_zipcode_news`方法）
- `scrapers/base_scraper.py` - 浏览器生命周期管理
- `scrapers/patch_scraper.py:398-422` - 导航逻辑和错误处理

## Implementation Notes

- 在导航前验证浏览器和页面状态
- 添加浏览器状态检查和自动恢复机制
- 改进错误处理：浏览器关闭时自动重新创建
- 考虑为每个zipcode使用独立的浏览器实例，避免状态污染
- 添加更详细的调试日志，记录浏览器状态变化

## Risks

- 修复可能影响已成功的10001采集
- 需要确保浏览器资源正确释放，避免内存泄漏
- 多个zipcode连续采集时的状态管理

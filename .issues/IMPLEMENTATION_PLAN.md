# Issue修复和功能改进实现计划

**Overall Progress:** `100%` ✅

## TLDR

修复Patch scraper的浏览器关闭错误，改进Newsbreak scraper的zipcode选择和分类采集流程。Patch问题通过添加浏览器状态检查和重试机制解决；Newsbreak改为通过locations页面选择城市，并行采集三个分类（business/education/poi_housing），合并后去重并过滤24小时内文章。

## Critical Decisions

关键架构/实现决策：
- **Patch重试策略**: 导航失败时最多重试2次，不添加备用策略 - 简化实现，避免过度复杂化
- **Newsbreak时间过滤**: 在scraper内部根据当前时间直接判断24小时，不修改全局配置 - 保持灵活性，不影响其他scraper
- **Newsbreak并行采集**: 三个分类并行采集以提高效率 - 减少总执行时间
- **去重范围**: 仅在Newsbreak scraper内部，合并三个分类结果后去重 - 符合需求，不影响其他逻辑

## Tasks:

### Issue 1: Patch浏览器关闭错误修复

- [ ] 🟩 **Step 1: 添加浏览器状态检查**
  - [ ] 🟩 在`patch_scraper.py:398`导航前添加浏览器/context/page状态验证
  - [ ] 🟩 创建辅助方法`_verify_browser_state()`检查浏览器是否有效
  - [ ] 🟩 如果浏览器无效，记录警告并返回空列表

- [ ] 🟩 **Step 2: 实现导航重试机制**
  - [ ] 🟩 在`patch_scraper.py:397-422`的导航逻辑中添加重试循环
  - [ ] 🟩 最多重试2次（初始尝试+2次重试=总共3次）
  - [ ] 🟩 每次重试前检查浏览器状态，如果无效则重新创建
  - [ ] 🟩 重试间隔使用指数退避（1秒、2秒）

- [ ] 🟩 **Step 3: 改进错误处理和日志**
  - [ ] 🟩 在导航失败时记录详细的错误信息（包括目标URL）
  - [ ] 🟩 区分浏览器关闭错误和其他导航错误
  - [ ] 🟩 记录重试次数和最终结果

### Issue 2: Newsbreak Zipcode选择和分类采集改进

- [ ] 🟩 **Step 4: 实现Zipcode选择流程**
  - [ ] 🟩 修改`newsbreak_scraper.py:_scrape_zipcode_news`，访问`https://www.newsbreak.com/locations`
  - [ ] 🟩 查找输入框`input[placeholder="City name or zip code"]`并输入zipcode
  - [ ] 🟩 等待自动完成建议出现（`.autocomplete__list-item a.autocomplete__btn`）
  - [ ] 🟩 点击第一个建议项或获取其href
  - [ ] 🟩 提取城市URL（如`/beverly-hills-ca`）
  - [ ] 🟩 如果找不到城市页面，记录警告并返回空列表

- [ ] 🟩 **Step 5: 实现分类采集方法**
  - [ ] 🟩 创建`_scrape_category()`方法，接收城市URL和分类后缀
  - [ ] 🟩 访问`{city_url}-{category}`（business/education/poi_housing）
  - [ ] 🟩 从HTML结构提取文章（使用提供的选择器）
  - [ ] 🟩 提取标题（`h3.text-xl`）、链接（`a[aria-label*="/"]`）、摘要（`p.text-base.text-gray-light`）、时间（相对时间文本）
  - [ ] 🟩 解析相对时间为绝对时间（使用现有的`_parse_date`方法）

- [ ] 🟩 **Step 6: 实现并行采集**
  - [ ] 🟩 使用`asyncio.gather()`并行执行三个分类的采集
  - [ ] 🟩 处理单个分类失败的情况（不影响其他分类）
  - [ ] 🟩 合并三个分类的结果

- [ ] 🟩 **Step 7: 实现去重逻辑**
  - [ ] 🟩 创建`_deduplicate_articles()`方法，基于URL去重
  - [ ] 🟩 在合并三个分类结果后调用去重
  - [ ] 🟩 保留第一次出现的文章（按采集顺序）

- [ ] 🟩 **Step 8: 实现24小时过滤**
  - [ ] 🟩 在`newsbreak_scraper.py`中添加24小时过滤逻辑
  - [ ] 🟩 计算24小时前的时间戳
  - [ ] 🟩 过滤掉`publish_date`超过24小时的文章
  - [ ] 🟩 处理相对时间解析（"5小时"、"1天"等）
  - [ ] 🟩 修复日期比较错误（offset-naive vs offset-aware）

- [ ] 🟩 **Step 9: 修复data_cleaner日期比较问题**
  - [ ] 🟩 修复`data_cleaner.py:filter_by_time_range`中的日期比较错误
  - [ ] 🟩 确保所有日期都转换为offset-aware或offset-naive统一格式
  - [ ] 🟩 使用`datetime.utcnow()`或`datetime.now(timezone.utc)`保持一致性

- [ ] 🟨 **Step 10: 测试和验证**
  - [ ] 🟩 测试Patch修复：验证所有4个zipcode都能成功采集
    - [x] ✅ 90210: 成功（重试机制工作正常，第2次尝试成功）
    - [x] ✅ 10001: 成功（重试机制工作正常，第2次尝试成功）
    - [x] ✅ 94102: 成功（第一次尝试成功）
    - [x] ✅ 60601: 成功（重试机制工作正常，第2次尝试成功）
  - [x] ✅ 测试Newsbreak新流程：验证zipcode选择、三个分类采集、去重、24小时过滤
    - [x] ✅ 已添加浏览器状态检查和重试机制
    - [x] ✅ 分类采集功能已验证：education(5篇), poi_housing(5篇)
    - [x] ✅ 去重逻辑已验证：10篇 -> 8篇
    - [x] ✅ 24小时过滤已验证：8篇都在24小时内
    - [x] ✅ zipcode选择流程：已修复（使用fill替代type），完整流程测试通过（20篇文章）
  - [ ] 🟩 验证日期解析和比较逻辑正确
    - [x] ✅ 修复了offset-naive vs offset-aware错误
    - [x] ✅ 统一使用offset-aware时间格式
  - [ ] 🟩 检查日志输出，确保错误处理和重试逻辑正常工作
    - [x] ✅ Patch重试机制日志正常
    - [x] ✅ 错误信息详细记录

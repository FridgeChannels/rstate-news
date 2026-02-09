# Realtor.com 反爬虫修复实现计划

**Overall Progress:** `100%`

## TLDR

修复Realtor.com采集器：先修复代码bug，然后使用headed模式验证反爬虫问题，改进等待策略和反检测措施，最后更新选择器以匹配实际DOM结构，确保能稳定采集到内容。

## Critical Decisions

关键架构/实现决策：
- **修复优先级**: 先修复代码bug再处理反爬虫 - 当前存在确定的参数错误，必须先解决才能验证反爬虫问题
- **验证策略**: Realtor.com单独使用headed模式验证 - 用户允许弹窗，可以快速验证是否是headless指纹检测问题
- **等待策略**: 避免使用networkidle，改用domcontentloaded + 等待元素 - networkidle在广告/追踪脚本多的页面容易卡死或触发检测
- **指纹策略**: 固定且一致的指纹优于随机 - Realtor.com可能对不一致的指纹更敏感，统一UA/locale/headers

## Tasks:

- [ ] 🟩 **Step 1: 修复RealtorScraper的代码bug**
  - [ ] 🟩 修复`scrapers/realtor_scraper.py`中`_retry_with_backoff`调用的参数错误
  - [ ] 🟩 将`wait_until="networkidle"`改为`domcontentloaded`
  - [ ] 🟩 验证修复后代码可以正常运行（不报TypeError）

- [ ] 🟩 **Step 2: 添加headed模式验证（仅Realtor.com）**
  - [ ] 🟩 为RealtorScraper添加可配置的headless参数（默认False用于验证）
  - [ ] 🟩 在headed模式下添加截图保存功能（用于观察页面状态）
  - [ ] 🟩 更新main.py以传递headless参数

- [ ] 🟩 **Step 3: 改进等待策略**
  - [ ] 🟩 将`wait_until="networkidle"`改为`domcontentloaded`
  - [ ] 🟩 添加等待文章元素出现的逻辑（使用实际DOM选择器）
  - [ ] 🟩 添加超时处理和fallback策略

- [ ] 🟩 **Step 4: 增强反检测措施**
  - [ ] 🟩 扩展`add_init_script`中的反检测代码（隐藏更多自动化特征）
  - [ ] 🟩 添加真实的浏览器属性（chrome对象、plugins、languages、permissions）
  - [ ] 🟩 统一User-Agent和locale设置（Realtor.com使用zh-CN locale和Accept-Language）

- [ ] 🟩 **Step 5: 添加行为模拟**
  - [ ] 🟩 在页面加载后添加随机滚动
  - [ ] 🟩 添加随机延迟模拟人类阅读时间
  - [ ] 🟩 添加弹窗处理逻辑

- [ ] 🟩 **Step 6: 更新选择器以匹配实际DOM**
  - [ ] 🟩 根据提供的HTML结构更新文章容器选择器（div.sc-1ri3r0p-0等）
  - [ ] 🟩 更新标题选择器（h3.sc-1ewhvwh-0等）
  - [ ] 🟩 更新链接选择器（a[href*='/news/real-estate-news/']）
  - [ ] 🟩 更新摘要选择器（p.dsOTPE等）
  - [ ] 🟩 重写extract_article_data_robust方法使用Realtor特定选择器

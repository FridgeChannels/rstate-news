# Scraper测试指南

## 前置条件

### 1. 安装依赖
```bash
cd /Users/markbai/Documents/rstate-news
pip3 install -r requirements.txt
playwright install chromium
```

### 2. 配置环境变量
确保 `.env` 文件已配置（至少需要Supabase配置用于测试数据库操作）

## 测试方法

### 方法1: 测试单个Scraper（推荐）

```bash
# 测试Newsbreak
python3 scripts/test_single_scraper.py

# 或使用交互式测试工具测试所有scraper
python3 scripts/test_scraper_interactive.py
```

### 方法2: 深度分析单个网站

```bash
# 分析Newsbreak网站结构
python3 scripts/analyze_single_website.py Newsbreak "https://www.newsbreak.com/search?q=90210" 90210

# 分析结果会保存在 analysis_output/ 目录
# 包括：
# - 截图
# - HTML结构
# - 分析结果JSON
```

### 方法3: 手动分析（交互式）

```bash
# 打开浏览器，逐个分析网站
python3 scripts/manual_analysis_guide.py
```

## 验证步骤

### Step 1: 测试Newsbreak
```bash
python3 -c "
import asyncio
from scrapers.newsbreak_scraper import NewsbreakScraper

async def test():
    scraper = NewsbreakScraper()
    articles = await scraper.scrape(zipcode='90210', limit=3)
    print(f'提取到 {len(articles)} 篇文章')
    for a in articles:
        print(f\"标题: {a.get('title', 'N/A')[:60]}...\")
        print(f\"链接: {a.get('url', 'N/A')[:60]}...\")
        print()

asyncio.run(test())
"
```

### Step 2: 测试Patch
```bash
# 普通模式
python3 -c "
import asyncio
from scrapers.patch_scraper import PatchScraper

async def test():
    scraper = PatchScraper()
    articles = await scraper.scrape(zipcode='90210', limit=3)
    print(f'提取到 {len(articles)} 篇文章')
    for a in articles:
        print(f\"标题: {a.get('title', 'N/A')[:60]}...\")

asyncio.run(test())
"

# 调试模式（详细日志和截图）
python3 scripts/test_patch_debug.py
```

### Step 3: 测试房地产新闻Scraper
```bash
# 测试Realtor.com
python3 -c "
import asyncio
from scrapers.realtor_scraper import RealtorScraper

async def test():
    scraper = RealtorScraper()
    articles = await scraper.scrape(limit=3)
    print(f'提取到 {len(articles)} 篇文章')
    for a in articles:
        print(f\"标题: {a.get('title', 'N/A')[:60]}...\")

asyncio.run(test())
"
```

## 预期结果

### 成功标准
- ✅ 能够访问网站（可能需要处理弹窗/验证码）
- ✅ 能够找到文章列表（至少3篇文章）
- ✅ 能够提取标题（非空）
- ✅ 能够提取链接（有效的URL）
- ✅ 能够提取日期（ISO格式或可解析格式）
- ✅ 能够提取内容/摘要（非空）

### 如果失败

1. **检查日志**: `logs/scraper.log`
2. **运行分析脚本**: 获取实际DOM结构
3. **查看截图**: `analysis_output/*_screenshot.png`
4. **查看HTML**: `analysis_output/*_article_structure.html`
5. **更新选择器**: 在 `robust_scraper_mixin.py` 中添加新的备选选择器

## 常见问题

### Q: 网站访问超时
**A**: 增加等待时间，或检查网络连接

### Q: 找不到文章列表
**A**: 运行分析脚本获取实际DOM结构，更新 `robust_scraper_mixin.py` 中的选择器

### Q: Cloudflare验证
**A**: Realtor.com和Redfin.com可能需要额外等待时间，或使用代理

### Q: 提取的数据为空
**A**: 检查选择器是否正确，运行分析脚本验证DOM结构

## 更新选择器

如果发现网站使用特殊的选择器，更新 `scrapers/robust_scraper_mixin.py`:

```python
# 在 extract_article_data_robust 方法中，添加新的选择器到列表前面
title_selectors = [
    "新的选择器",  # 添加到前面，提高优先级
    "h1", "h2", "h3", "h4",
    # ... 其他选择器
]
```

# 贡献指南

欢迎贡献代码！本文档将帮助你了解如何参与项目开发。

## 开发环境设置

1. **克隆仓库**
   ```bash
   git clone <repository-url>
   cd rstate-news
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件
   ```

## 代码规范

- **Python风格**: 遵循PEP 8
- **类型提示**: 使用类型提示（typing模块）
- **文档字符串**: 所有函数和类都需要docstring
- **注释**: 复杂逻辑需要注释说明

## 添加新的采集器

### 局部新闻采集器

1. 继承 `LocalNewsScraper` 类
2. 实现 `_scrape_zipcode_news` 方法
3. 在 `main.py` 的 `SCRAPER_CLASSES` 中注册
4. 在Supabase数据库的 `play_news_sources` 表中添加信号源配置

示例：

```python
from scrapers.local_news_scraper import LocalNewsScraper

class MyLocalScraper(LocalNewsScraper):
    def __init__(self):
        super().__init__("MySource")  # source_name必须与数据库中的source_name一致
    
    async def _scrape_zipcode_news(self, zipcode: str, limit: int = 10):
        # 实现采集逻辑
        pass
```

在 `main.py` 中注册：
```python
SCRAPER_CLASSES = {
    'MySource': MyLocalScraper,  # key必须与数据库中的source_name一致
    # ...
}
```

### 房地产新闻采集器

1. 继承 `RealEstateScraper` 类
2. 实现 `_scrape_real_estate_news` 方法
3. 在 `main.py` 的 `SCRAPER_CLASSES` 中注册
4. 在Supabase数据库的 `play_news_sources` 表中添加信号源配置

## 测试

运行测试：

```bash
pytest tests/
```

编写新测试：

- 测试文件命名：`test_*.py`
- 测试函数命名：`test_*`
- 使用pytest fixtures管理测试数据

## 提交代码

1. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **提交更改**
   ```bash
   git add .
   git commit -m "描述你的更改"
   ```

3. **推送并创建PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## 常见问题

### DOM选择器失效

如果网站结构变化导致采集失败：

1. 检查网站实际HTML结构
2. 更新scraper中的选择器
3. 添加多个备选选择器（使用 `query_selector_all` 然后过滤）

### Cloudflare拦截

如果遇到Cloudflare验证：

1. 增加延迟时间
2. 检查User-Agent是否正常
3. 考虑使用代理（需要修改 `base_scraper.py`）

## 联系方式

如有问题，请提交Issue或联系维护者。

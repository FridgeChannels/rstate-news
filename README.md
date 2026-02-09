# RState News - 新闻采集系统

基于Zipcode的局部新闻与全国房地产新闻自动化采集系统。

## 功能特性

- 📍 **局部新闻采集**: 基于Zipcode从Newsbreak和Patch.com采集当地新闻
- 🏠 **房地产新闻采集**: 从Realtor.com、Redfin、NAR、Freddie Mac采集行业新闻
- 🗄️ **Supabase存储**: 使用Supabase PostgreSQL存储，支持去重和历史存档
- ⏰ **定时调度**: 集成APScheduler，支持手动触发和定时任务
- 🔔 **失败通知**: 支持邮件/日志通知
- 📊 **JSON导出**: 按日期和来源分组导出采集结果
- 🛡️ **反爬虫策略**: User-Agent轮换、随机延迟、重试机制

## 技术栈

- **Python 3.9+**
- **Playwright**: 浏览器自动化
- **Supabase**: PostgreSQL数据库
- **APScheduler**: 任务调度
- **BeautifulSoup**: HTML解析
- **Pandas**: 数据处理

## 安装

### 1. 克隆项目

```bash
git clone <repository-url>
cd rstate-news
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 安装Playwright浏览器

```bash
playwright install chromium
```

### 4. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置以下必需配置：

```env
# Supabase配置（必需）
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key

# 其他配置使用默认值即可
```

### 5. 配置Supabase数据库

在Supabase Dashboard的SQL Editor中执行：

**推荐方式（新数据库）**：
- 执行 `database/migrations/000_complete_schema.sql` - 包含所有表结构和初始数据

**或分步执行（已有数据库）**：
1. 执行 `database/migrations/001_initial_schema.sql` 的UP Migration部分
2. 执行 `database/migrations/002_add_news_sources_tables.sql` 的UP Migration部分
3. 执行 `database/migrations/002_seed_news_sources.sql` 初始化信号源数据

### 6. Zipcode 列表（局部新闻）

Zipcode 列表从 Supabase 表 **magnet** 读取（非空 `zip_code` 去重）。请确保 `magnet` 表中有需要采集的 `zip_code` 数据。本地测试时如需用文件配置，可保留 `config.csv`，但主流程不再读取该文件。

## 使用方法

### 手动触发

```bash
python main.py
```

### 定时任务模式

在 `.env` 中设置：

```env
SCHEDULER_ENABLED=true
SCHEDULER_HOUR=2
SCHEDULER_MINUTE=0
```

然后运行：

```bash
python main.py
```

程序将持续运行，按配置的时间自动执行采集任务。

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `SUPABASE_URL` | Supabase项目URL | 必需 |
| `SUPABASE_KEY` | Supabase匿名密钥 | 必需 |
| `SCHEDULER_ENABLED` | 是否启用调度器 | `true` |
| `SCHEDULER_TIMEZONE` | 调度器时区 | `America/New_York` |
| `SCHEDULER_HOUR` | 调度器运行小时 | `2` |
| `SCHEDULER_MINUTE` | 调度器运行分钟 | `0` |
| `SCRAPE_DELAY_MIN` | 采集延迟最小值（秒） | `1` |
| `SCRAPE_DELAY_MAX` | 采集延迟最大值（秒） | `3` |
| `SCRAPE_RETRY_MAX` | 最大重试次数 | `3` |
| `SCRAPE_TIME_RANGE_DAYS` | 采集时间范围（天数） | `7` |
| `NOTIFICATION_ENABLED` | 是否启用通知 | `true` |
| `NOTIFICATION_TYPE` | 通知类型（log/email） | `log` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

完整配置说明请参考 `.env.example`。

### 信号源配置

系统从Supabase数据库的 `play_news_sources` 表加载信号源配置，支持的信号源包括：
- **局部新闻**: Newsbreak, Patch
- **房地产新闻**: Realtor.com, Redfin, NAR, Freddie Mac

信号源配置存储在数据库中，支持动态启用/禁用，无需修改代码。

## 项目结构

```
rstate-news/
├── config/              # 配置模块
│   ├── settings.py      # 配置管理
│   └── __init__.py
├── database/            # 数据库模块
│   ├── supabase_client.py
│   ├── migrations/       # 数据库迁移脚本
│   └── __init__.py
├── scrapers/            # 采集器模块
│   ├── base_scraper.py  # 基础采集器
│   ├── local_news_scraper.py
│   ├── newsbreak_scraper.py
│   ├── patch_scraper.py
│   ├── real_estate_scraper.py
│   ├── realtor_scraper.py
│   ├── redfin_scraper.py
│   ├── nar_scraper.py
│   └── freddiemac_scraper.py
├── utils/               # 工具模块
│   ├── logger.py        # 日志系统
│   ├── data_cleaner.py  # 数据清洗
│   └── json_exporter.py # JSON导出
├── scheduler/           # 调度器模块
│   └── scheduler_manager.py
├── notifications/      # 通知模块
│   └── notification_service.py
├── tests/              # 测试文件
├── output/             # JSON导出目录
├── logs/               # 日志目录
├── config.csv          # 可选，仅本地测试用；主流程从 magnet 表读 Zipcode
├── main.py             # 主程序入口
├── requirements.txt    # 依赖列表
└── README.md           # 本文档
```

## 数据流程

1. **采集**: 从各网站采集新闻文章（基于数据库中的信号源配置）
2. **清洗**: 日期标准化、HTML清理、关键词提取
3. **验证**: 验证必需字段（title, url, source_id等）
4. **过滤**: 按时间范围过滤（默认7天）
5. **存储**: 批量插入Supabase的 `play_raw_news` 表（自动去重）
6. **导出**: 生成JSON文件（按日期和来源分组）

## 生产环境：每天跑一次

项目**支持**在生产环境部署后每天跑一次全量采集，推荐做法如下。

### 推荐方式：外部定时 + 单次执行

1. **关闭内置调度**，让进程执行一次后退出：
   ```env
   SCHEDULER_ENABLED=false
   ```
2. **用系统或云平台的定时任务**每天执行一次，例如：
   - **Linux cron**（每天凌晨 2 点，**无需 Docker**，在服务器上装好 Python 与依赖即可）：
     ```bash
     0 2 * * * cd /path/to/rstate-news && python main.py
     ```
   - **Docker + cron**（可选）：若希望用容器跑，可由宿主机 cron 每天 `docker run --rm --env-file .env your-image python main.py`
   - **GitHub Actions / Render Cron / 云函数定时**：每天触发一次运行 `python main.py`

这样每次启动都会做一次**全量采集**（所有激活源 + 所有 zipcode），执行完后进程退出，无需常驻进程。

### 备选方式：进程常驻 + 内置调度

若希望进程 24 小时常驻并由内置调度器触发：

1. 设置 `SCHEDULER_ENABLED=true`，并配置时区与默认时间（见上文环境变量）。
2. 在 Supabase 表 `play_news_sources` 中，为每个信号源设置 `update_frequency` 为**每日** cron，例如 `0 2 * * *`（每天凌晨 2 点）。
3. 注意：当前实现是**按源**调度，即每个源在各自 cron 时间各跑一次；若需“每天只跑一次全量”，建议仍采用上面的**外部定时 + SCHEDULER_ENABLED=false**。

### 生产环境检查清单

- [ ] 已配置 `SUPABASE_URL`、`SUPABASE_KEY`
- [ ] 已执行 `database/migrations/000_complete_schema.sql`（或等价迁移）
- [ ] `play_news_sources` 中需采集的源已激活，`magnet` 表中有 zipcode（局部新闻需要）
- [ ] 若用 Docker：已安装 Chromium（镜像 `mcr.microsoft.com/playwright/python` 已包含），Realtor 等需虚拟显示时使用 xvfb（Dockerfile 已配置）
- [ ] 每天跑一次时建议使用 `SCHEDULER_ENABLED=false` + 外部 cron/云定时

## Docker 与 Playwright（容器内浏览器）

### 结论：容器内可用，无需单独安装 Chrome/Chromium 或 chromedriver

- **Playwright 官方镜像**（`mcr.microsoft.com/playwright/python`）已内置 **Chromium** 及所需系统依赖，无需在镜像里再执行 `playwright install` 或安装系统 Chrome。
- **没有使用 Selenium 的 chromedriver**：本项目通过 `playwright.chromium.launch()` 启动浏览器，由 Playwright 自带的浏览器二进制与驱动一体完成，不依赖单独 ChromeDriver。
- **Realtor.com 在容器内**：主流程对 Realtor 使用 `headless=False`（便于过反爬）。容器内无真实显示器，Dockerfile 已用 **xvfb** 提供虚拟显示（`DISPLAY=:99`，启动时先起 Xvfb 再跑 `python main.py`），因此 headed 模式在 Docker 中可正常运行。

### 代码层面已适配容器

- 在 **非 macOS**（即 Linux 容器）下，`base_scraper` 会为 Chromium 加上：
  - `--no-sandbox`、`--disable-dev-shm-usage`（避免容器内沙箱与共享内存问题），
  - 以及 headed 时的 `--disable-gpu` 等参数，适配无显卡 + xvfb 环境。
- 仅在 **macOS** 上才会走「系统 Chrome + 持久化 profile」分支；容器内为 Linux，统一走 Chromium + 上述参数，与当前 Docker 镜像一致。

### 运行 Docker 时的注意点

- **`--ipc=host`**：Chromium 在容器内可能因 IPC 命名空间导致崩溃或 OOM，官方建议运行时加 `--ipc=host`。示例：
  ```bash
  docker run --rm -it --env-file .env --ipc=host rstate-news
  ```
- **镜像标签**：Dockerfile 使用与 `playwright==1.40.0` 对应的镜像（如 `v1.40.0-jammy`）。若升级 Playwright 版本，请同步改用对应标签（如 `v1.xx.x-jammy` 或 `v1.xx.x-noble`），否则可能出现浏览器路径不匹配。

### 小结

| 项目           | 说明 |
|----------------|------|
| Chromium       | 由 Playwright 镜像提供，无需额外安装 |
| ChromeDriver   | 不使用；Playwright 自带浏览器与驱动 |
| headed 模式    | 通过 xvfb + `DISPLAY=:99` 支持 |
| 容器内运行     | 已用 `--no-sandbox`、`--disable-dev-shm-usage` 等参数适配；运行建议加 `--ipc=host` |

## 注意事项

### Cloudflare反爬

Realtor.com和Redfin.com有强反爬机制，可能遇到以下情况：

- 需要等待Cloudflare验证（程序会自动等待）
- 如果频繁被封，建议：
  - 增加采集延迟（`SCRAPE_DELAY_MIN/MAX`）
  - 降低采集频率
  - 使用代理（需要修改代码）

### 网站结构变化

如果网站DOM结构变化导致采集失败：

1. 检查日志文件 `logs/scraper.log`
2. 更新对应scraper的DOM选择器
3. 选择器已设计为可配置，便于维护

### Supabase配额

注意Supabase免费层的限制：

- 数据库大小: 500MB
- API请求: 50,000/月
- 存储: 1GB

建议监控使用量，必要时升级计划。

## 开发

### 运行测试

```bash
pytest tests/
```

### 代码风格

遵循PEP 8规范，使用类型提示。

## 许可证

[添加许可证信息]

## 贡献

欢迎提交Issue和Pull Request！

# 快速启动指南

## 5分钟快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置Supabase

1. 在 [Supabase](https://supabase.com) 创建项目
2. 在SQL Editor中执行 `database/migrations/001_initial_schema.sql` 的UP Migration部分
3. 获取项目URL和anon key

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少设置：

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

### 4. Zipcode 列表（局部新闻）

Zipcode 从 Supabase 表 **magnet** 读取。请确保 `magnet` 表中有 `zip_code` 数据。本地测试可保留 `config.csv`，主流程不读取。

### 5. 运行

```bash
python main.py
```

## 验证安装

检查日志文件 `logs/scraper.log`，应该看到：

```
INFO - Supabase客户端初始化成功
INFO - 加载了 X 个Zipcode
INFO - 开始执行采集任务
```

## 常见问题

**Q: 提示Supabase连接失败？**  
A: 检查 `.env` 中的 `SUPABASE_URL` 和 `SUPABASE_KEY` 是否正确。

**Q: Playwright浏览器启动失败？**  
A: 运行 `playwright install chromium` 安装浏览器。

**Q: 采集不到数据？**  
A: 检查网络连接，某些网站可能需要VPN。查看日志了解详细错误。

## 下一步

- 阅读 [README.md](README.md) 了解完整功能
- 查看 [CONTRIBUTING.md](CONTRIBUTING.md) 参与开发
- 调整 `.env` 中的配置参数优化采集策略

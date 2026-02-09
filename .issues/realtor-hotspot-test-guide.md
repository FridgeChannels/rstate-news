# Realtor.com 手机热点验证指引

目标：在“可用网络”（手机热点）下验证 Realtor.com 抓取链路与选择器是否正常，排除家宽出口 IP 风控封禁的干扰。

## 前置条件
- 电脑连接手机热点（Wi‑Fi 或 USB 共享均可）
- 关闭 VPN/代理（除非你明确要测代理效果）

## 运行方式（只跑 Realtor.com）
在项目根目录执行：

```bash
python3 -c "import asyncio; from main import ScraperCoordinator; c=ScraperCoordinator(); asyncio.run(c.run_scraping_task(source_id=11))"
```

说明：
- `source_id=11` 需要与你数据库里的 Realtor.com 源一致（当前项目约定为 11）
- Realtor.com 默认用 **非 headless** 打开浏览器窗口（便于观察）
- 如需“首次人工放行”等待，可设置环境变量：`REALTOR_MANUAL_GATE_SECONDS=60`（单位秒）

## 预期结果
- 日志中出现 `Realtor.com: 采集完成，获得 X 篇文章` 且 `X > 0`
- `logs/realtor_screenshots/` 下生成截图（用于留证）

## 封禁快速判定（关键日志）
若命中封禁页，会在日志中出现类似标记：
- `REALTOR_BLOCK_PAGE_DETECTED`

并且截图内容通常包含：
- `Your request could not be processed`
- `unblockrequest@realtor.com`


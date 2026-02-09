# Zipcode 来源改为 Supabase 实现计划

**Overall Progress:** `100%`

## TLDR

将主程序 Zipcode 列表从读取 `config.csv` 改为从 Supabase 表 `magnet` 查询（`select zip_code from magnet where zip_code is not null group by zip_code`）。`config.csv` 后续不再参与主流程，仅保留供本地测试可选使用；空列表时日志写明「magnet中无zip_code」。

## Critical Decisions

- **magnet 表与实现方式**：magnet 表已存在、SQL 可用 → 使用 Supabase 表 API `table('magnet').select('zip_code').not_.is_('zip_code','null')`，在 Python 内去重，等价 GROUP BY；不建 RPC。
- **数据量**：magnet 查询结果数量暂不考虑，不做分页或限流。
- **config.csv**：主流程不再使用 config.csv；保留 `settings.zipcode_csv_path` 与文件，供本地测试可选使用；不实现「DB 失败回退读 CSV」。
- **空列表日志**：当 zipcode 列表为空时，日志明确写「magnet中无zip_code」（在跳过 local_business 的 warning 中体现）。

## Tasks

- [x] 🟩 **Step 1: 在 Supabase 客户端中新增获取 zipcode 列表方法**
  - [x] 🟩 在 `database/supabase_client.py` 的 `DatabaseManager` 中新增 `get_zipcodes_from_magnet() -> List[str]`（async）。
  - [x] 🟩 使用 `table('magnet').select('zip_code').not_.is_('zip_code','null')`，用 `asyncio.to_thread` 包装同步调用；对返回行在 Python 内去重并统一转为 `str`，返回列表。
  - [x] 🟩 查询异常时打日志并返回 `[]`。

- [x] 🟩 **Step 2: 主程序改为从 DB 加载 zipcode并更新日志**
  - [x] 🟩 将 `main.py` 中 `load_zipcodes()` 改为 async，内部调用 `await db_manager.get_zipcodes_from_magnet()`，返回类型仍为 `List[str]`。
  - [x] 🟩 调用处（约 521 行）改为 `zipcodes = await self.load_zipcodes()`。
  - [x] 🟩 当 zipcode 列表为空且为 local_business 时，将 warning 改为写明「magnet中无zip_code」（例如：`局部新闻源 {source_name} 需要zipcode，但magnet中无zip_code`）。

- [x] 🟩 **Step 3: 文档说明 zipcode 来自 magnet**
  - [x] 🟩 在 README、QUICKSTART 中说明 Zipcode 列表来自 Supabase 表 `magnet`，不再依赖编辑 config.csv；可注明本地测试仍可保留 config.csv。
  - [x] 🟩 在 TEST_PLAN 中将「确认 config.csv 中有 zipcode」改为「确认 magnet 表中有 zip_code 或验证无 zipcode 时仅跳过局部新闻」等等价检查。

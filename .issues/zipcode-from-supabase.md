# Zipcode 列表改为从 Supabase 查询

**类型**: improvement  
**优先级**: normal  
**预估**: medium  

---

## TL;DR

主程序当前从 `config.csv` 读取 Zipcode 列表；需改为从 Supabase 表 `magnet` 查询非空 `zip_code` 并去重，SQL：`select zip_code from magnet where zip_code is not null group by zip_code`。

---

## 当前 vs 期望

| 项目 | 当前 | 期望 |
|------|------|------|
| 数据源 | `config.csv`（本地文件） | Supabase 表 `magnet` |
| 获取方式 | `ScraperCoordinator.load_zipcodes()` 读 CSV | 调用 DB 查询，等价 SQL 见上 |
| 空列表时 | 打日志「config.csv为空」 | 打日志「magnet 中无 zip_code」或类似 |

---

## 相关文件

- **`main.py`**  
  - `load_zipcodes()`（约 279–305 行）：改为调用 Supabase 获取 zipcode 列表；若改为异步，需同步改调用处（约 521 行 `zipcodes = self.load_zipcodes()`）。
- **`database/supabase_client.py`**  
  - 新增方法：从 `magnet` 查询 `zip_code`（`where zip_code is not null` + 按 `zip_code` 去重）。Supabase 客户端若无 RPC，可用 `table('magnet').select('zip_code').not_.is_('zip_code', 'null')` 查询后在 Python 侧去重。
- **`config/settings.py`**  
  - `zipcode_csv_path`（约 210 行）：若不再用 CSV 做 zipcode，可保留作兼容或后续移除，在 issue 内注明即可。

---

## 实现要点

- SQL 等价行为：`select zip_code from magnet where zip_code is not null group by zip_code`。
- 返回类型保持 `List[str]`，与现有 `load_zipcodes()` 一致，便于主流程不变。
- 若 `load_zipcodes()` 改为 async，需在调用处 `await self.load_zipcodes()` 并确保调用链为 async。

---

## 风险与备注

- **依赖**：主程序已使用 `db_manager`，无新增运行时依赖；需确认 Supabase 中已有 `magnet` 表及 `zip_code` 字段。
- **兼容**：若有脚本或文档仍假设 zipcode 来自 `config.csv`，需在 README/QUICKSTART 中说明改为 DB 驱动。
- **测试**：验证 `magnet` 无数据或全为 `zip_code is null` 时，主程序不报错且局部新闻逻辑正常跳过。

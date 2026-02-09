# 验证：无 Zipcode 列表时仍会爬取非局部新闻站

**类型**: improvement  
**优先级**: normal  
**预估**: small  

---

## TL;DR

在 zipcode 列表改为从 Supabase 查询后，需确认：当列表为空（如 magnet 表无数据）时，程序仍会正常爬取 **real_estate / housing** 等非局部新闻站，仅跳过 **local_business** 源。

---

## 当前 vs 期望

| 场景 | 当前逻辑（main.py 524–546） | 期望 |
|------|-----------------------------|------|
| zipcodes 为空 | real_estate/housing 照常 `scrape_source(source)`；local_business 被 `continue` 并打 warning | 保持该行为，并显式验证/测试 |
| zipcodes 非空 | 全部按 content_scope 分支执行 | 不变 |

---

## 相关文件

- **`main.py`**  
  - `run_scraping_task()` 中按 `content_scope` 分支（约 529–546 行）：当前实现上已满足“无 zipcode 仍爬非 local”；可在此处或注释中明确写出“无 zipcode 时仅跳过 local_business”。
- **测试或文档**  
  - 可选：在 TEST_PLAN 或单测里增加“zipcodes=[] 时仅跑 real_estate/housing”的用例或步骤说明。

---

## 实现要点

- 确认无回归：不改变现有分支逻辑，仅做验证与可选的文档/测试补充。
- 若后续 zipcode 改为从 Supabase 拉取（见 `.issues/zipcode-from-supabase.md`），在部署/说明中注明：magnet 无 zip_code 时只会影响局部新闻，房地产等源照常跑。

---

## 风险与备注

- 低风险：仅验证与文档/轻量测试，不修改核心流程。
- 与 **zipcode-from-supabase** issue 关联：改数据源后建议在本项验证通过后再关闭。

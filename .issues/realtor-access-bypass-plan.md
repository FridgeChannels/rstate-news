# Feature Implementation Plan

**Overall Progress:** `100%`

## TLDR
Realtor.com 在当前家宽出口下对“新会话（无痕/自动化）”触发封禁页（`Your request could not be processed`），但在手机热点下无痕可正常访问。我们将先用**手机热点**作为可用出口进行验证，同时在代码侧实现“更像真实用户”的访问策略：**固定 `en-US` 画像、复用持久化会话、允许人工验证/放行一次并复用 cookie**，以提高在不同网络下的稳定性。

## Critical Decisions
- Decision 1: **先用手机热点验证链路** - 已确认热点下无痕可用，可作为基准环境快速验证采集逻辑与选择器，不被家宽出口封禁干扰。
- Decision 2: **优先复用持久化会话（方案B）** - 家宽下普通窗口连续刷新 10 次仍可访问，说明“已建立信任的会话”有效；自动化应尽量复用会话而不是每次新会话。
- Decision 3: **统一为 `en-US`（即使本机偏 `zh-CN`）** - 用户明确要求以 `en-US` 画像运行；实现时以 `locale/Accept-Language/timezone` 等一致化为目标。
- Decision 4: **接受更长等待/交互** - 为降低风控命中率，可接受增加等待、滚动、轻交互与手动验证窗口。

## Tasks:

- [ ] 🟩 **Step 1: 固化“可用网络”验证流程（手机热点）**
  - [ ] 🟩 增加一份测试指引：在手机热点下运行 `source_id=11`（Realtor.com）并确认可见新闻列表（见 `/.issues/realtor-hotspot-test-guide.md`）
  - [ ] 🟩 在运行日志中明确标记：当前是否出现封禁页关键字（用于快速判定，日志标记：`REALTOR_BLOCK_PAGE_DETECTED`）

- [ ] 🟩 **Step 2: Realtor.com 专用浏览器画像（强制 `en-US`）**
  - [ ] 🟩 Realtor.com context 固定 `locale='en-US'`、`Accept-Language='en-US,en;q=0.9'`（可用环境变量覆盖）
  - [ ] 🟩 固定 `timezone_id`（默认 `America/Los_Angeles`，可用环境变量覆盖）
  - [ ] 🟩 固定 UA 为“macOS + Chrome”真实组合（可用环境变量覆盖）

- [ ] 🟨 **Step 3: 方案B — 复用持久化会话 / 手动放行一次**
  - [ ] 🟩 Realtor.com 使用 `launch_persistent_context` 持久化 profile（`logs/realtor_profile/`）
  - [ ] 🟩 提供“首次人工放行”模式：`headless=False` 打开窗口，并可用 `REALTOR_MANUAL_GATE_SECONDS` 控制等待时间
  - [ ] 🟥 后续运行默认复用该 profile/cookie，无需重复人工操作（以热点环境验证通过为准）

- [ ] 🟩 **Step 4: 风控识别与降级策略**
  - [ ] 🟩 检测封禁页特征文本（如 `Your request could not be processed`、`unblockrequest@realtor.com`）
  - [ ] 🟩 一旦命中封禁：保存截图 + 导出 HTML（`logs/realtor_blocked/`），并中止本次 Realtor 抓取（避免反复触发加重封禁）

- [ ] 🟩 **Step 5: 行为拟真（轻量、可控）**
  - [ ] 🟩 页面加载后添加分段滚动与随机停留（轻量拟真）
  - [ ] 🟩 降低 Realtor.com 请求节奏（`REALTOR_MIN_REQUEST_INTERVAL_SECONDS`），避免短时间多次触发风控

- [ ] 🟨 **Step 6: 在“可用网络”下验证选择器与内容抓取**
  - [ ] 🟨 在手机热点下确认新闻列表页能抓到文章容器（`div.sc-1ri3r0p-0` 等）
  - [ ] 🟨 确认文章标题/链接/摘要可提取，并最终写入数据库与 JSON 导出

> 备注：当前在家宽出口上仍会命中封禁页（已落盘证据到 `logs/realtor_blocked/`）。请在手机热点下执行 `/.issues/realtor-hotspot-test-guide.md` 的命令完成最终验证。


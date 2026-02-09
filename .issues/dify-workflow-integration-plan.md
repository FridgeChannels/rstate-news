# Dify工作流集成实现计划

**Overall Progress:** `100%`

## TLDR

在所有网站爬取完成并插入数据库后，获取插入记录的id，按zipcode分组（空值也是一组），每组顺序调用Dify工作流接口进行审核。如果某条记录返回status为APPROVE，该组停止继续执行。

## Critical Decisions

关键架构/实现决策：
- **返回类型修改**: `insert_raw_news`改为返回插入记录列表（包含id），保持向后兼容 - 需要同时返回记录列表和数量，便于调用方选择使用
- **分组键处理**: zipcode为NULL/空字符串统一归为"__empty__"组 - 简化分组逻辑，避免None值问题
- **错误处理策略**: 单条记录调用失败时继续执行下一条，不中断整组 - 提高容错性，避免因网络问题影响整组处理
- **API配置**: Dify API Key和Endpoint硬编码在客户端类中 - 简化配置，后续如需可移到.env

## Tasks:

- [ ] 🟩 **Step 1: 修改数据库插入方法返回完整记录**
  - [ ] 🟩 修改`database/supabase_client.py`中`insert_raw_news`方法的返回类型
  - [ ] 🟩 返回插入的记录列表（`response.data`），包含自动生成的id
  - [ ] 🟩 保持向后兼容，同时返回记录列表和数量（或返回元组）
  - [ ] 🟩 更新方法文档说明新的返回格式

- [ ] 🟩 **Step 2: 创建Dify客户端封装类**
  - [ ] 🟩 创建`utils/dify_client.py`文件
  - [ ] 🟩 实现`DifyClient`类，封装API调用逻辑
  - [ ] 🟩 实现`run_workflow`方法，接受`play_raw_news_id`参数
  - [ ] 🟩 配置API Key: `app-11UCJJckzZQIu14r1TZrllQm`
  - [ ] 🟩 配置Endpoint: `http://kno.fridgechannels.com/v1/workflows/run`
  - [ ] 🟩 实现请求构建（inputs, response_mode, user）
  - [ ] 🟩 添加HTTP请求错误处理和超时处理
  - [ ] 🟩 实现响应解析，提取status字段

- [ ] 🟩 **Step 3: 实现zipcode分组逻辑**
  - [ ] 🟩 在`main.py`中创建`_group_by_zipcode`辅助方法
  - [ ] 🟩 处理zipcode为None/空字符串的情况，统一归为"__empty__"组
  - [ ] 🟩 保持每组内记录的插入顺序
  - [ ] 🟩 返回分组字典：`{zipcode: [record1, record2, ...]}`

- [ ] 🟩 **Step 4: 实现按组顺序调用Dify接口**
  - [ ] 🟩 在`main.py`中创建`_process_dify_review`方法
  - [ ] 🟩 遍历每个zipcode组
  - [ ] 🟩 每组内按顺序调用Dify接口（使用DifyClient）
  - [ ] 🟩 检查返回的status字段是否为"APPROVE"
  - [ ] 🟩 如果遇到APPROVE，记录日志并停止该组后续处理
  - [ ] 🟩 如果调用失败，记录错误但继续下一条
  - [ ] 🟩 记录每条记录的调用结果（成功/失败/已通过）

- [ ] 🟩 **Step 5: 集成到主爬虫流程**
  - [ ] 🟩 修改`main.py`的`run_scraping_task`方法
  - [ ] 🟩 在数据库插入后（第4步），获取插入的记录列表
  - [ ] 🟩 调用分组和Dify处理逻辑
  - [ ] 🟩 在JSON导出之前（第5步之前）执行Dify审核
  - [ ] 🟩 添加适当的日志记录

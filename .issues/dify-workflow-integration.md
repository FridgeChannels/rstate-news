# 集成Dify工作流：按zipcode分组调用审核接口

**Type:** `feature`  
**Priority:** `normal`  
**Effort:** `medium`

## TL;DR

在所有网站爬取完成并插入数据库后，获取插入记录的id，按zipcode分组（空值也是一组），每组顺序调用Dify工作流接口进行审核。如果某条记录返回status为APPROVE，该组停止继续执行。

## Current State

- 爬虫完成后，数据插入到`play_raw_news`表
- `insert_raw_news`方法只返回插入数量，不返回插入记录的id
- 没有调用Dify工作流进行审核的逻辑

## Expected Outcome

1. **修改数据库插入方法**：
   - `insert_raw_news`方法返回插入的记录列表（包含id），而不仅仅是数量
   - 确保`response.data`包含完整的插入记录（包括自动生成的id）

2. **实现zipcode分组逻辑**：
   - 获取所有插入记录的id和zipcode
   - 按zipcode分组，zipcode为NULL/空的记录归为一组
   - 每组内的记录保持插入顺序

3. **实现Dify接口调用**：
   - 创建Dify客户端封装类
   - 每组内顺序调用接口（按插入顺序）
   - 请求格式：
     ```json
     {
       "inputs": {
         "play_raw_news_id": <记录id>
       },
       "response_mode": "blocking",
       "user": "abc-123"
     }
     ```
   - API Key: `app-11UCJJckzZQIu14r1TZrllQm`
   - Endpoint: `http://kno.fridgechannels.com/v1/workflows/run`

4. **实现审核状态判断**：
   - 解析Dify返回的响应
   - 检查`status`字段是否为`APPROVE`
   - 如果某条记录返回`APPROVE`，该组停止继续执行后续记录
   - 记录调用结果（成功/失败/已通过）

5. **集成到主流程**：
   - 在`main.py`的`run_scraping_task`方法中，插入数据库后调用新逻辑
   - 在JSON导出之前执行Dify审核流程

## Relevant Files

- `database/supabase_client.py` - 修改`insert_raw_news`方法返回完整记录
- `main.py` - 在`run_scraping_task`中集成Dify调用逻辑
- `utils/dify_client.py` - 新建Dify客户端封装（如果不存在）
- `.env` - 添加Dify API配置（如果需要）

## Implementation Notes

- Dify API调用需要处理网络错误和超时
- 需要记录每条记录的调用状态（可选：更新数据库字段或写入日志）
- 如果某条记录调用失败，建议继续执行下一条（不因单条失败影响整组）
- 考虑添加重试机制（可选，根据实际需求）
- 响应解析需要确认Dify返回的完整JSON结构

## Risks

- Dify API可能不稳定，需要错误处理和重试
- 如果插入记录很多，顺序调用可能耗时较长（考虑是否需要并发，但用户要求顺序）
- zipcode分组逻辑需要处理NULL/空值的边界情况
- 需要确认Dify返回的响应格式，特别是status字段的位置和值

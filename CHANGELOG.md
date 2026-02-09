# 更新日志

本文档记录项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- Patch Scraper 调试模式：添加 `debug_mode` 参数，支持详细日志和自动截图
- Patch Scraper 调试测试脚本：`scripts/test_patch_debug.py` 用于手动测试验证工作流程
- 调试截图功能：在关键步骤自动保存截图到 `logs/patch_debug_screenshots/`
- 浏览器状态检查：添加浏览器连接验证和重试机制，提高稳定性

### Changed
- Patch Scraper 工作流程：从访问搜索URL改为访问主页，通过自动完成建议导航到目标页面
- Patch Scraper 等待策略：输入zipcode后等待时间从1-2秒增加到3秒，确保自动完成加载完成
- Patch Scraper 导航方式：从点击建议项改为直接获取URL并导航，避免浏览器崩溃问题
- Patch Scraper 选择器：更新为实际发现的DOM选择器（`.autocomplete__dropdown`, `.autocomplete__list-item a.autocomplete__btn`, `article.styles_ArticleCard__ZF3Wi` 等）

### Fixed
- Patch Scraper 浏览器稳定性：修复headless=False模式下的浏览器断开问题，改为使用headless=True但保留调试功能
- Patch Scraper 页面创建：添加页面创建重试机制（最多3次），提高成功率
- Patch Scraper 文章提取：优化文章数据提取逻辑，使用Patch特定的选择器并回退到通用方法

### Removed
- 清理项目文档：删除所有临时实施计划、执行总结、测试结果、探索文档、代码审查等临时文档，仅保留核心文档（README、CHANGELOG、QUICKSTART、CONTRIBUTING、TESTING_GUIDE）

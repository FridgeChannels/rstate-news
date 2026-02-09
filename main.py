"""
主程序入口
协调所有采集器，执行采集任务（配置驱动）
"""
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

from config.settings import settings
from database.supabase_client import db_manager
from scrapers.newsbreak_scraper import NewsbreakScraper
from scrapers.patch_scraper import PatchScraper
from scrapers.realtor_scraper import RealtorScraper
from scrapers.redfin_scraper import RedfinScraper
from scrapers.nar_scraper import NARScraper
from scrapers.freddiemac_scraper import FreddieMacScraper
from utils.data_cleaner import DataCleaner
from utils.json_exporter import JSONExporter
from utils.dify_client import dify_client
from utils.logger import logger
from notifications.notification_service import NotificationService
from scheduler.scheduler_manager import SchedulerManager


class ScraperCoordinator:
    """采集器协调器（配置驱动）"""
    
    # Scraper类映射表（根据source_name匹配）
    SCRAPER_CLASSES = {
        'Newsbreak': NewsbreakScraper,
        'Patch': PatchScraper,
        'Realtor.com': RealtorScraper,
        'Redfin': RedfinScraper,
        'NAR': NARScraper,
        'Freddie Mac': FreddieMacScraper,
    }
    
    def __init__(self):
        """初始化协调器"""
        self.data_cleaner = DataCleaner(time_range_days=settings.scrape_time_range_days)
        self.json_exporter = JSONExporter()
        self.notification_service = NotificationService()
        self.sources_cache: List[Dict[str, Any]] = []
    
    async def load_sources_from_db(self) -> List[Dict[str, Any]]:
        """
        从play_news_sources表加载所有激活的信号源配置
        
        Returns:
            信号源配置列表
        """
        try:
            sources = await db_manager.get_active_sources()
            self.sources_cache = sources
            logger.info(f"从数据库加载了 {len(sources)} 个激活的信号源")
            return sources
        except Exception as e:
            logger.error(f"加载信号源配置失败: {str(e)}", exc_info=True)
            return []
    
    def _create_scraper(self, source_config: Dict[str, Any]):
        """
        根据信号源配置创建对应的scraper实例
        
        Args:
            source_config: 信号源配置字典
            
        Returns:
            Scraper实例，如果找不到对应的scraper则返回None
        """
        source_name = source_config.get('source_name')
        
        if source_name not in self.SCRAPER_CLASSES:
            logger.warning(f"未找到对应的scraper类: {source_name}")
            return None
        
        scraper_class = self.SCRAPER_CLASSES[source_name]
        # Realtor.com使用headed模式验证反爬虫问题
        if source_name == 'Realtor.com':
            return scraper_class(headless=False)
        return scraper_class()
    
    def _validate_raw_news(self, raw_news: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证原始新闻数据
        
        Args:
            raw_news: 原始新闻数据字典
            
        Returns:
            (是否有效, 错误信息) 元组
        """
        # 验证必需字段
        if not raw_news.get('source_id'):
            return False, "source_id is required"
        
        title = raw_news.get('title', '')
        if not title or len(title.strip()) == 0:
            return False, "title is required and cannot be empty"
        
        url = raw_news.get('url', '')
        if not url:
            return False, "url is required"
        
        # URL格式验证
        if not url.startswith(('http://', 'https://')):
            return False, f"invalid url format: {url}"
        
        return True, None
    
    def _deduplicate_raw_news(self, raw_news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        基于URL去重原始新闻列表
        
        使用URL标准化函数处理URL，确保相同内容的不同URL格式能被识别为重复。
        保留第一次出现的记录。
        
        Args:
            raw_news_list: 原始新闻列表
            
        Returns:
            去重后的新闻列表
        """
        if not raw_news_list:
            return []
        
        original_count = len(raw_news_list)
        seen_urls = set()
        deduplicated = []
        
        for news in raw_news_list:
            url = news.get('url', '')
            if not url:
                # 如果没有URL，保留记录（但记录警告）
                logger.warning(f"发现没有URL的记录，保留: {news.get('title', 'unknown')[:50]}")
                deduplicated.append(news)
                continue
            
            # 标准化URL
            normalized_url = self.data_cleaner.normalize_url(url)
            
            if normalized_url and normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                deduplicated.append(news)
            else:
                logger.debug(f"发现重复URL，已跳过: {url[:100]}")
        
        deduplicated_count = len(deduplicated)
        removed_count = original_count - deduplicated_count
        
        if removed_count > 0:
            logger.info(f"主流程去重完成: {original_count} -> {deduplicated_count} 条记录（移除 {removed_count} 条重复）")
        else:
            logger.debug(f"主流程去重: {original_count} 条记录，无重复")
        
        return deduplicated
    
    def _group_by_zipcode(self, records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        按zipcode对记录进行分组
        
        Args:
            records: 包含id和zip_code的记录列表
            
        Returns:
            分组字典，格式: {zipcode: [record1, record2, ...]}
            zipcode为None/空字符串的记录归为"__empty__"组
        """
        groups: Dict[str, List[Dict[str, Any]]] = {}
        
        for record in records:
            zipcode = record.get('zip_code') or record.get('zipcode')
            
            # 处理None和空字符串
            if not zipcode or zipcode.strip() == '':
                group_key = "__empty__"
            else:
                group_key = str(zipcode).strip()
            
            if group_key not in groups:
                groups[group_key] = []
            
            groups[group_key].append(record)
        
        return groups
    
    async def _process_dify_review(self, inserted_records: List[Dict[str, Any]]) -> None:
        """
        按zipcode分组，每组顺序调用Dify工作流接口进行审核
        
        Args:
            inserted_records: 插入数据库的记录列表（包含id和zip_code）
        """
        if not inserted_records:
            logger.info("没有需要审核的记录")
            return
        
        # 按zipcode分组
        groups = self._group_by_zipcode(inserted_records)
        logger.info(f"按zipcode分组完成，共 {len(groups)} 组")
        
        total_processed = 0
        total_approved = 0
        total_failed = 0
        
        # 遍历每个zipcode组
        for zipcode, records in groups.items():
            zipcode_display = "(空)" if zipcode == "__empty__" else zipcode
            logger.info(f"开始处理zipcode组: {zipcode_display}，共 {len(records)} 条记录")
            
            group_approved = False
            
            # 每组内按顺序调用Dify接口
            for i, record in enumerate(records, 1):
                record_id = record.get('id')
                if not record_id:
                    logger.warning(f"记录缺少id字段，跳过: {record}")
                    continue
                
                logger.debug(f"调用Dify接口: zipcode={zipcode_display}, record_id={record_id} ({i}/{len(records)})")
                
                try:
                    # 调用Dify工作流
                    response = await dify_client.run_workflow(record_id)
                    
                    # 检查是否通过
                    if dify_client.is_approved(response):
                        logger.info(f"记录已通过审核: zipcode={zipcode_display}, record_id={record_id}")
                        total_approved += 1
                        group_approved = True
                        # 该组已通过，停止处理后续记录
                        logger.info(f"zipcode组 {zipcode_display} 已通过审核，停止处理该组剩余 {len(records) - i} 条记录")
                        break
                    else:
                        # 未通过或调用失败
                        if "error" in response:
                            logger.warning(f"Dify调用失败: zipcode={zipcode_display}, record_id={record_id}, error={response.get('error')}")
                            total_failed += 1
                        else:
                            logger.debug(f"记录未通过审核: zipcode={zipcode_display}, record_id={record_id}, status={response.get('status')}")
                    
                    total_processed += 1
                    
                except Exception as e:
                    logger.error(f"处理Dify审核时发生异常: zipcode={zipcode_display}, record_id={record_id}, error={str(e)}", exc_info=True)
                    total_failed += 1
                    total_processed += 1
                    # 继续处理下一条，不中断整组
            
            if not group_approved:
                logger.info(f"zipcode组 {zipcode_display} 处理完成，未通过审核")
        
        logger.info(f"Dify审核流程完成: 总处理={total_processed}, 通过={total_approved}, 失败={total_failed}")
    
    def _extract_raw_category(self, article: Dict[str, Any]) -> Optional[str]:
        """
        从文章数据中提取原始分类标签
        
        Args:
            article: 文章数据字典
            
        Returns:
            原始分类标签字符串，如果不存在返回None
        """
        raw_category = article.get('raw_category')
        if raw_category:
            return raw_category
        
        keywords = article.get('keywords')
        if keywords:
            if isinstance(keywords, str):
                return keywords
            elif isinstance(keywords, list) and keywords:
                return ', '.join(str(k) for k in keywords[:5])  # 限制长度
        
        return None
    
    async def load_zipcodes(self) -> List[str]:
        """
        从 Supabase 表 magnet 加载 Zipcode 列表（非空 zip_code 去重）。
        
        Returns:
            Zipcode 列表；异常或无数据时返回 []。
        """
        return await db_manager.get_zipcodes_from_magnet()
    
    async def scrape_source(
        self,
        source_config: Dict[str, Any],
        zipcode: Optional[str] = None
    ) -> List[dict]:
        """
        采集指定信号源的新闻
        
        Args:
            source_config: 信号源配置
            zipcode: 邮政编码（仅局部新闻需要）
            
        Returns:
            原始新闻列表
        """
        source_id = source_config.get('id')
        source_name = source_config.get('source_name')
        content_scope = source_config.get('content_scope')
        city = source_config.get('city')
        
        all_news = []
        
        try:
            # 创建scraper实例
            scraper = self._create_scraper(source_config)
            if not scraper:
                logger.warning(f"无法创建scraper: {source_name}")
                return []
            
            # 记录任务开始
            task_log_id = await db_manager.log_task(
                task_type="local_news" if zipcode else "real_estate",
                status="running",
                source_id=source_id,
                source=source_name,
                zipcode=zipcode
            )
            
            # 执行采集（添加超时控制，防止单个源阻塞太久）
            try:
                if zipcode:
                    # 局部新闻采集
                    articles = await asyncio.wait_for(
                        scraper.scrape(zipcode=zipcode, limit=10),
                        timeout=300  # 5分钟超时
                    )
                else:
                    # 房地产新闻采集
                    articles = await asyncio.wait_for(
                        scraper.scrape(limit=20),
                        timeout=300  # 5分钟超时
                    )
            except asyncio.TimeoutError:
                logger.error(f"采集超时: {source_name} (ID: {source_id})")
                articles = []
            
            if articles:
                # 清洗数据
                cleaned_articles = self.data_cleaner.clean_articles(articles)
                
                # 批量获取文章真实内容
                cleaned_articles = await self._fetch_articles_content(cleaned_articles)
                
                # 转换为play_raw_news格式并验证
                for article in cleaned_articles:
                    raw_news = {
                        'source_id': source_id,
                        'city': city or article.get('city', ''),
                        'zip_code': zipcode if zipcode else article.get('zipcode') or article.get('zip_code'),  # 兼容zipcode和zip_code字段
                        'title': article.get('title', ''),
                        'content': article.get('content') or article.get('content_summary', ''),
                        'publish_date': article.get('publish_date'),
                        'url': article.get('url', ''),
                        'language': article.get('language', 'en'),
                        'raw_category': self._extract_raw_category(article),
                        'status': 'new'
                    }
                    
                    # 验证数据
                    is_valid, error_msg = self._validate_raw_news(raw_news)
                    if not is_valid:
                        logger.warning(f"跳过无效数据: {error_msg} - URL: {raw_news.get('url', 'unknown')}")
                        continue
                    
                    all_news.append(raw_news)
                
                # 更新任务日志
                await db_manager.update_task_log(
                    task_log_id,
                    status="success",
                    articles_count=len(all_news),
                    source_id=source_id
                )
            else:
                await db_manager.update_task_log(
                    task_log_id,
                    status="success",
                    articles_count=0,
                    source_id=source_id
                )
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"采集失败 ({source_name}, ID: {source_id}): {error_msg}", exc_info=True)
            
            # 发送失败通知
            await self.notification_service.send_failure_notification(
                task_type="local_news" if zipcode else "real_estate",
                error_message=error_msg,
                zipcode=zipcode,
                source=source_name
            )
            
            # 更新任务日志
            try:
                await db_manager.log_task(
                    task_type="local_news" if zipcode else "real_estate",
                    status="failed",
                    source_id=source_id,
                    source=source_name,
                    zipcode=zipcode,
                    error_message=error_msg
                )
            except Exception as e:
                logger.warning(f"记录失败任务日志失败: {str(e)}")
        
        return all_news
    
    async def _fetch_articles_content(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量获取文章真实内容
        
        Args:
            articles: 文章列表
            
        Returns:
            更新后的文章列表（成功获取内容的文章已更新content和content_summary）
        """
        if not articles:
            return articles
        
        from utils.article_content_fetcher import fetch_article_content
        
        # 创建信号量控制并发数（3个并发）
        semaphore = asyncio.Semaphore(3)
        
        async def _fetch_content_for_article(article: Dict[str, Any]) -> Dict[str, Any]:
            """为单篇文章获取内容"""
            async with semaphore:
                url = article.get('url', '')
                if not url:
                    return article
                
                # 尝试获取真实内容
                content = await fetch_article_content(url, timeout=30)
                
                if content:
                    # 成功获取内容，更新content和content_summary
                    article['content'] = content
                    article['content_summary'] = content
                # 如果失败，保留原有的content_summary（已在article中）
            
            return article
        
        # 批量处理所有文章
        try:
            results = await asyncio.gather(
                *[_fetch_content_for_article(article) for article in articles],
                return_exceptions=True
            )
            
            # 处理结果，排除异常
            updated_articles = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # 如果处理失败，保留原文章
                    updated_articles.append(articles[i])
                else:
                    updated_articles.append(result)
            
            return updated_articles
            
        except Exception as e:
            # 如果批量处理失败，返回原文章列表
            logger.warning(f"批量获取文章内容失败: {str(e)}")
            return articles
    
    async def run_scraping_task(self, source_id: Optional[int] = None):
        """
        执行采集任务
        
        Args:
            source_id: 如果指定，只采集该源；否则采集所有激活的源
        """
        logger.info("=" * 50)
        logger.info("开始执行采集任务")
        logger.info("=" * 50)
        
        all_raw_news = []
        
        try:
            # 1. 加载信号源配置
            sources = await self.load_sources_from_db()
            
            if source_id:
                # 只采集指定的源
                sources = [s for s in sources if s.get('id') == source_id]
            
            if not sources:
                logger.warning("没有找到激活的信号源")
                return
            
            # 2. 加载 zipcode 列表（用于局部新闻，来自 Supabase 表 magnet）
            zipcodes = await self.load_zipcodes()
            
            # 3. 按内容范围分组处理
            for source in sources:
                content_scope = source.get('content_scope')
                source_name = source.get('source_name')
                
                logger.info(f"处理信号源: {source_name} (ID: {source.get('id')})")
                
                if content_scope in ['real_estate', 'housing']:
                    # 房地产新闻，不需要zipcode
                    news = await self.scrape_source(source)
                    all_raw_news.extend(news)
                    await asyncio.sleep(2)  # 避免请求过快
                    
                elif content_scope == 'local_business':
                    # 局部新闻，需要zipcode
                    if not zipcodes:
                        logger.warning(f"局部新闻源 {source_name} 需要zipcode，但magnet中无zip_code")
                        continue
                    
                    for zipcode in zipcodes:
                        logger.info(f"  处理Zipcode: {zipcode}")
                        news = await self.scrape_source(source, zipcode=zipcode)
                        all_raw_news.extend(news)
                        await asyncio.sleep(2)  # 避免请求过快
            
            # 3.5. 主流程去重（合并所有scraper结果后）
            if all_raw_news:
                logger.info("=" * 50)
                logger.info("开始主流程去重")
                logger.info("=" * 50)
                all_raw_news = self._deduplicate_raw_news(all_raw_news)
            
            # 4. 存储到数据库（play_raw_news表）
            inserted_records = []
            if all_raw_news:
                logger.info(f"准备存储 {len(all_raw_news)} 条原始新闻到数据库")
                inserted_count, inserted_records = await db_manager.insert_raw_news(all_raw_news)
                logger.info(f"成功存储 {inserted_count} 条原始新闻")
            else:
                logger.warning("没有采集到任何新闻")
            
            # 4.5. Dify工作流审核（按zipcode分组）
            if inserted_records:
                logger.info("=" * 50)
                logger.info("开始Dify工作流审核流程")
                logger.info("=" * 50)
                await self._process_dify_review(inserted_records)
                logger.info("=" * 50)
            
            # 5. 导出JSON
            if all_raw_news:
                json_path = self.json_exporter.export_by_date_and_source(all_raw_news)
                logger.info(f"JSON导出完成: {json_path}")
            
            logger.info("=" * 50)
            logger.info("采集任务完成")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"采集任务执行失败: {str(e)}", exc_info=True)
            await self.notification_service.send_failure_notification(
                task_type="full_task",
                error_message=str(e)
            )
            raise


async def main():
    """主函数"""
    coordinator = ScraperCoordinator()
    
    # Debug模式：直接执行所有激活源的采集任务，忽略调度器
    if settings.debug_mode:
        logger.info("=" * 50)
        logger.info("DEBUG模式已启用 - 直接执行所有激活源的采集任务")
        logger.info("=" * 50)
        await coordinator.run_scraping_task()
        logger.info("DEBUG模式执行完成")
        return
    
    # 如果调度器启用，设置多源独立调度
    scheduler_manager = SchedulerManager()
    if scheduler_manager.is_scheduler_enabled():
        # 加载信号源配置
        sources = await coordinator.load_sources_from_db()
        
        if sources:
            # 为每个源创建独立的调度任务
            await scheduler_manager.add_source_jobs(
                sources,
                coordinator.run_scraping_task
            )
            scheduler_manager.start()
            
            logger.info("调度器已启动，程序将持续运行...")
            logger.info(f"已为 {len(sources)} 个信号源创建调度任务")
            logger.info("按 Ctrl+C 停止")
            
            try:
                # 保持程序运行
                while True:
                    await asyncio.sleep(60)
            except KeyboardInterrupt:
                logger.info("收到停止信号，正在关闭...")
                scheduler_manager.stop()
        else:
            logger.warning("没有找到激活的信号源，无法启动调度器")
            # 手动触发一次
            await coordinator.run_scraping_task()
    else:
        # 手动触发一次
        logger.info("调度器未启用，执行一次采集任务")
        await coordinator.run_scraping_task()


if __name__ == "__main__":
    asyncio.run(main())

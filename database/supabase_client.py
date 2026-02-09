"""
Supabase数据库客户端封装
提供CRUD操作，支持play_news_sources和play_raw_news表
"""
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from config.settings import settings
from utils.logger import logger
from utils.data_cleaner import DataCleaner


class DatabaseManager:
    """Supabase数据库管理器"""
    
    def __init__(self):
        """初始化Supabase客户端"""
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_key,
            options=ClientOptions(
                auto_refresh_token=True,
                persist_session=True
            )
        )
        self.data_cleaner = DataCleaner()  # 用于URL标准化
        logger.info("Supabase客户端初始化成功")
    
    async def get_active_sources(self) -> List[Dict[str, Any]]:
        """
        获取所有激活的信号源配置
        
        Returns:
            激活的信号源列表
        """
        try:
            # 使用asyncio.to_thread包装同步调用，避免阻塞事件循环
            response = await asyncio.to_thread(
                lambda: self.client.table('play_news_sources').select('*').eq('is_active', True).execute()
            )
            sources = response.data if response.data else []
            logger.info(f"获取到 {len(sources)} 个激活的信号源")
            return sources
        except Exception as e:
            logger.error(f"获取激活信号源失败: {str(e)}", exc_info=True)
            return []
    
    async def get_zipcodes_from_magnet(self) -> List[str]:
        """
        从 magnet 表查询非空 zip_code 并去重，等价 SQL：
        select zip_code from magnet where zip_code is not null group by zip_code
        
        Returns:
            去重后的 zip_code 列表（字符串），异常或无数据时返回 []
        """
        try:
            response = await asyncio.to_thread(
                lambda: self.client.table('magnet')
                .select('zip_code')
                .not_.is_('zip_code', 'null')
                .execute()
            )
            rows = response.data if response.data else []
            # 去重并统一转为 str（兼容 DB 返回数值类型）
            seen = set()
            zipcodes = []
            for row in rows:
                z = row.get('zip_code')
                if z is not None and str(z).strip():
                    key = str(z).strip()
                    if key not in seen:
                        seen.add(key)
                        zipcodes.append(key)
            logger.info(f"从 magnet 表加载了 {len(zipcodes)} 个 Zipcode")
            return zipcodes
        except Exception as e:
            logger.error(f"从 magnet 获取 Zipcode 失败: {str(e)}", exc_info=True)
            return []
    
    async def _check_existing_urls(self, normalized_urls: List[str], original_urls: List[str]) -> set:
        """
        批量查询已存在的URL（基于标准化URL比较）
        
        Args:
            normalized_urls: 标准化后的URL列表（用于比较）
            original_urls: 原始URL列表（用于数据库查询）
            
        Returns:
            已存在标准化URL的集合
        """
        if not normalized_urls or not original_urls or len(normalized_urls) != len(original_urls):
            return set()
        
        try:
            # 先查询数据库中所有可能的URL（使用原始URL的IN查询）
            # 注意：Supabase的IN查询有长度限制，需要分批处理
            batch_size = 100  # 每批最多100个URL
            existing_normalized_urls = set()
            
            # 创建原始URL到标准化URL的映射
            url_mapping = dict(zip(original_urls, normalized_urls))
            
            for i in range(0, len(original_urls), batch_size):
                batch_original_urls = original_urls[i:i + batch_size]
                
                def query_batch():
                    return self.client.table('play_raw_news').select('url').in_('url', batch_original_urls).execute()
                
                response = await asyncio.to_thread(query_batch)
                
                if response.data:
                    # 获取数据库中的URL，标准化后与待插入的标准化URL比较
                    for record in response.data:
                        db_url = record.get('url')
                        if db_url:
                            # 标准化数据库中的URL
                            db_normalized = self.data_cleaner.normalize_url(db_url)
                            if db_normalized:
                                existing_normalized_urls.add(db_normalized)
            
            logger.debug(f"URL存在性检查完成: 检查 {len(normalized_urls)} 个URL，发现 {len(existing_normalized_urls)} 个已存在")
            return existing_normalized_urls
            
        except Exception as e:
            logger.warning(f"查询已存在URL失败: {str(e)}，将允许继续插入")
            # 如果查询失败，返回空集合，允许继续插入（避免因查询失败导致数据丢失）
            return set()
    
    async def insert_raw_news(self, raw_news_list: List[Dict[str, Any]]) -> Tuple[int, List[Dict[str, Any]]]:
        """
        批量插入原始新闻到play_raw_news表
        
        Args:
            raw_news_list: 原始新闻列表，每个新闻包含：
                - source_id: 信号源ID（必需）
                - city: 城市名称（必需）
                - zip_code: 邮政编码（可选，来自 magnet 表或局部新闻采集）
                - title: 标题（必需）
                - content: 完整内容（可选）
                - publish_date: 发布时间（可选）
                - url: 链接（必需）
                - language: 语言（默认'en'）
                - raw_category: 原始分类标签（可选）
                - status: 状态（默认'new'）
                
        Returns:
            元组 (插入数量, 插入的记录列表)，记录列表包含自动生成的id
        """
        if not raw_news_list:
            return (0, [])
        
        inserted_count = 0
        inserted_records = []
        errors = []
        
        try:
            # 准备数据，添加时间戳
            now = datetime.utcnow().isoformat()
            for news in raw_news_list:
                news['crawl_time'] = now
                news['created_at'] = now
                news['updated_at'] = now
                # 设置默认值
                if 'language' not in news:
                    news['language'] = 'en'
                if 'status' not in news:
                    news['status'] = 'new'
            
            # 检查已存在的URL（数据库层去重）
            # 标准化所有URL用于检查
            normalized_urls = []
            original_urls = []
            normalized_to_news_map = {}
            for news in raw_news_list:
                url = news.get('url', '')
                if url:
                    normalized_url = self.data_cleaner.normalize_url(url)
                    if normalized_url:
                        normalized_urls.append(normalized_url)
                        original_urls.append(url)
                        # 保存标准化URL到记录的映射
                        normalized_to_news_map[normalized_url] = news
            
            # 查询已存在的URL（基于标准化URL比较）
            existing_normalized_urls = await self._check_existing_urls(normalized_urls, original_urls)
            
            # 过滤掉已存在的记录
            new_news_list = []
            skipped_count = 0
            for normalized_url, news in normalized_to_news_map.items():
                if normalized_url in existing_normalized_urls:
                    skipped_count += 1
                    logger.debug(f"跳过已存在的URL: {news.get('url', '')[:100]}")
                else:
                    new_news_list.append(news)
            
            if skipped_count > 0:
                logger.info(f"数据库层去重: 跳过 {skipped_count} 条已存在的记录，剩余 {len(new_news_list)} 条新记录")
            
            # 如果没有新记录，直接返回
            if not new_news_list:
                logger.info("所有记录都已存在，无需插入")
                return (0, [])
            
            # 批量插入新记录（使用asyncio.to_thread包装同步调用）
            response = await asyncio.to_thread(
                lambda: self.client.table('play_raw_news').insert(new_news_list).execute()
            )
            
            if response.data:
                inserted_records = response.data
                inserted_count = len(inserted_records)
            
            logger.info(f"成功插入 {inserted_count} 条原始新闻")
            
        except Exception as e:
            logger.error(f"批量插入原始新闻失败: {str(e)}", exc_info=True)
            
            # 保存失败数据到文件，防止数据丢失
            try:
                failed_data_dir = Path("logs/failed_inserts")
                failed_data_dir.mkdir(parents=True, exist_ok=True)
                failed_data_path = failed_data_dir / f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                with open(failed_data_path, 'w', encoding='utf-8') as f:
                    json.dump(raw_news_list, f, indent=2, ensure_ascii=False)
                logger.error(f"批量插入失败，数据已保存到: {failed_data_path}")
            except Exception as save_error:
                logger.error(f"保存失败数据到文件也失败: {str(save_error)}", exc_info=True)
            
            # 如果批量插入失败，尝试单条插入（用于错误定位）
            for news in raw_news_list:
                try:
                    news['crawl_time'] = datetime.utcnow().isoformat()
                    news['created_at'] = datetime.utcnow().isoformat()
                    news['updated_at'] = datetime.utcnow().isoformat()
                    if 'language' not in news:
                        news['language'] = 'en'
                    if 'status' not in news:
                        news['status'] = 'new'
                    
                    # 单条插入前也检查URL是否存在
                    url = news.get('url', '')
                    if url:
                        normalized_url = self.data_cleaner.normalize_url(url)
                        existing_urls = await self._check_existing_urls([normalized_url], [url])
                        if normalized_url in existing_urls:
                            logger.debug(f"单条插入跳过已存在的URL: {url[:100]}")
                            continue
                    
                    # 单条插入也使用异步包装
                    single_response = await asyncio.to_thread(
                        lambda: self.client.table('play_raw_news').insert(news).execute()
                    )
                    if single_response.data:
                        inserted_records.extend(single_response.data)
                    inserted_count += 1
                except Exception as single_error:
                    error_info = {
                        'url': news.get('url', 'unknown'),
                        'error': str(single_error)
                    }
                    errors.append(error_info)
                    logger.warning(f"单条插入失败: {error_info}")
            
            if errors:
                logger.warning(f"部分原始新闻插入失败: {len(errors)} 条", extra={'errors': errors})
        
        return (inserted_count, inserted_records)
    
    async def get_recent_raw_news(
        self,
        days: int = 7,
        zip_code: Optional[str] = None,
        source_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取最近的原始新闻
        
        Args:
            days: 最近天数
            zip_code: 过滤Zipcode（可选）
            source_id: 过滤信号源ID（可选）
            status: 过滤状态（可选：'new', 'filtered', 'scored'）
            limit: 返回数量限制
            
        Returns:
            原始新闻列表
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            cutoff_iso = cutoff_date.isoformat()
            
            # 构建并执行查询（使用异步包装整个查询链）
            def build_and_execute_query():
                query = self.client.table('play_raw_news').select('*').gte('publish_date', cutoff_iso)
                if zip_code:
                    query = query.eq('zip_code', zip_code)
                if source_id:
                    query = query.eq('source_id', source_id)
                if status:
                    query = query.eq('status', status)
                return query.order('publish_date', desc=True).limit(limit).execute()
            
            response = await asyncio.to_thread(build_and_execute_query)
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"查询最近原始新闻失败: {str(e)}", exc_info=True)
            return []
    
    async def log_task(
        self,
        task_type: str,
        status: str,
        source_id: Optional[int] = None,
        zipcode: Optional[str] = None,
        source: Optional[str] = None,
        articles_count: int = 0,
        error_message: Optional[str] = None
    ) -> str:
        """
        记录任务日志
        
        Args:
            task_type: 任务类型 ('local_news' 或 'real_estate')
            status: 任务状态 ('running', 'success', 'failed')
            source_id: 信号源ID（外键关联play_news_sources.id）
            zipcode: Zipcode（仅local_news任务，向后兼容）
            source: 来源网站（仅real_estate任务，向后兼容）
            articles_count: 采集的文章数量
            error_message: 错误信息（如果失败）
            
        Returns:
            任务日志ID
        """
        try:
            task_log = {
                'task_type': task_type,
                'status': status,
                'articles_count': articles_count,
                'started_at': datetime.utcnow().isoformat(),
            }
            
            if source_id:
                task_log['source_id'] = source_id
            if zipcode:
                task_log['zipcode'] = zipcode
            if source:
                task_log['source'] = source
            if error_message:
                task_log['error_message'] = error_message
            if status in ['success', 'failed']:
                task_log['completed_at'] = datetime.utcnow().isoformat()
            
            response = await asyncio.to_thread(
                lambda: self.client.table('task_logs').insert(task_log).execute()
            )
            task_id = response.data[0]['id'] if response.data else None
            
            logger.info(f"任务日志已记录: {task_type} - {status} - {articles_count} 篇文章")
            return task_id
            
        except Exception as e:
            logger.error(f"记录任务日志失败: {str(e)}", exc_info=True)
            return ""
    
    async def update_task_log(
        self,
        task_id: str,
        status: str,
        articles_count: int = 0,
        error_message: Optional[str] = None,
        source_id: Optional[int] = None
    ):
        """
        更新任务日志
        
        Args:
            task_id: 任务日志ID
            status: 新状态
            articles_count: 文章数量
            error_message: 错误信息
            source_id: 信号源ID（可选）
        """
        try:
            update_data = {
                'status': status,
                'articles_count': articles_count,
                'completed_at': datetime.utcnow().isoformat()
            }
            
            if error_message:
                update_data['error_message'] = error_message
            if source_id:
                update_data['source_id'] = source_id
            
            await asyncio.to_thread(
                lambda: self.client.table('task_logs').update(update_data).eq('id', task_id).execute()
            )
            logger.debug(f"任务日志已更新: {task_id} - {status}")
            
        except Exception as e:
            logger.error(f"更新任务日志失败: {str(e)}", exc_info=True)


# 全局数据库管理器实例
db_manager = DatabaseManager()

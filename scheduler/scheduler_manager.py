"""
调度器管理模块
使用APScheduler管理定时任务，支持cron表达式和多源独立调度
"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Callable, Optional, List, Dict, Any

from config.settings import settings
from utils.logger import logger


class SchedulerManager:
    """调度器管理器"""
    
    def __init__(self):
        """初始化调度器"""
        self.scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
        self.is_running = False
    
    def create_cron_trigger(self, cron_expr: str) -> CronTrigger:
        """
        从cron表达式字符串创建CronTrigger
        
        Args:
            cron_expr: 标准5位cron表达式，如 "0 2 * * *" (每天凌晨2点)
                      格式: minute hour day month day_of_week
            
        Returns:
            CronTrigger实例
            
        Raises:
            ValueError: 如果cron表达式格式无效
        """
        try:
            # 使用from_crontab解析标准cron表达式
            trigger = CronTrigger.from_crontab(cron_expr, timezone=settings.scheduler_timezone)
            logger.debug(f"成功解析cron表达式: {cron_expr}")
            return trigger
        except Exception as e:
            logger.error(f"解析cron表达式失败: {cron_expr} - {str(e)}", exc_info=True)
            raise ValueError(f"Invalid cron expression: {cron_expr}")
    
    def add_job(
        self,
        func: Callable,
        trigger: Optional[CronTrigger] = None,
        job_id: str = "scrape_job"
    ):
        """
        添加定时任务
        
        Args:
            func: 要执行的函数
            trigger: 触发器（如果不提供，使用配置的默认值）
            job_id: 任务ID
        """
        if not trigger:
            trigger = CronTrigger(
                hour=settings.scheduler_hour,
                minute=settings.scheduler_minute,
                timezone=settings.scheduler_timezone
            )
        
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True
        )
        
        logger.info(f"定时任务已添加: {job_id} - {trigger}")
    
    async def add_source_jobs(
        self,
        sources: List[Dict[str, Any]],
        scrape_func: Callable
    ):
        """
        为每个激活的源创建独立的调度任务
        
        Args:
            sources: 信号源配置列表（从play_news_sources读取）
            scrape_func: 采集函数，接收source_id作为参数
        """
        for source in sources:
            source_id = source.get('id')
            source_name = source.get('source_name', 'unknown')
            update_frequency = source.get('update_frequency')
            is_active = source.get('is_active', True)
            
            if not is_active:
                logger.debug(f"跳过非激活源: {source_name} (ID: {source_id})")
                continue
            
            if not update_frequency:
                logger.warning(f"源 {source_name} (ID: {source_id}) 没有设置update_frequency，跳过")
                continue
            
            try:
                # 从cron表达式创建触发器
                trigger = self.create_cron_trigger(update_frequency)
                
                # 创建包装函数，传入source_id（使用默认参数避免闭包问题）
                async def scrape_with_source_id(src_id=source_id):
                    await scrape_func(src_id)
                
                # 添加调度任务（限制并发，防止同一任务重复执行）
                job_id = f"source_{source_id}"
                self.scheduler.add_job(
                    scrape_with_source_id,
                    trigger=trigger,
                    id=job_id,
                    replace_existing=True,
                    max_instances=1  # 防止同一源并发执行
                )
                
                logger.info(f"为源 {source_name} (ID: {source_id}) 创建调度任务: {update_frequency}")
                
            except Exception as e:
                logger.error(f"为源 {source_name} (ID: {source_id}) 创建调度任务失败: {str(e)}", exc_info=True)
                continue
    
    def start(self):
        """启动调度器"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("调度器已启动")
        else:
            logger.warning("调度器已在运行")
    
    def stop(self):
        """停止调度器"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("调度器已停止")
        else:
            logger.warning("调度器未运行")
    
    def is_scheduler_enabled(self) -> bool:
        """检查调度器是否启用"""
        return settings.scheduler_enabled

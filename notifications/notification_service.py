"""
通知服务模块
处理失败通知（邮件/日志）
"""
import aiosmtplib
from typing import Optional
from pathlib import Path
from datetime import datetime

from config.settings import settings
from utils.logger import logger


class NotificationService:
    """通知服务"""
    
    def __init__(self):
        """初始化通知服务"""
        self.notification_type = settings.notification_type
        self.enabled = settings.notification_enabled
    
    async def send_failure_notification(
        self,
        task_type: str,
        error_message: str,
        zipcode: Optional[str] = None,
        source: Optional[str] = None
    ):
        """
        发送失败通知
        
        Args:
            task_type: 任务类型
            error_message: 错误信息
            zipcode: Zipcode（可选）
            source: 来源网站（可选）
        """
        if not self.enabled:
            return
        
        try:
            if self.notification_type == "email":
                await self._send_email_notification(task_type, error_message, zipcode, source)
            else:
                self._log_notification(task_type, error_message, zipcode, source)
        except Exception as e:
            logger.error(f"发送通知失败: {str(e)}", exc_info=True)
    
    async def _send_email_notification(
        self,
        task_type: str,
        error_message: str,
        zipcode: Optional[str] = None,
        source: Optional[str] = None
    ):
        """发送邮件通知"""
        if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password, settings.notification_email_to]):
            logger.warning("邮件配置不完整，无法发送邮件通知")
            return
        
        try:
            # 构建邮件内容
            subject = f"[RState News] 采集任务失败 - {task_type}"
            body = f"""
采集任务执行失败

任务类型: {task_type}
失败时间: {datetime.utcnow().isoformat()}
错误信息: {error_message}
"""
            if zipcode:
                body += f"Zipcode: {zipcode}\n"
            if source:
                body += f"来源网站: {source}\n"
            
            # 发送邮件
            message = f"""From: {settings.smtp_user}
To: {settings.notification_email_to}
Subject: {subject}

{body}
"""
            
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                use_tls=True
            )
            
            logger.info(f"邮件通知已发送: {subject}")
            
        except Exception as e:
            logger.error(f"发送邮件失败: {str(e)}", exc_info=True)
    
    def _log_notification(
        self,
        task_type: str,
        error_message: str,
        zipcode: Optional[str] = None,
        source: Optional[str] = None
    ):
        """记录日志通知"""
        notification_msg = f"""
========== 采集任务失败通知 ==========
任务类型: {task_type}
失败时间: {datetime.utcnow().isoformat()}
错误信息: {error_message}
"""
        if zipcode:
            notification_msg += f"Zipcode: {zipcode}\n"
        if source:
            notification_msg += f"来源网站: {source}\n"
        notification_msg += "=" * 40
        
        logger.error(notification_msg)

"""
配置管理模块
负责读取环境变量和配置文件
"""
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


class Settings:
    """应用配置类"""
    
    def __init__(self):
        self._load_config()
    
    def _load_config(self):
        """加载配置文件（如果存在）"""
        config_file = PROJECT_ROOT / "config.json"
        self._config = {}
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
    
    def _get_env_or_config(self, key: str, default: Any = None) -> Any:
        """优先从环境变量读取，其次从config.json读取"""
        return os.getenv(key) or self._config.get(key, default)
    
    # Supabase配置
    @property
    def supabase_url(self) -> str:
        """Supabase项目URL"""
        url = self._get_env_or_config("SUPABASE_URL")
        if not url:
            raise ValueError("SUPABASE_URL未配置，请在.env文件中设置")
        return url
    
    @property
    def supabase_key(self) -> str:
        """Supabase匿名密钥"""
        key = self._get_env_or_config("SUPABASE_KEY")
        if not key:
            raise ValueError("SUPABASE_KEY未配置，请在.env文件中设置")
        return key
    
    # Debug模式配置
    @property
    def debug_mode(self) -> bool:
        """是否启用Debug模式（直接执行，忽略调度器）"""
        return self._get_env_or_config("DEBUG_MODE", "false").lower() == "true"
    
    # 调度器配置
    @property
    def scheduler_enabled(self) -> bool:
        """是否启用调度器"""
        return self._get_env_or_config("SCHEDULER_ENABLED", "true").lower() == "true"
    
    @property
    def scheduler_timezone(self) -> str:
        """调度器时区"""
        return self._get_env_or_config("SCHEDULER_TIMEZONE", "America/New_York")
    
    @property
    def scheduler_hour(self) -> int:
        """调度器运行小时（0-23）"""
        return int(self._get_env_or_config("SCHEDULER_HOUR", "2"))
    
    @property
    def scheduler_minute(self) -> int:
        """调度器运行分钟（0-59）"""
        return int(self._get_env_or_config("SCHEDULER_MINUTE", "0"))
    
    # 采集配置
    @property
    def scrape_delay_min(self) -> int:
        """采集延迟最小值（秒）"""
        return int(self._get_env_or_config("SCRAPE_DELAY_MIN", "1"))
    
    @property
    def scrape_delay_max(self) -> int:
        """采集延迟最大值（秒）"""
        return int(self._get_env_or_config("SCRAPE_DELAY_MAX", "3"))
    
    @property
    def scrape_retry_max(self) -> int:
        """最大重试次数"""
        return int(self._get_env_or_config("SCRAPE_RETRY_MAX", "3"))
    
    @property
    def scrape_time_range_days(self) -> int:
        """采集时间范围（天数）"""
        return int(self._get_env_or_config("SCRAPE_TIME_RANGE_DAYS", "7"))

    # Realtor.com 专用配置（反风控画像）
    @property
    def realtor_locale(self) -> str:
        """Realtor.com 浏览器 locale（用户要求 en-US）"""
        return self._get_env_or_config("REALTOR_LOCALE", "en-US")

    @property
    def realtor_accept_language(self) -> str:
        """Realtor.com Accept-Language（用户要求 en-US）"""
        return self._get_env_or_config("REALTOR_ACCEPT_LANGUAGE", "en-US,en;q=0.9")

    @property
    def realtor_timezone_id(self) -> str:
        """
        Realtor.com timezone_id。
        需要与 locale/UA 保持一致，避免“语言/时区/平台”互相矛盾。
        """
        return self._get_env_or_config("REALTOR_TIMEZONE_ID", "America/Los_Angeles")

    @property
    def realtor_user_agent(self) -> str:
        """Realtor.com 固定 UA（macOS + Chrome，避免随机 Windows UA）"""
        return self._get_env_or_config(
            "REALTOR_USER_AGENT",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

    @property
    def realtor_manual_gate_seconds(self) -> int:
        """
        首次人工放行等待时间（秒）。
        0 表示不等待（自动继续）。
        """
        return int(self._get_env_or_config("REALTOR_MANUAL_GATE_SECONDS", "0"))

    @property
    def realtor_min_request_interval_seconds(self) -> float:
        """Realtor.com 最小请求间隔（秒），用于降低短时间请求密度"""
        return float(self._get_env_or_config("REALTOR_MIN_REQUEST_INTERVAL_SECONDS", "2.0"))

    @property
    def realtor_block_settlement_seconds(self) -> float:
        """
        封禁页“过渡等待”秒数。
        Realtor 有时先返回封禁/等待页，约 2s 后由前端替换为正常内容；在此时间内不判定为封禁。
        """
        return float(self._get_env_or_config("REALTOR_BLOCK_SETTLEMENT_SECONDS", "4.0"))
    
    # 通知配置
    @property
    def notification_enabled(self) -> bool:
        """是否启用通知"""
        return self._get_env_or_config("NOTIFICATION_ENABLED", "true").lower() == "true"
    
    @property
    def notification_type(self) -> str:
        """通知类型：log 或 email"""
        return self._get_env_or_config("NOTIFICATION_TYPE", "log").lower()
    
    # 邮件配置
    @property
    def smtp_host(self) -> Optional[str]:
        """SMTP服务器地址"""
        return self._get_env_or_config("SMTP_HOST")
    
    @property
    def smtp_port(self) -> int:
        """SMTP端口"""
        return int(self._get_env_or_config("SMTP_PORT", "587"))
    
    @property
    def smtp_user(self) -> Optional[str]:
        """SMTP用户名"""
        return self._get_env_or_config("SMTP_USER")
    
    @property
    def smtp_password(self) -> Optional[str]:
        """SMTP密码"""
        return self._get_env_or_config("SMTP_PASSWORD")
    
    @property
    def notification_email_to(self) -> Optional[str]:
        """通知接收邮箱"""
        return self._get_env_or_config("NOTIFICATION_EMAIL_TO")
    
    # 日志配置
    @property
    def log_level(self) -> str:
        """日志级别"""
        return self._get_env_or_config("LOG_LEVEL", "INFO").upper()
    
    @property
    def log_file(self) -> Path:
        """日志文件路径"""
        log_path = self._get_env_or_config("LOG_FILE", "logs/scraper.log")
        return PROJECT_ROOT / log_path
    
    @property
    def log_max_bytes(self) -> int:
        """日志文件最大字节数"""
        return int(self._get_env_or_config("LOG_MAX_BYTES", "10485760"))
    
    @property
    def log_backup_count(self) -> int:
        """日志备份文件数量"""
        return int(self._get_env_or_config("LOG_BACKUP_COUNT", "5"))
    
    # CSV配置路径
    @property
    def zipcode_csv_path(self) -> Path:
        """Zipcode CSV文件路径"""
        return PROJECT_ROOT / "config.csv"


# 全局配置实例
settings = Settings()

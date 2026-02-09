"""
JSON导出模块
将采集结果导出为JSON文件（支持play_raw_news格式）
"""
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict

from config.settings import settings
from utils.logger import logger


class JSONExporter:
    """JSON导出器"""
    
    def __init__(self, output_dir: Path = None):
        """
        初始化导出器
        
        Args:
            output_dir: 输出目录（默认使用项目根目录/output）
        """
        if output_dir is None:
            output_dir = Path(settings.zipcode_csv_path.parent) / "output"
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_by_date_and_source(
        self,
        articles: List[Dict[str, Any]],
        filename: str = None
    ) -> Path:
        """
        按日期和来源分组导出JSON（支持play_raw_news格式）
        
        Args:
            articles: 文章列表（可以是play_raw_news格式或旧格式）
            filename: 输出文件名（如果不提供，使用时间戳）
            
        Returns:
            输出文件路径
        """
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"raw_news_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        # 按日期和来源分组
        grouped = defaultdict(lambda: defaultdict(list))
        
        for article in articles:
            publish_date = article.get('publish_date', 'unknown')
            # 优先使用source字段（字符串），如果没有则使用source_id
            source = article.get('source', f"source_id_{article.get('source_id', 'unknown')}")
            
            # 提取日期部分（YYYY-MM-DD）
            try:
                date_part = publish_date.split('T')[0] if 'T' in publish_date else publish_date[:10]
            except Exception as e:
                logger.debug(f"解析日期失败: {str(e)}")
                date_part = 'unknown'
            
            grouped[date_part][source].append(article)
        
        # 转换为列表格式
        result = {
            'exported_at': datetime.utcnow().isoformat(),
            'total_articles': len(articles),
            'grouped_by_date_and_source': {
                date: {
                    source: articles_list
                    for source, articles_list in sources.items()
                }
                for date, sources in grouped.items()
            }
        }
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON导出完成: {output_path} ({len(articles)} 条原始新闻)")
        
        return output_path
    
    def export_simple(self, articles: List[Dict[str, Any]], filename: str = None) -> Path:
        """
        简单导出（不分组，支持play_raw_news格式）
        
        Args:
            articles: 文章列表（可以是play_raw_news格式）
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"raw_news_simple_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        result = {
            'exported_at': datetime.utcnow().isoformat(),
            'total_articles': len(articles),
            'articles': articles
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON导出完成: {output_path} ({len(articles)} 条原始新闻)")
        
        return output_path

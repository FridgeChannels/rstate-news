"""
局部新闻采集器基类
处理基于Zipcode的新闻采集
"""
from typing import List, Dict, Any
from scrapers.base_scraper import BaseScraper
from utils.logger import logger


class LocalNewsScraper(BaseScraper):
    """局部新闻采集器基类"""
    
    def __init__(self, source_name: str):
        """
        初始化局部新闻采集器
        
        Args:
            source_name: 来源网站名称
        """
        super().__init__(source_name)
    
    async def scrape(self, zipcode: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        采集指定Zipcode的局部新闻
        
        Args:
            zipcode: 邮政编码
            limit: 采集数量限制
            
        Returns:
            文章列表
        """
        logger.info(f"{self.source_name}: 开始采集Zipcode {zipcode} 的新闻")
        
        try:
            articles = await self._scrape_zipcode_news(zipcode, limit)
            logger.info(f"{self.source_name}: Zipcode {zipcode} 采集完成，获得 {len(articles)} 篇文章")
            return articles
        except Exception as e:
            logger.error(f"{self.source_name}: Zipcode {zipcode} 采集失败: {str(e)}", exc_info=True)
            return []
    
    async def _scrape_zipcode_news(self, zipcode: str, limit: int) -> List[Dict[str, Any]]:
        """
        子类需要实现的具体采集逻辑
        
        Args:
            zipcode: 邮政编码
            limit: 采集数量限制
            
        Returns:
            文章列表
        """
        raise NotImplementedError("子类必须实现 _scrape_zipcode_news 方法")

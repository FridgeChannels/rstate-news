"""
房地产新闻采集器基类
处理全国性房地产行业新闻采集
"""
from typing import List, Dict, Any
from scrapers.base_scraper import BaseScraper
from utils.logger import logger


class RealEstateScraper(BaseScraper):
    """房地产新闻采集器基类"""
    
    def __init__(self, source_name: str, base_url: str):
        """
        初始化房地产新闻采集器
        
        Args:
            source_name: 来源网站名称
            base_url: 网站基础URL
        """
        super().__init__(source_name)
        self.base_url = base_url
    
    async def scrape(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        采集房地产新闻
        
        Args:
            limit: 采集数量限制
            
        Returns:
            文章列表
        """
        logger.info(f"{self.source_name}: 开始采集房地产新闻")
        
        try:
            articles = await self._scrape_real_estate_news(limit)
            logger.info(f"{self.source_name}: 采集完成，获得 {len(articles)} 篇文章")
            return articles
        except Exception as e:
            logger.error(f"{self.source_name}: 采集失败: {str(e)}", exc_info=True)
            return []
    
    async def _scrape_real_estate_news(self, limit: int) -> List[Dict[str, Any]]:
        """
        子类需要实现的具体采集逻辑
        
        Args:
            limit: 采集数量限制
            
        Returns:
            文章列表
        """
        raise NotImplementedError("子类必须实现 _scrape_real_estate_news 方法")

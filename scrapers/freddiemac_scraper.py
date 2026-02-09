"""
Freddie Mac采集器
采集房地产行业新闻
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from scrapers.real_estate_scraper import RealEstateScraper
from scrapers.robust_scraper_mixin import RobustScraperMixin
from utils.logger import logger


class FreddieMacScraper(RealEstateScraper, RobustScraperMixin):
    """Freddie Mac新闻采集器"""
    
    def __init__(self):
        super().__init__(
            "Freddie Mac",
            "https://freddiemac.gcs-web.com/?_gl=1*qtpff7*_gcl_au*MTY1ODc4ODI2MC4xNzY5NDkwOTAx*_ga*MTI2MTk2MjU0LjE3Njk0OTA5MDQ.*_ga_B5N0FKC09S*czE3Njk0OTA5MDQkbzEkZzEkdDE3Njk0OTA5MDQkajYwJGwwJGgw"
        )
    
    async def _scrape_real_estate_news(self, limit: int = 20) -> List[Dict[str, Any]]:
        """采集Freddie Mac的房地产新闻"""
        articles = []
        page = None
        
        try:
            await self._setup_browser(headless=True)
            page = await self._create_page()
            
            logger.debug(f"访问: {self.base_url}")
            
            await page.goto(self.base_url, wait_until="networkidle", timeout=30000)
            await self._random_delay()
            
            # 使用多种备选选择器，优先使用Drupal特定选择器
            article_selectors = [
                "article.node.node--type-nir-news",   # Drupal特定选择器
                "article.node",                      # 更宽松的Drupal选择器
                "article",
                ".article-card",
                ".news-item",
                "[data-testid='article']",
                ".press-release",
                ".card",
                "div[class*='article']",
                "div[class*='press']"
            ]
            
            # 尝试等待任一选择器
            for selector in article_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    break
                except Exception as e:
                    logger.debug(f"等待选择器 {selector} 超时: {str(e)}")
                    continue
            
            # 使用robust方法查找元素
            article_elements = await self.find_elements_with_fallback(page, article_selectors)
            
            logger.debug(f"找到 {len(article_elements)} 个文章元素")
            
            for i, element in enumerate(article_elements[:limit]):
                try:
                    article = await self._extract_article_data(element)
                    if article:
                        articles.append(article)
                        await self._random_delay(0.5, 1.5)
                except Exception as e:
                    logger.warning(f"提取第 {i+1} 篇文章失败: {str(e)}", exc_info=True)
                    continue
            
        except Exception as e:
            logger.error(f"Freddie Mac采集过程出错: {str(e)}", exc_info=True)
        finally:
            # 确保页面和浏览器资源都被清理
            # 注意：不需要单独关闭page，cleanup()会关闭整个context（包括所有页面）
            await self.cleanup()
        
        return articles
    
    async def extract_article_data_robust(self, element, zipcode=None) -> Optional[Dict[str, Any]]:
        """
        使用Freddie Mac特定的Drupal选择器提取文章数据
        优先使用Drupal框架的精确选择器，失败后回退到通用fallback
        
        Args:
            element: 文章元素
            zipcode: 邮政编码（可选，Freddie Mac不使用）
            
        Returns:
            文章数据字典
        """
        try:
            # 标题 - 优先使用Drupal选择器
            title = await self.find_element_with_fallback(
                element,
                [
                    "h3.nir-widget--news--headline > a",  # Drupal特定选择器
                    "h3.nir-widget--news--headline",      # 如果没有链接
                    "h1", "h2", "h3", "h4",              # 通用fallback
                    ".title", ".headline", ".article-title", ".post-title",
                    "[data-testid*='title']",
                    "a[href] > *:first-child",
                    "a.title", "a.headline"
                ]
            )
            
            # 链接 - 优先使用Drupal选择器
            link_elem = await self.find_element_with_fallback(
                element,
                [
                    "h3.nir-widget--news--headline > a",  # Drupal标题链接
                    "a[href]",
                    "a.article-link",
                    "a[href*='/news']",
                    "a[href*='/article']",
                    "a[href*='/story']",
                    ".title a",
                    ".headline a"
                ],
                extract_text=False
            )
            
            url = ""
            if link_elem:
                href = await link_elem.get_attribute("href")
                if href:
                    url = href
            
            # 日期 - 优先使用Drupal选择器
            date_elem = await self.find_element_with_fallback(
                element,
                [
                    ".nir-widget--news--date-time.article-date",  # Drupal特定选择器
                    ".nir-widget--news--date-time",               # 更宽松的选择器
                    "time[datetime]",
                    "time",
                    ".date", ".publish-date", ".published-date",
                    "[datetime]",
                    ".timestamp",
                    "[data-testid*='date']",
                    ".meta time",
                    ".byline time"
                ],
                extract_text=False
            )
            
            publish_date = None
            if date_elem:
                datetime_attr = await date_elem.get_attribute("datetime")
                if datetime_attr:
                    publish_date = datetime_attr
                else:
                    date_text = await date_elem.inner_text()
                    if date_text:
                        publish_date = date_text.strip()
            
            # 摘要 - 优先使用Drupal选择器
            summary = await self.find_element_with_fallback(
                element,
                [
                    ".nir-widget--news--teaser",      # Drupal特定选择器
                    ".summary", ".excerpt", ".description",
                    ".article-summary", ".post-excerpt",
                    "p:not(.title):not(.headline)",
                    ".snippet", ".preview"
                ]
            )
            
            # 验证必需字段
            if not title or not url:
                # 如果特定选择器失败，回退到通用方法
                logger.debug("Freddie Mac特定选择器失败，回退到通用fallback")
                return await super().extract_article_data_robust(element, zipcode)
            
            return {
                "title": title,
                "url": url,
                "publish_date": publish_date or "",
                "content": summary or "",
                "content_summary": summary or "",
                "keywords": [],
                "zipcode": zipcode if zipcode else None
            }
            
        except Exception as e:
            logger.warning(f"Freddie Mac特定选择器提取失败: {str(e)}，回退到通用方法")
            return await super().extract_article_data_robust(element, zipcode)
    
    async def _extract_article_data(self, element) -> Dict[str, Any]:
        """从文章元素中提取数据（使用健壮的多选择器机制）"""
        try:
            # 使用robust mixin提取数据（现在会优先使用Freddie Mac特定选择器）
            article_data = await self.extract_article_data_robust(element)
            
            if not article_data:
                return None
            
            # 处理URL
            url = article_data.get('url', '')
            if url and not url.startswith('http'):
                url = f"https://freddiemac.gcs-web.com{url}" if url.startswith('/') else f"https://freddiemac.gcs-web.com/{url}"
            
            # 解析日期
            publish_date = article_data.get('publish_date', '')
            if publish_date:
                try:
                    from dateutil import parser
                    publish_date = parser.parse(publish_date).isoformat()
                except Exception as e:
                    logger.debug(f"日期解析失败: {publish_date} - {str(e)}")
                    publish_date = datetime.utcnow().isoformat()
            else:
                publish_date = datetime.utcnow().isoformat()
            
            return {
                "source": self.source_name,
                "title": article_data.get('title', ''),
                "url": url,
                "publish_date": publish_date,
                "content": article_data.get('content', ''),
                "content_summary": article_data.get('content_summary', ''),
                "keywords": article_data.get('keywords', [])
            }
            
        except Exception as e:
            logger.warning(f"提取文章数据失败: {str(e)}")
            return None

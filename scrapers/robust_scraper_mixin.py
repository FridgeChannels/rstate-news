"""
健壮的Scraper混入类
提供多种备选选择器，提高元素提取成功率
"""
from typing import List, Optional, Dict, Any
from utils.logger import logger


class RobustScraperMixin:
    """健壮的Scraper混入类，提供多选择器尝试机制"""
    
    async def find_element_with_fallback(
        self,
        element,
        selectors: List[str],
        extract_text: bool = True
    ) -> Optional[Any]:
        """
        使用多个备选选择器查找元素
        
        Args:
            element: 父元素
            selectors: 选择器列表（按优先级排序）
            extract_text: 是否提取文本内容
            
        Returns:
            找到的元素或文本，如果都失败返回None
        """
        for selector in selectors:
            try:
                found = await element.query_selector(selector)
                if found and await found.is_visible():
                    if extract_text:
                        text = await found.inner_text()
                        if text and text.strip():
                            return text.strip()
                    else:
                        return found
            except Exception as e:
                logger.debug(f"选择器 {selector} 查找失败: {str(e)}")
                continue
        return None
    
    async def find_elements_with_fallback(
        self,
        page,
        selectors: List[str],
        min_count: int = 3
    ) -> List:
        """
        使用多个备选选择器查找元素列表
        
        Args:
            page: Playwright页面对象
            selectors: 选择器列表（按优先级排序）
            min_count: 最少找到的元素数量
            
        Returns:
            找到的元素列表
        """
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    # 检查可见元素数量
                    visible_count = 0
                    visible_elements = []
                    for elem in elements:
                        try:
                            if await elem.is_visible():
                                # 检查是否包含链接（文章通常有链接）
                                link = await elem.query_selector("a[href]")
                                if link:
                                    visible_count += 1
                                    visible_elements.append(elem)
                        except Exception as e:
                            logger.debug(f"检查元素可见性失败: {str(e)}")
                            continue
                    
                    if visible_count >= min_count:
                        logger.debug(f"找到 {visible_count} 个可见文章元素 (选择器: {selector})")
                        return visible_elements
            except Exception as e:
                logger.debug(f"选择器 {selector} 查找失败: {str(e)}")
                continue
        
        return []
    
    async def extract_article_data_robust(
        self,
        element,
        zipcode: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        使用多种备选选择器提取文章数据
        
        Args:
            element: 文章元素
            zipcode: 邮政编码（可选）
            
        Returns:
            文章数据字典
        """
        try:
            # 标题 - 多种备选选择器
            title = await self.find_element_with_fallback(
                element,
                [
                    "h1", "h2", "h3", "h4",
                    ".title", ".headline", ".article-title", ".post-title",
                    "[data-testid*='title']",
                    "a[href] > *:first-child",
                    "a.title", "a.headline"
                ]
            )
            
            # 链接 - 多种备选选择器
            link_elem = await self.find_element_with_fallback(
                element,
                [
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
            
            # 日期 - 多种备选选择器
            date_elem = await self.find_element_with_fallback(
                element,
                [
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
            
            # 摘要 - 多种备选选择器
            summary = await self.find_element_with_fallback(
                element,
                [
                    ".summary", ".excerpt", ".description",
                    ".article-summary", ".post-excerpt",
                    "p:not(.title):not(.headline)",
                    ".snippet", ".preview"
                ]
            )
            
            # 验证必需字段
            if not title or not url:
                return None
            
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
            logger.warning(f"提取文章数据失败: {str(e)}")
            return None

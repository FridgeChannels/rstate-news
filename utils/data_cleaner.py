"""
数据清洗模块
提供日期标准化、HTML清理、关键词提取等功能
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse, parse_qs
from bs4 import BeautifulSoup
from dateutil import parser

from utils.logger import logger


class DataCleaner:
    """数据清洗器"""
    
    # 房地产相关关键词模式
    KEYWORD_PATTERNS = [
        r'房价|house price|home price',
        r'成交|sale|transaction',
        r'新规|regulation|policy',
        r'利率|interest rate|mortgage rate',
        r'市场|market',
        r'投资|investment',
        r'贷款|loan|mortgage',
        r'租金|rent|rental',
        r'供应|supply|inventory',
        r'需求|demand',
    ]
    
    def __init__(self, time_range_days: int = 7):
        """
        初始化数据清洗器
        
        Args:
            time_range_days: 时间范围过滤（天数）
        """
        self.time_range_days = time_range_days
        # 使用offset-aware时间，避免比较错误
        self.cutoff_date = datetime.now(timezone.utc) - timedelta(days=time_range_days)
    
    def clean_html(self, html_content: str) -> str:
        """
        清理HTML标签，提取纯文本
        
        Args:
            html_content: HTML内容
            
        Returns:
            清理后的纯文本
        """
        if not html_content:
            return ""
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            text = soup.get_text(separator=' ', strip=True)
            # 清理多余的空白字符
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        except Exception as e:
            logger.warning(f"HTML清理失败: {str(e)}")
            # 如果BeautifulSoup失败，使用简单正则
            return re.sub(r'<[^>]+>', '', html_content).strip()
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """
        标准化URL格式，用于去重
        
        统一URL格式：
        - 统一http/https协议（统一为https）
        - 去除URL查询参数（?后的内容）
        - 去除URL fragment（#后的内容）
        - 去除末尾斜杠（保留根路径的斜杠）
        - 统一大小写（域名部分）
        
        Args:
            url: 原始URL
            
        Returns:
            标准化后的URL
        """
        if not url:
            return ""
        
        url = url.strip()
        
        try:
            # 解析URL
            parsed = urlparse(url)
            
            # 统一协议为https
            scheme = "https" if parsed.scheme in ["http", "https"] else parsed.scheme
            
            # 统一域名大小写（小写）
            netloc = parsed.netloc.lower()
            
            # 处理路径：去除末尾斜杠（除非是根路径）
            path = parsed.path.rstrip('/') if parsed.path != '/' else '/'
            
            # 去除查询参数和fragment
            query = ""
            fragment = ""
            
            # 重新构建URL
            normalized = urlunparse((scheme, netloc, path, parsed.params, query, fragment))
            
            return normalized
            
        except Exception as e:
            logger.warning(f"URL标准化失败: {url} - {str(e)}")
            # 如果解析失败，返回原始URL（去除查询参数和fragment的简单处理）
            url = url.split('?')[0].split('#')[0].rstrip('/')
            return url if url else ""
    
    def normalize_date(self, date_str: str) -> Optional[str]:
        """
        标准化日期格式为ISO 8601
        
        Args:
            date_str: 日期字符串（各种格式）
            
        Returns:
            ISO格式日期字符串，如果解析失败返回None
        """
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # 处理相对时间
        now = datetime.utcnow()
        date_lower = date_str.lower()
        
        if "just now" in date_lower or "now" in date_lower:
            return now.isoformat()
        elif "minute" in date_lower:
            minutes = int(re.search(r'(\d+)', date_str).group(1)) if re.search(r'(\d+)', date_str) else 0
            return (now - timedelta(minutes=minutes)).isoformat()
        elif "hour" in date_lower:
            hours = int(re.search(r'(\d+)', date_str).group(1)) if re.search(r'(\d+)', date_str) else 0
            return (now - timedelta(hours=hours)).isoformat()
        elif "day" in date_lower or "yesterday" in date_lower:
            days = 1 if "yesterday" in date_lower else (int(re.search(r'(\d+)', date_str).group(1)) if re.search(r'(\d+)', date_str) else 1)
            return (now - timedelta(days=days)).isoformat()
        elif "week" in date_lower:
            weeks = int(re.search(r'(\d+)', date_str).group(1)) if re.search(r'(\d+)', date_str) else 1
            return (now - timedelta(weeks=weeks)).isoformat()
        elif "month" in date_lower:
            months = int(re.search(r'(\d+)', date_str).group(1)) if re.search(r'(\d+)', date_str) else 1
            return (now - timedelta(days=months * 30)).isoformat()
        else:
            # 尝试使用dateutil解析
            try:
                parsed_date = parser.parse(date_str)
                return parsed_date.isoformat()
            except Exception as e:
                logger.warning(f"日期解析失败: {date_str} - {str(e)}")
                return None
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取房地产相关关键词
        
        Args:
            text: 文本内容
            
        Returns:
            关键词列表
        """
        if not text:
            return []
        
        text_lower = text.lower()
        keywords = []
        
        for pattern in self.KEYWORD_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                # 去重并添加到关键词列表
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match else ""
                    if match and match not in keywords:
                        keywords.append(match)
        
        return keywords[:10]  # 限制关键词数量
    
    def filter_by_time_range(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        按时间范围过滤文章
        
        Args:
            articles: 文章列表
            
        Returns:
            过滤后的文章列表（只保留指定时间范围内的）
        """
        filtered = []
        
        for article in articles:
            publish_date_str = article.get('publish_date')
            if not publish_date_str:
                # 如果没有发布日期，跳过
                continue
            
            try:
                # 解析日期
                if isinstance(publish_date_str, str):
                    # 尝试解析ISO格式（支持Z后缀）
                    try:
                        publish_date = datetime.fromisoformat(publish_date_str.replace('Z', '+00:00'))
                    except ValueError:
                        # 如果ISO解析失败，使用dateutil
                        publish_date = parser.parse(publish_date_str)
                else:
                    publish_date = publish_date_str
                
                # 确保publish_date是offset-aware（与cutoff_date一致）
                if publish_date.tzinfo is None:
                    # 假设是UTC时间
                    publish_date = publish_date.replace(tzinfo=timezone.utc)
                
                # 检查是否在时间范围内
                if publish_date >= self.cutoff_date:
                    filtered.append(article)
                else:
                    logger.debug(f"文章超出时间范围，已过滤: {article.get('title', '')[:50]}")
                    
            except Exception as e:
                logger.warning(f"日期解析失败，保留文章: {str(e)}")
                # 如果解析失败，保留文章（避免丢失数据）
                filtered.append(article)
        
        return filtered
    
    def clean_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        清洗单篇文章数据（适配play_raw_news格式）
        
        Args:
            article: 原始文章数据（来自scraper）
            
        Returns:
            清洗后的文章数据（包含content字段，兼容content_summary）
        """
        cleaned = article.copy()
        
        # 清理HTML标签（优先处理content字段，如果没有则处理content_summary）
        if 'content' in cleaned and cleaned['content']:
            cleaned['content'] = self.clean_html(cleaned['content'])
        elif 'content_summary' in cleaned:
            # 如果没有content，将content_summary作为content
            cleaned['content'] = self.clean_html(cleaned['content_summary'])
            cleaned['content_summary'] = cleaned['content']  # 保持向后兼容
        
        # 标准化日期
        if 'publish_date' in cleaned and cleaned['publish_date']:
            normalized_date = self.normalize_date(cleaned['publish_date'])
            if normalized_date:
                cleaned['publish_date'] = normalized_date
            else:
                # 如果解析失败，使用当前时间
                cleaned['publish_date'] = datetime.utcnow().isoformat()
        
        # 提取关键词（如果没有）
        if not cleaned.get('keywords') or len(cleaned.get('keywords', [])) == 0:
            text = f"{cleaned.get('title', '')} {cleaned.get('content', '') or cleaned.get('content_summary', '')}"
            cleaned['keywords'] = self.extract_keywords(text)
        
        return cleaned
    
    def clean_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量清洗文章数据
        
        Args:
            articles: 原始文章列表
            
        Returns:
            清洗后的文章列表
        """
        cleaned_articles = []
        
        for article in articles:
            try:
                cleaned = self.clean_article(article)
                cleaned_articles.append(cleaned)
            except Exception as e:
                logger.warning(f"清洗文章失败: {str(e)}", extra={'article': article.get('url', 'unknown')})
                continue
        
        # 时间范围过滤
        filtered_articles = self.filter_by_time_range(cleaned_articles)
        
        logger.info(f"数据清洗完成: {len(articles)} -> {len(filtered_articles)} 篇文章")
        
        return filtered_articles

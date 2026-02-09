"""
文章内容获取工具模块
使用trafilatura和newspaper3k从URL提取文章真实内容
"""
import asyncio
from typing import Optional


async def _fetch_with_trafilatura(url: str, timeout: int = 30) -> Optional[str]:
    """
    使用trafilatura提取文章内容
    
    Args:
        url: 文章URL
        timeout: 超时时间（秒）
        
    Returns:
        提取的文章文本内容，失败返回None
    """
    try:
        from trafilatura import fetch_url, extract
        
        # 使用asyncio.to_thread包装同步调用
        downloaded = await asyncio.wait_for(
            asyncio.to_thread(fetch_url, url),
            timeout=timeout
        )
        
        if not downloaded:
            return None
        
        # 提取文本内容
        result = await asyncio.wait_for(
            asyncio.to_thread(extract, downloaded, output_format='text'),
            timeout=timeout
        )
        
        if result and result.strip():
            return result.strip()
        
        return None
        
    except asyncio.TimeoutError:
        return None
    except Exception:
        return None


async def _fetch_with_newspaper3k(url: str, timeout: int = 30) -> Optional[str]:
    """
    使用newspaper3k提取文章内容
    
    Args:
        url: 文章URL
        timeout: 超时时间（秒）
        
    Returns:
        提取的文章文本内容，失败返回None
    """
    try:
        from newspaper import Article
        
        # 创建Article对象
        article = Article(url)
        
        # 下载文章（使用asyncio.to_thread包装）
        await asyncio.wait_for(
            asyncio.to_thread(article.download),
            timeout=timeout
        )
        
        # 解析文章（使用asyncio.to_thread包装）
        await asyncio.wait_for(
            asyncio.to_thread(article.parse),
            timeout=timeout
        )
        
        # 获取文本内容
        if article.text and article.text.strip():
            return article.text.strip()
        
        return None
        
    except asyncio.TimeoutError:
        return None
    except Exception:
        return None


async def fetch_article_content(url: str, timeout: int = 30) -> Optional[str]:
    """
    按优先级提取文章内容：trafilatura → newspaper3k
    
    Args:
        url: 文章URL
        timeout: 超时时间（秒）
        
    Returns:
        提取的文章文本内容，失败返回None
    """
    if not url or not url.startswith(('http://', 'https://')):
        return None
    
    # 优先尝试trafilatura
    content = await _fetch_with_trafilatura(url, timeout)
    if content:
        return content
    
    # trafilatura失败，尝试newspaper3k
    content = await _fetch_with_newspaper3k(url, timeout)
    if content:
        return content
    
    # 两者都失败，返回None
    return None

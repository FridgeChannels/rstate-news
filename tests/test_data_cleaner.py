"""
数据清洗器测试
"""
import pytest
from datetime import datetime, timedelta
from utils.data_cleaner import DataCleaner


def test_clean_html():
    """测试HTML清理"""
    cleaner = DataCleaner()
    
    html = "<p>这是<strong>测试</strong>内容</p>"
    result = cleaner.clean_html(html)
    
    assert "测试" in result
    assert "<p>" not in result
    assert "<strong>" not in result


def test_normalize_date():
    """测试日期标准化"""
    cleaner = DataCleaner()
    
    # 测试相对时间
    result = cleaner.normalize_date("2 hours ago")
    assert result is not None
    
    # 测试标准日期
    result = cleaner.normalize_date("2024-01-15")
    assert result is not None
    assert "2024-01-15" in result


def test_extract_keywords():
    """测试关键词提取"""
    cleaner = DataCleaner()
    
    text = "房价上涨，市场成交活跃，利率下降"
    keywords = cleaner.extract_keywords(text)
    
    assert len(keywords) > 0
    assert any("房价" in k or "price" in k.lower() for k in keywords)


def test_filter_by_time_range():
    """测试时间范围过滤"""
    cleaner = DataCleaner(time_range_days=7)
    
    # 创建测试文章
    now = datetime.utcnow()
    articles = [
        {
            "title": "新文章",
            "publish_date": now.isoformat(),
            "url": "http://example.com/1"
        },
        {
            "title": "旧文章",
            "publish_date": (now - timedelta(days=10)).isoformat(),
            "url": "http://example.com/2"
        }
    ]
    
    filtered = cleaner.filter_by_time_range(articles)
    
    assert len(filtered) == 1
    assert filtered[0]["title"] == "新文章"

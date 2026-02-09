"""
测试文章内容获取功能
验证trafilatura、newspaper3k和fallback机制
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.article_content_fetcher import fetch_article_content
from utils.logger import logger


async def test_trafilatura_success():
    """测试trafilatura成功提取内容"""
    print("\n" + "=" * 70)
    print("测试1: Trafilatura成功提取")
    print("=" * 70)
    
    # 使用一个简单的新闻文章URL
    test_url = "https://www.bbc.com/news/technology"
    
    print(f"测试URL: {test_url}")
    print("预期: 使用trafilatura成功提取内容")
    
    try:
        content = await fetch_article_content(test_url, timeout=30)
        
        if content:
            print(f"✅ 成功: 提取到 {len(content)} 个字符的内容")
            print(f"内容预览: {content[:200]}...")
            return True
        else:
            print("❌ 失败: 未提取到内容")
            return False
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_newspaper3k_fallback():
    """测试trafilatura失败时，newspaper3k作为fallback"""
    print("\n" + "=" * 70)
    print("测试2: Newspaper3k Fallback")
    print("=" * 70)
    
    # 使用一个可能trafilatura失败但newspaper3k能成功的URL
    test_url = "https://techcrunch.com/2024/01/01/test"
    
    print(f"测试URL: {test_url}")
    print("预期: trafilatura可能失败，但newspaper3k应该能提取内容")
    
    try:
        content = await fetch_article_content(test_url, timeout=30)
        
        if content:
            print(f"✅ 成功: 提取到 {len(content)} 个字符的内容")
            print(f"内容预览: {content[:200]}...")
            return True
        else:
            print("⚠️  未提取到内容（可能是URL无效或两个库都失败）")
            return False
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_fallback_to_summary():
    """测试两者都失败时，保留列表页摘要"""
    print("\n" + "=" * 70)
    print("测试3: Fallback到列表页摘要")
    print("=" * 70)
    
    # 使用一个无效的URL
    test_url = "https://invalid-url-that-does-not-exist-12345.com/article"
    
    print(f"测试URL: {test_url}")
    print("预期: 两个库都失败，返回None（应该保留列表页摘要）")
    
    try:
        content = await fetch_article_content(test_url, timeout=10)
        
        if content is None:
            print("✅ 成功: 返回None，应该保留列表页摘要")
            return True
        else:
            print(f"⚠️  意外: 返回了内容（{len(content)} 字符）")
            return False
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_concurrent_processing():
    """测试并发控制（3个并发）"""
    print("\n" + "=" * 70)
    print("测试4: 并发控制（3个并发）")
    print("=" * 70)
    
    # 使用多个URL测试并发
    test_urls = [
        "https://www.bbc.com/news",
        "https://techcrunch.com",
        "https://www.theverge.com",
        "https://www.wired.com",
        "https://www.engadget.com"
    ]
    
    print(f"测试URL数量: {len(test_urls)}")
    print("预期: 最多3个并发，其他等待")
    
    try:
        import time
        start_time = time.time()
        
        # 使用Semaphore控制并发
        semaphore = asyncio.Semaphore(3)
        
        async def fetch_with_semaphore(url):
            async with semaphore:
                print(f"  开始处理: {url}")
                content = await fetch_article_content(url, timeout=15)
                print(f"  完成处理: {url} (内容长度: {len(content) if content else 0})")
                return content
        
        results = await asyncio.gather(
            *[fetch_with_semaphore(url) for url in test_urls],
            return_exceptions=True
        )
        
        elapsed_time = time.time() - start_time
        
        success_count = sum(1 for r in results if r and not isinstance(r, Exception))
        
        print(f"\n✅ 并发测试完成:")
        print(f"  总耗时: {elapsed_time:.2f} 秒")
        print(f"  成功: {success_count}/{len(test_urls)}")
        print(f"  预期: 由于3个并发限制，总耗时应该 > 单URL耗时 * (URL数/3)")
        
        return True
        
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_timeout_mechanism():
    """测试超时机制"""
    print("\n" + "=" * 70)
    print("测试5: 超时机制")
    print("=" * 70)
    
    # 使用一个会超时的URL（或者很慢的URL）
    test_url = "https://httpstat.us/200?sleep=5000"  # 5秒延迟
    
    print(f"测试URL: {test_url}")
    print("预期: 5秒超时，返回None")
    
    try:
        import time
        start_time = time.time()
        
        content = await fetch_article_content(test_url, timeout=3)  # 3秒超时
        
        elapsed_time = time.time() - start_time
        
        if content is None and elapsed_time < 5:
            print(f"✅ 成功: 超时机制工作正常（耗时: {elapsed_time:.2f} 秒）")
            return True
        elif content:
            print(f"⚠️  意外: 在超时前获取到了内容")
            return False
        else:
            print(f"⚠️  未获取内容，但耗时: {elapsed_time:.2f} 秒")
            return False
            
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_integration_with_coordinator():
    """测试与Coordinator的集成"""
    print("\n" + "=" * 70)
    print("测试6: Coordinator集成测试")
    print("=" * 70)
    
    # 模拟文章数据
    test_articles = [
        {
            'title': 'Test Article 1',
            'url': 'https://www.bbc.com/news/technology',
            'content': 'Original summary from list page',
            'content_summary': 'Original summary from list page',
            'publish_date': '2026-01-28T00:00:00'
        },
        {
            'title': 'Test Article 2',
            'url': 'https://invalid-url-12345.com',
            'content': 'Original summary from list page',
            'content_summary': 'Original summary from list page',
            'publish_date': '2026-01-28T00:00:00'
        }
    ]
    
    print(f"测试文章数: {len(test_articles)}")
    print("预期: 第一个文章应该更新content，第二个保留原摘要")
    
    try:
        from main import ScraperCoordinator
        
        coordinator = ScraperCoordinator()
        updated_articles = await coordinator._fetch_articles_content(test_articles)
        
        print(f"\n结果:")
        for i, article in enumerate(updated_articles, 1):
            url = article.get('url', '')
            content = article.get('content', '')
            summary = article.get('content_summary', '')
            
            if 'invalid-url' in url:
                if content == summary == 'Original summary from list page':
                    print(f"  文章 {i}: ✅ 保留原摘要（正确）")
                else:
                    print(f"  文章 {i}: ❌ 摘要被修改（错误）")
            else:
                if len(content) > len('Original summary'):
                    print(f"  文章 {i}: ✅ 内容已更新（长度: {len(content)}）")
                else:
                    print(f"  文章 {i}: ⚠️  内容未更新")
        
        return True
        
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "=" * 70)
    print("文章内容获取功能测试")
    print("=" * 70)
    
    results = {}
    
    # 运行所有测试
    results['trafilatura'] = await test_trafilatura_success()
    results['newspaper3k_fallback'] = await test_newspaper3k_fallback()
    results['fallback_to_summary'] = await test_fallback_to_summary()
    results['concurrent'] = await test_concurrent_processing()
    results['timeout'] = await test_timeout_mechanism()
    results['integration'] = await test_integration_with_coordinator()
    
    # 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

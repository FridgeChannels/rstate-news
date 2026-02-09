"""
代码结构验证脚本
验证所有scraper的代码结构是否正确，不依赖网络连接
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def validate_imports():
    """验证所有模块可以正确导入"""
    print("="*70)
    print("验证模块导入")
    print("="*70)
    
    modules = [
        ("scrapers.base_scraper", "BaseScraper"),
        ("scrapers.local_news_scraper", "LocalNewsScraper"),
        ("scrapers.newsbreak_scraper", "NewsbreakScraper"),
        ("scrapers.patch_scraper", "PatchScraper"),
        ("scrapers.real_estate_scraper", "RealEstateScraper"),
        ("scrapers.realtor_scraper", "RealtorScraper"),
        ("scrapers.redfin_scraper", "RedfinScraper"),
        ("scrapers.nar_scraper", "NARScraper"),
        ("scrapers.freddiemac_scraper", "FreddieMacScraper"),
        ("scrapers.robust_scraper_mixin", "RobustScraperMixin"),
        ("database.supabase_client", "DatabaseManager"),
        ("scheduler.scheduler_manager", "SchedulerManager"),
        ("utils.data_cleaner", "DataCleaner"),
        ("utils.json_exporter", "JSONExporter"),
    ]
    
    success_count = 0
    for module_path, class_name in modules:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"✅ {module_path}.{class_name}")
            success_count += 1
        except Exception as e:
            print(f"❌ {module_path}.{class_name}: {str(e)[:50]}")
    
    print(f"\n导入验证: {success_count}/{len(modules)} 成功")
    return success_count == len(modules)


def validate_scraper_structure():
    """验证scraper类结构"""
    print("\n" + "="*70)
    print("验证Scraper类结构")
    print("="*70)
    
    from scrapers.newsbreak_scraper import NewsbreakScraper
    from scrapers.robust_scraper_mixin import RobustScraperMixin
    
    scraper = NewsbreakScraper()
    
    # 检查是否有必要的方法
    required_methods = [
        'scrape',
        '_scrape_zipcode_news',
        '_extract_article_data',
        'find_elements_with_fallback',
        'extract_article_data_robust'
    ]
    
    success_count = 0
    for method in required_methods:
        if hasattr(scraper, method):
            print(f"✅ 方法存在: {method}")
            success_count += 1
        else:
            print(f"❌ 方法缺失: {method}")
    
    # 检查是否继承了RobustScraperMixin
    if isinstance(scraper, RobustScraperMixin):
        print("✅ 继承了 RobustScraperMixin")
        success_count += 1
    else:
        print("❌ 未继承 RobustScraperMixin")
    
    print(f"\n结构验证: {success_count}/{len(required_methods) + 1} 通过")
    return success_count == len(required_methods) + 1


def validate_database_client():
    """验证数据库客户端方法"""
    print("\n" + "="*70)
    print("验证数据库客户端")
    print("="*70)
    
    from database.supabase_client import DatabaseManager
    
    db = DatabaseManager()
    
    required_methods = [
        'get_active_sources',
        'insert_raw_news',
        'get_recent_raw_news',
        'log_task',
        'update_task_log'
    ]
    
    success_count = 0
    for method in required_methods:
        if hasattr(db, method):
            print(f"✅ 方法存在: {method}")
            success_count += 1
        else:
            print(f"❌ 方法缺失: {method}")
    
    # 检查是否删除了旧方法
    old_methods = ['insert_articles', 'archive_old_articles', 'get_recent_articles']
    removed_count = 0
    for method in old_methods:
        if not hasattr(db, method):
            print(f"✅ 旧方法已删除: {method}")
            removed_count += 1
        else:
            print(f"⚠️  旧方法仍存在: {method}")
    
    print(f"\n数据库验证: {success_count}/{len(required_methods)} 通过, {removed_count}/{len(old_methods)} 旧方法已删除")
    return success_count == len(required_methods) and removed_count == len(old_methods)


def main():
    """主函数"""
    print("\n" + "="*70)
    print("代码结构验证")
    print("="*70 + "\n")
    
    results = []
    results.append(("模块导入", validate_imports()))
    results.append(("Scraper结构", validate_scraper_structure()))
    results.append(("数据库客户端", validate_database_client()))
    
    print("\n" + "="*70)
    print("验证总结")
    print("="*70)
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("="*70)
    
    if all_passed:
        print("\n✅ 所有代码结构验证通过！")
        print("📝 下一步：在实际环境中测试scraper功能")
    else:
        print("\n❌ 部分验证失败，请检查代码")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

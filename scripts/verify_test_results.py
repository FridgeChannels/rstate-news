"""
测试结果验证脚本
用于验证DEBUG模式测试后的数据库数据
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.supabase_client import db_manager
from config.settings import settings


async def verify_database_data():
    """验证数据库中的数据"""
    print("=" * 70)
    print("数据库数据验证")
    print("=" * 70)
    
    results = {
        'total_records': 0,
        'by_source': {},
        'by_zipcode': {},
        'field_validation': {},
        'task_logs': []
    }
    
    try:
        # 1. 获取所有激活的信号源
        sources = await db_manager.get_active_sources()
        print(f"\n✅ 找到 {len(sources)} 个激活的信号源")
        source_map = {s['id']: s['source_name'] for s in sources}
        
        # 2. 查询play_raw_news表
        print("\n查询play_raw_news表...")
        response = await asyncio.to_thread(
            lambda: db_manager.client.table('play_raw_news')
            .select('*')
            .order('created_at', desc=True)
            .limit(1000)
            .execute()
        )
        
        all_news = response.data if response.data else []
        results['total_records'] = len(all_news)
        print(f"✅ 找到 {len(all_news)} 条记录")
        
        # 3. 按source_id分组统计
        print("\n按信号源分组统计:")
        for news in all_news:
            source_id = news.get('source_id')
            source_name = source_map.get(source_id, f"Unknown({source_id})")
            if source_name not in results['by_source']:
                results['by_source'][source_name] = 0
            results['by_source'][source_name] += 1
        
        for source_name, count in results['by_source'].items():
            print(f"  - {source_name}: {count} 条")
        
        # 4. 按zipcode分组统计
        print("\n按Zipcode分组统计:")
        for news in all_news:
            zipcode = news.get('zip_code') or 'NULL'
            if zipcode not in results['by_zipcode']:
                results['by_zipcode'][zipcode] = 0
            results['by_zipcode'][zipcode] += 1
        
        for zipcode, count in sorted(results['by_zipcode'].items()):
            print(f"  - {zipcode}: {count} 条")
        
        # 5. 字段验证
        print("\n字段完整性验证:")
        field_checks = {
            'source_id': 0,
            'title': 0,
            'url': 0,
            'city': 0,
            'status': 0,
            'language': 0,
            'crawl_time': 0,
            'created_at': 0
        }
        
        invalid_records = []
        for news in all_news:
            # 检查必需字段
            if news.get('source_id'):
                field_checks['source_id'] += 1
            if news.get('title') and len(news.get('title', '').strip()) > 0:
                field_checks['title'] += 1
            if news.get('url') and news.get('url', '').startswith(('http://', 'https://')):
                field_checks['url'] += 1
            if news.get('city'):
                field_checks['city'] += 1
            if news.get('status') == 'new':
                field_checks['status'] += 1
            if news.get('language') == 'en':
                field_checks['language'] += 1
            if news.get('crawl_time'):
                field_checks['crawl_time'] += 1
            if news.get('created_at'):
                field_checks['created_at'] += 1
            
            # 检查是否有无效记录
            if not news.get('title') or not news.get('url'):
                invalid_records.append(news.get('id'))
        
        for field, count in field_checks.items():
            percentage = (count / len(all_news) * 100) if all_news else 0
            status = "✅" if count == len(all_news) else "⚠️"
            print(f"  {status} {field}: {count}/{len(all_news)} ({percentage:.1f}%)")
        
        if invalid_records:
            print(f"\n⚠️  发现 {len(invalid_records)} 条无效记录 (ID: {invalid_records[:5]})")
        
        # 6. 查询任务日志
        print("\n查询task_logs表...")
        response = await asyncio.to_thread(
            lambda: db_manager.client.table('task_logs')
            .select('*')
            .order('started_at', desc=True)
            .limit(100)
            .execute()
        )
        
        task_logs = response.data if response.data else []
        results['task_logs'] = task_logs
        print(f"✅ 找到 {len(task_logs)} 条任务日志")
        
        # 统计任务状态
        status_count = {}
        for log in task_logs:
            status = log.get('status', 'unknown')
            status_count[status] = status_count.get(status, 0) + 1
        
        print("\n任务状态统计:")
        for status, count in status_count.items():
            print(f"  - {status}: {count} 个")
        
        # 显示最近的任务
        print("\n最近的任务执行记录:")
        for log in task_logs[:10]:
            task_type = log.get('task_type', 'unknown')
            status = log.get('status', 'unknown')
            source = log.get('source', 'N/A')
            zipcode = log.get('zipcode', 'N/A')
            count = log.get('articles_count', 0)
            print(f"  - {task_type} | {source} | {zipcode} | {status} | {count} 篇文章")
        
        return results
        
    except Exception as e:
        print(f"\n❌ 验证过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return results


async def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("DEBUG模式测试结果验证")
    print("=" * 70 + "\n")
    
    results = await verify_database_data()
    
    print("\n" + "=" * 70)
    print("验证总结")
    print("=" * 70)
    print(f"总记录数: {results['total_records']}")
    print(f"信号源数量: {len(results['by_source'])}")
    print(f"任务日志数: {len(results['task_logs'])}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

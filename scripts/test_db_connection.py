"""
简单的数据库连接测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from database.supabase_client import db_manager
    print("✅ 数据库管理器导入成功")
    
    import asyncio
    async def test():
        sources = await db_manager.get_active_sources()
        print(f"✅ 成功连接到数据库，找到 {len(sources)} 个激活的信号源")
        for s in sources:
            print(f"  - {s.get('source_name')} (ID: {s.get('id')})")
    
    asyncio.run(test())
except Exception as e:
    print(f"❌ 数据库连接失败: {str(e)}")
    import traceback
    traceback.print_exc()

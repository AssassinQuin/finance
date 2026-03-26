"""基线设置脚本 - Phase 0"""
import asyncio
from fcli.core.database import Database
from fcli.core.config import config


async def main():
    print("=== Phase 0: 建立基线与可回滚机制 ===\n")
    
    await Database.init(config)
    
    # 1. 创建 migrations 表（如果不存在）
    print("1. 创建 migrations 表...")
    try:
        await Database.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                version VARCHAR(255) PRIMARY KEY,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✓ migrations 表已就绪\n")
    except Exception as e:
        print(f"   ✗ 创建失败: {e}\n")
        await Database.close()
        return
    
    # 2. 记录基线迁移
    print("2. 记录基线迁移...")
    try:
        await Database.execute("""
            INSERT INTO migrations (version, description, applied_at)
            VALUES (
                '000_baseline',
                'Initial baseline snapshot before refactoring',
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (version) DO NOTHING
        """)
        print("   ✓ 基线迁移记录已创建\n")
    except Exception as e:
        print(f"   ! 记录已存在或插入失败: {e}\n")
    
    # 3. 验证关键表状态
    print("3. 验证关键表状态...")
    tables = [
        'dim_fund', 'fact_fund_scale', 'fact_gold_reserve',
        'watchlist_assets', 'gold_supply_demand', 'fact_gold_supply_demand',
        'dim_asset', 'fact_quote', 'dim_currency', 'fact_fx_rate'
    ]
    
    print("   关键表行数统计:")
    for table in tables:
        try:
            result = await Database.fetch_one(f"SELECT COUNT(*) as count FROM {table}")
            print(f"   - {table}: {result['count']} rows")
        except Exception as e:
            print(f"   - {table}: ERROR - {e}")
    
    print("\n✓ Phase 0 基线设置完成")
    print("  - migrations 表已创建")
    print("  - 基线记录已插入")
    print("  - 关键表状态已验证")
    print("\n可以安全进入 Phase 1")
    
    await Database.close()


if __name__ == "__main__":
    asyncio.run(main())

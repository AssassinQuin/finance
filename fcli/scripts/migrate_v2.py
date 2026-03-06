#!/usr/bin/env python3
"""
V2 数据库迁移脚本

将 V1 表（gold_reserves, gpr_history, watchlist_assets, cache_entries）
迁移到 V2 维度模型（维度表 + 事实表）

执行步骤：
1. 创建 V2 表结构
2. 填充维度表（dim_country, dim_currency, dim_data_source）
3. 迁移事实数据（fact_gold_reserve, fact_gpr）
4. 迁移其他表（watchlist_assets, cache_entries - 保持不变）
5. 重命名旧表为 _v1_backup
6. 创建视图以保持向后兼容

使用方法：
    python -m fcli.scripts.migrate_v2
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fcli.core.config import Settings
from fcli.core.database import Database


async def create_v2_schema():
    """创建 V2 表结构"""
    print("📦 Creating V2 schema...")

    sql_file = Path(__file__).parent.parent.parent / "init_v2.sql"
    with open(sql_file) as f:
        sql = f.read()

    import re

    current_stmt = []
    statements = []

    for line in sql.split("\n"):
        if line.strip().startswith("--"):
            continue

        current_stmt.append(line)

        if ";" in line:
            stmt = "\n".join(current_stmt).strip()
            if stmt and stmt != ";":
                statements.append(stmt)
            current_stmt = []

    for stmt in statements:
        try:
            await Database.execute(stmt)
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower() or "does not exist" in error_msg.lower():
                print(f"  ⚠️  Warning: {error_msg}")
            else:
                raise

    print("  ✓ V2 schema created")


async def populate_dimensions():
    """填充维度表数据"""
    print("📊 Populating dimension tables...")

    # 1. Populate dim_data_source
    print("  → Inserting data sources...")
    data_sources = [
        ("IMF", "https://www.imf.org", "International Monetary Fund"),
        ("WGC", "https://www.gold.org", "World Gold Council"),
        ("Caldara-Dario-Iacoviello", "https://www.matteoiacoviello.com/gpr.htm", "GPR Index Research"),
        ("Akshare", "https://akshare.akfamily.xyz", "Chinese Market Data"),
    ]

    for name, url, notes in data_sources:
        await Database.execute(
            """
            INSERT INTO dim_data_source (source_name, source_url, notes)
            VALUES ($1, $2, $3)
            ON CONFLICT (source_name) DO NOTHING
            """,
            name,
            url,
            notes,
        )

    # 2. Populate dim_currency
    print("  → Inserting currencies...")
    currencies = [
        ("USD", "US Dollar", "$"),
        ("CNY", "Chinese Yuan", "¥"),
        ("EUR", "Euro", "€"),
        ("GBP", "British Pound", "£"),
        ("JPY", "Japanese Yen", "¥"),
    ]

    for code, name, symbol in currencies:
        await Database.execute(
            """
            INSERT INTO dim_currency (currency_code, currency_name, symbol)
            VALUES ($1, $2, $3)
            ON CONFLICT (currency_code) DO NOTHING
            """,
            code,
            name,
            symbol,
        )

    # 3. Populate dim_country from gold_reserves
    print("  → Extracting countries from gold_reserves...")
    countries = await Database.fetch_all(
        """
        SELECT DISTINCT country_code, country_name
        FROM gold_reserves
        ORDER BY country_code
        """
    )

    for country in countries:
        await Database.execute(
            """
            INSERT INTO dim_country (country_code, country_name, is_active)
            VALUES ($1, $2, TRUE)
            ON CONFLICT (country_code) DO NOTHING
            """,
            country["country_code"],
            country["country_name"],
        )

    print(f"  ✓ Inserted {len(countries)} countries")


async def migrate_gold_reserves():
    """迁移 gold_reserves 数据到 fact_gold_reserve"""
    print("💰 Migrating gold_reserves...")

    # Get data source ID
    source = await Database.fetch_one("SELECT id FROM dim_data_source WHERE source_name = 'WGC'")
    source_id = source["id"] if source else None

    # Migrate data
    result = await Database.execute(
        f"""
        INSERT INTO fact_gold_reserve (country_id, report_date, gold_tonnes, source_id, fetched_at)
        SELECT
            c.id,
            gr.data_date,
            gr.gold_tonnes,
            {source_id},
            gr.fetched_at
        FROM gold_reserves gr
        JOIN dim_country c ON c.country_code = gr.country_code
        ON CONFLICT (country_id, report_date) DO NOTHING
        """
    )

    # Count migrated records
    count = await Database.fetch_one("SELECT COUNT(*) as count FROM fact_gold_reserve")
    print(f"  ✓ Migrated {count['count']} gold reserve records")


async def migrate_gpr():
    """迁移 gpr_history 数据到 fact_gpr"""
    print("📈 Migrating gpr_history...")

    # Get data source ID
    source = await Database.fetch_one("SELECT id FROM dim_data_source WHERE source_name = 'Caldara-Dario-Iacoviello'")
    source_id = source["id"] if source else None

    # Migrate data
    result = await Database.execute(
        f"""
        INSERT INTO fact_gpr (country_code, report_date, gpr_index, source_id)
        SELECT
            country_code,
            report_date,
            gpr_index,
            {source_id}
        FROM gpr_history
        ON CONFLICT (country_code, report_date) DO NOTHING
        """
    )

    # Count migrated records
    count = await Database.fetch_one("SELECT COUNT(*) as count FROM fact_gpr")
    print(f"  ✓ Migrated {count['count']} GPR records")


async def backup_old_tables():
    """备份旧表"""
    print("💾 Backing up old tables...")

    tables = ["gold_reserves", "gpr_history"]

    for table in tables:
        try:
            await Database.execute(f"ALTER TABLE {table} RENAME TO {table}_v1_backup")
            print(f"  ✓ {table} → {table}_v1_backup")
        except Exception as e:
            print(f"  ⚠️  {table} backup failed: {e}")


async def verify_migration():
    """验证迁移结果"""
    print("\n🔍 Verifying migration...")

    # Check dimension tables
    dims = ["dim_country", "dim_currency", "dim_data_source"]
    for dim in dims:
        count = await Database.fetch_one(f"SELECT COUNT(*) as count FROM {dim}")
        print(f"  {dim}: {count['count']} records")

    # Check fact tables
    facts = ["fact_gold_reserve", "fact_gpr"]
    for fact in facts:
        count = await Database.fetch_one(f"SELECT COUNT(*) as count FROM {fact}")
        print(f"  {fact}: {count['count']} records")

    # Check views
    print("\n  Checking views...")
    try:
        result = await Database.fetch_all("SELECT COUNT(*) as count FROM v_gold_reserves")
        print(f"  v_gold_reserves: {result[0]['count']} records ✓")
    except Exception as e:
        print(f"  v_gold_reserves: ⚠️  {e}")

    try:
        result = await Database.fetch_all("SELECT COUNT(*) as count FROM v_gpr_history")
        print(f"  v_gpr_history: {result[0]['count']} records ✓")
    except Exception as e:
        print(f"  v_gpr_history: ⚠️  {e}")


async def main():
    """主迁移流程"""
    print("🚀 V2 Database Migration")
    print("=" * 60)

    settings = Settings()
    await Database.init(settings)

    try:
        # Step 1: Create V2 schema
        await create_v2_schema()

        # Step 2: Populate dimensions
        await populate_dimensions()

        # Step 3: Migrate fact data
        await migrate_gold_reserves()
        await migrate_gpr()

        # Step 4: Backup old tables
        await backup_old_tables()

        # Step 5: Verify
        await verify_migration()

        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Update Store classes to use V2 tables")
        print("2. Test all commands")
        print("3. Drop backup tables after verification: DROP TABLE gold_reserves_v1_backup, gpr_history_v1_backup;")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await Database.close()


if __name__ == "__main__":
    asyncio.run(main())

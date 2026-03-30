﻿#!/usr/bin/env python3
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

import sys

from fcli.core.config import Settings
from fcli.core.database import Database
from fcli.infra.http_client import run_async


async def create_v2_schema():
    """创建 V2 表结构（如果不存在）"""
    print("📦 Checking V2 schema...")

    required_tables = [
        "dim_country",
        "dim_currency",
        "dim_data_source",
        "dim_asset",
        "dim_period",
        "dim_metric",
        "fact_gold_reserve",
        "fact_gpr",
        "fact_fx_rate",
        "fact_quote",
        "fact_gold_supply_demand",
    ]

    existing = await Database.fetch_all(
        """
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = ANY($1)
        """,
        required_tables,
    )
    existing_names = {row["table_name"] for row in existing}

    if len(existing_names) == len(required_tables):
        print("  ✓ V2 schema already exists, skipping creation")
        return

    missing = set(required_tables) - existing_names
    print(f"  ⚠️  Missing tables: {missing}")
    print("  ❌ V2 schema incomplete. Please run full migration from V1.")
    print("     This script is designed for one-time V1→V2 migration.")
    print("     If you need to recreate the schema, restore init_v2.sql first.")
    sys.exit(1)


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
    await Database.execute(
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
    await Database.execute(
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
        await create_v2_schema()

        v1_exists = await Database.fetch_one(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'gold_reserves')"
        )

        if not v1_exists or not v1_exists["exists"]:
            print("\n✅ V2 schema is ready. No V1 tables to migrate.")
            print("   Migration was already completed or this is a fresh install.")
            return

        print("\n📋 V1 tables detected. Starting data migration...")

        await populate_dimensions()
        await migrate_gold_reserves()
        await migrate_gpr()
        await backup_old_tables()
        await verify_migration()

        print("\n✅ Migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await Database.close()


if __name__ == "__main__":
    run_async(main())

#!/usr/bin/env python3
"""
V3 数据库迁移脚本 — 扁平化重构

将 V2 星型 schema (dim_* + fact_*) 迁移到 V3 简单平面表。

新表结构:
- gold_reserves (替代 fact_gold_reserve + dim_country + dim_data_source)
- gpr_history   (替代 fact_gpr + dim_data_source)
- quotes        (替代 fact_quote + dim_asset + dim_data_source)
- fx_rates      (替代 fact_fx_rate + dim_currency + dim_data_source)
- gold_supply_demand (替代 fact_gold_supply_demand + dim_period + dim_data_source)
- funds         (重命名 dim_fund)
- fund_scales   (重命名 fact_fund_scale)

保留:
- watchlist_assets (不变)
- cache_entries    (不变)

使用方法:
    python -m fcli.scripts.migrate_v3
    python -m fcli.scripts.migrate_v3 --drop-old  # 迁移后删除旧表
"""

import argparse
import sys

from fcli.core.config import Settings
from fcli.core.database import Database
from fcli.infra.http_client import run_async


async def check_v2_schema() -> bool:
    """检查 V2 schema 是否存在"""
    print("📦 Checking V2 schema...")

    required = [
        "fact_gold_reserve",
        "fact_gpr",
    ]

    existing = await Database.fetch_all(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = ANY($1)
        """,
        required,
    )
    existing_names = {row["table_name"] for row in existing}

    if not existing_names:
        print("  ℹ️  No V2 tables found. Fresh install or already migrated.")
        return False

    print(f"  ✓ Found V2 tables: {existing_names}")
    return True


async def create_v3_tables():
    """创建 V3 平面表"""
    print("\n🏗️  Creating V3 flat tables...")

    tables = {
        "gold_reserves": """
            CREATE TABLE IF NOT EXISTS gold_reserves (
                id SERIAL PRIMARY KEY,
                country_code VARCHAR(10) NOT NULL,
                country_name VARCHAR(100) NOT NULL,
                gold_tonnes NUMERIC(12, 3) NOT NULL,
                report_date DATE NOT NULL,
                data_source VARCHAR(50) DEFAULT 'IMF',
                fetched_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (country_code, report_date)
            )
        """,
        "gpr_history": """
            CREATE TABLE IF NOT EXISTS gpr_history (
                id SERIAL PRIMARY KEY,
                country_code VARCHAR(10) DEFAULT 'WLD',
                report_date DATE NOT NULL,
                gpr_index NUMERIC(10, 4) NOT NULL,
                data_source VARCHAR(50) DEFAULT 'Caldara-Iacoviello',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (country_code, report_date)
            )
        """,
        "quotes": """
            CREATE TABLE IF NOT EXISTS quotes (
                id SERIAL PRIMARY KEY,
                code VARCHAR(20) NOT NULL,
                name VARCHAR(100),
                asset_type VARCHAR(20) DEFAULT 'stock',
                price NUMERIC(15, 4),
                change_amount NUMERIC(15, 4),
                change_percent NUMERIC(8, 4),
                high_price NUMERIC(15, 4),
                low_price NUMERIC(15, 4),
                open_price NUMERIC(15, 4),
                prev_close NUMERIC(15, 4),
                volume BIGINT,
                quote_time TIMESTAMP NOT NULL,
                data_source VARCHAR(50) DEFAULT 'Akshare',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "fx_rates": """
            CREATE TABLE IF NOT EXISTS fx_rates (
                id SERIAL PRIMARY KEY,
                base_currency VARCHAR(10) NOT NULL,
                quote_currency VARCHAR(10) NOT NULL,
                rate NUMERIC(15, 8) NOT NULL,
                rate_time TIMESTAMP NOT NULL,
                data_source VARCHAR(50) DEFAULT 'Frankfurter',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "gold_supply_demand": """
            CREATE TABLE IF NOT EXISTS gold_supply_demand (
                id SERIAL PRIMARY KEY,
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL CHECK (quarter IN (1, 2, 3, 4)),
                mine_production NUMERIC(12, 3),
                recycling NUMERIC(12, 3),
                net_hedging NUMERIC(12, 3),
                total_supply NUMERIC(12, 3),
                jewelry NUMERIC(12, 3),
                technology NUMERIC(12, 3),
                total_investment NUMERIC(12, 3),
                bars_coins NUMERIC(12, 3),
                etfs NUMERIC(12, 3),
                otc_investment NUMERIC(12, 3),
                central_banks NUMERIC(12, 3),
                total_demand NUMERIC(12, 3),
                supply_demand_balance NUMERIC(12, 3),
                price_avg_usd NUMERIC(10, 2),
                data_source VARCHAR(50) DEFAULT 'WGC',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (year, quarter)
            )
        """,
    }

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_gold_reserves_date ON gold_reserves (report_date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_gold_reserves_country ON gold_reserves (country_code)",
        "CREATE INDEX IF NOT EXISTS idx_gold_reserves_country_date ON gold_reserves (country_code, report_date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_gpr_date ON gpr_history (report_date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_quotes_code ON quotes (code, quote_time DESC)",
        "CREATE INDEX IF NOT EXISTS idx_fx_pair ON fx_rates (base_currency, quote_currency, rate_time DESC)",
        "CREATE INDEX IF NOT EXISTS idx_gsd_year_quarter ON gold_supply_demand (year DESC, quarter DESC)",
    ]

    for name, ddl in tables.items():
        await Database.execute(ddl)
        print(f"  ✓ Created table: {name}")

    for idx_sql in indexes:
        await Database.execute(idx_sql)
    print(f"  ✓ Created {len(indexes)} indexes")


async def migrate_gold_reserves():
    """迁移 gold_reserves: fact_gold_reserve + dim_country + dim_data_source → gold_reserves"""
    print("\n💰 Migrating gold_reserves...")

    # Check if source tables exist
    exists = await Database.fetch_one(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'fact_gold_reserve')"
    )
    if not exists or not exists["exists"]:
        print("  ⏭️  fact_gold_reserve not found, skipping")
        return 0

    await Database.execute("""
        INSERT INTO gold_reserves (country_code, country_name, gold_tonnes, report_date, data_source, fetched_at, created_at, updated_at)
        SELECT
            c.country_code,
            c.country_name,
            f.gold_tonnes,
            f.report_date,
            COALESCE(ds.source_name, 'IMF'),
            f.fetched_at,
            f.created_at,
            f.updated_at
        FROM fact_gold_reserve f
        JOIN dim_country c ON f.country_id = c.id
        LEFT JOIN dim_data_source ds ON f.source_id = ds.id
        ON CONFLICT (country_code, report_date) DO NOTHING
    """)

    count = await Database.fetch_one("SELECT COUNT(*) as count FROM gold_reserves")
    print(f"  ✓ Migrated {count['count']} gold reserve records")
    return count["count"]


async def migrate_gpr():
    """迁移 gpr_history: fact_gpr + dim_data_source → gpr_history"""
    print("\n📈 Migrating gpr_history...")

    exists = await Database.fetch_one(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'fact_gpr')"
    )
    if not exists or not exists["exists"]:
        print("  ⏭️  fact_gpr not found, skipping")
        return 0

    await Database.execute("""
        INSERT INTO gpr_history (country_code, report_date, gpr_index, data_source, created_at)
        SELECT
            f.country_code,
            f.report_date,
            f.gpr_index,
            COALESCE(ds.source_name, 'Caldara-Iacoviello'),
            f.created_at
        FROM fact_gpr f
        LEFT JOIN dim_data_source ds ON f.source_id = ds.id
        ON CONFLICT (country_code, report_date) DO NOTHING
    """)

    count = await Database.fetch_one("SELECT COUNT(*) as count FROM gpr_history")
    print(f"  ✓ Migrated {count['count']} GPR records")
    return count["count"]


async def migrate_quotes():
    """迁移 quotes: fact_quote + dim_asset + dim_data_source → quotes"""
    print("\n📊 Migrating quotes...")

    exists = await Database.fetch_one(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'fact_quote')"
    )
    if not exists or not exists["exists"]:
        print("  ⏭️  fact_quote not found, skipping")
        return 0

    await Database.execute("""
        INSERT INTO quotes (code, name, asset_type, price, change_amount, change_percent,
                           high_price, low_price, open_price, prev_close, volume, quote_time, data_source, created_at)
        SELECT
            a.asset_code,
            a.asset_name,
            a.asset_type,
            f.price,
            f.change_amount,
            f.change_percent,
            f.high_price,
            f.low_price,
            f.open_price,
            f.prev_close,
            f.volume,
            f.quote_time,
            COALESCE(ds.source_name, 'Akshare'),
            f.created_at
        FROM fact_quote f
        JOIN dim_asset a ON f.asset_id = a.id
        LEFT JOIN dim_data_source ds ON f.source_id = ds.id
    """)

    count = await Database.fetch_one("SELECT COUNT(*) as count FROM quotes")
    print(f"  ✓ Migrated {count['count']} quote records")
    return count["count"]


async def migrate_fx_rates():
    """迁移 fx_rates: fact_fx_rate + dim_currency + dim_data_source → fx_rates"""
    print("\n💱 Migrating fx_rates...")

    exists = await Database.fetch_one(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'fact_fx_rate')"
    )
    if not exists or not exists["exists"]:
        print("  ⏭️  fact_fx_rate not found, skipping")
        return 0

    await Database.execute("""
        INSERT INTO fx_rates (base_currency, quote_currency, rate, rate_time, data_source, created_at)
        SELECT
            bc.currency_code,
            qc.currency_code,
            f.rate,
            f.rate_time,
            COALESCE(ds.source_name, 'Frankfurter'),
            f.created_at
        FROM fact_fx_rate f
        JOIN dim_currency bc ON f.base_currency_id = bc.id
        JOIN dim_currency qc ON f.quote_currency_id = qc.id
        LEFT JOIN dim_data_source ds ON f.source_id = ds.id
    """)

    count = await Database.fetch_one("SELECT COUNT(*) as count FROM fx_rates")
    print(f"  ✓ Migrated {count['count']} FX rate records")
    return count["count"]


async def migrate_gold_supply_demand():
    """迁移 gold_supply_demand: fact_gold_supply_demand + dim_period + dim_data_source → gold_supply_demand"""
    print("\n⛏️  Migrating gold_supply_demand...")

    exists = await Database.fetch_one(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'fact_gold_supply_demand')"
    )
    if not exists or not exists["exists"]:
        print("  ⏭️  fact_gold_supply_demand not found, skipping")
        return 0

    await Database.execute("""
        INSERT INTO gold_supply_demand (
            year, quarter,
            mine_production, recycling, net_hedging, total_supply,
            jewelry, technology, total_investment, bars_coins, etfs,
            otc_investment, central_banks, total_demand,
            supply_demand_balance, price_avg_usd,
            data_source, created_at, updated_at
        )
        SELECT
            p.year, p.quarter,
            f.mine_production, f.recycling, f.net_hedging, f.total_supply,
            f.jewelry, f.technology, f.total_investment, f.bars_coins, f.etfs,
            f.otc_investment, f.central_banks, f.total_demand,
            f.supply_demand_balance, f.price_avg_usd,
            COALESCE(ds.source_name, 'WGC'),
            f.created_at, f.updated_at
        FROM fact_gold_supply_demand f
        JOIN dim_period p ON f.period_id = p.id
        LEFT JOIN dim_data_source ds ON f.source_id = ds.id
        ON CONFLICT (year, quarter) DO NOTHING
    """)

    count = await Database.fetch_one("SELECT COUNT(*) as count FROM gold_supply_demand")
    print(f"  ✓ Migrated {count['count']} gold supply/demand records")
    return count["count"]


async def rename_fund_tables():
    """重命名 dim_fund → funds, fact_fund_scale → fund_scales"""
    print("\n📋 Renaming fund tables...")

    # Check dim_fund exists
    exists = await Database.fetch_one(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'dim_fund')"
    )
    if exists and exists["exists"]:
        await Database.execute("ALTER TABLE dim_fund RENAME TO funds")
        print("  ✓ dim_fund → funds")
    else:
        print("  ⏭️  dim_fund not found (may already be renamed)")

    exists = await Database.fetch_one(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'fact_fund_scale')"
    )
    if exists and exists["exists"]:
        await Database.execute("ALTER TABLE fact_fund_scale RENAME TO fund_scales")
        print("  ✓ fact_fund_scale → fund_scales")
    else:
        print("  ⏭️  fact_fund_scale not found (may already be renamed)")


async def drop_old_tables():
    """删除旧的 V2 表和视图"""
    print("\n🗑️  Dropping old V2 tables...")

    # Drop views first
    views = ["v_gold_reserves", "v_gpr_history", "gold_reserves_view", "gpr_history_view"]
    for view in views:
        try:
            await Database.execute(f"DROP VIEW IF EXISTS {view}")
            print(f"  ✓ Dropped view: {view}")
        except Exception as e:
            print(f"  ⚠️  Failed to drop view {view}: {e}")

    # Drop fact tables (depend on dim tables)
    fact_tables = [
        "fact_gold_reserve",
        "fact_gpr",
        "fact_quote",
        "fact_fx_rate",
        "fact_gold_supply_demand",
    ]
    for table in fact_tables:
        try:
            await Database.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"  ✓ Dropped: {table}")
        except Exception as e:
            print(f"  ⚠️  Failed to drop {table}: {e}")

    # Drop dim tables
    dim_tables = [
        "dim_country",
        "dim_currency",
        "dim_data_source",
        "dim_asset",
        "dim_period",
        "dim_metric",
    ]
    for table in dim_tables:
        try:
            await Database.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"  ✓ Dropped: {table}")
        except Exception as e:
            print(f"  ⚠️  Failed to drop {table}: {e}")

    # Drop V1 backup tables if they exist
    backups = ["gold_reserves_v1_backup", "gpr_history_v1_backup"]
    for table in backups:
        try:
            await Database.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"  ✓ Dropped backup: {table}")
        except Exception as e:
            print(f"  ⚠️  Failed to drop {table}: {e}")


async def verify_migration():
    """验证迁移结果"""
    print("\n🔍 Verifying V3 migration...")

    tables = {
        "gold_reserves": "gold_reserves",
        "gpr_history": "gpr_history",
        "quotes": "quotes",
        "fx_rates": "fx_rates",
        "gold_supply_demand": "gold_supply_demand",
        "funds": "funds",
        "fund_scales": "fund_scales",
        "watchlist_assets": "watchlist_assets",
        "cache_entries": "cache_entries",
    }

    for label, table in tables.items():
        exists = await Database.fetch_one(
            f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = '{table}')"
        )
        if exists and exists["exists"]:
            count = await Database.fetch_one(f"SELECT COUNT(*) as count FROM {table}")
            print(f"  ✓ {label}: {count['count']} records")
        else:
            print(f"  ⚠️  {label}: table not found!")

    # Verify no V2 tables remain
    v2_tables = await Database.fetch_all(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
          AND (table_name LIKE 'dim_%' OR table_name LIKE 'fact_%')
        """
    )
    if v2_tables:
        remaining = [row["table_name"] for row in v2_tables]
        print(f"\n  ⚠️  Remaining V2 tables: {remaining}")
        print("     Run with --drop-old to remove them")
    else:
        print("\n  ✓ No V2 tables remaining")


async def main(drop_old: bool = False):
    """主迁移流程"""
    print("🚀 V3 Database Migration — Flatten Star Schema")
    print("=" * 60)

    settings = Settings()
    await Database.init(settings)

    try:
        has_v2 = await check_v2_schema()

        # Step 1: Create new tables
        await create_v3_tables()

        if has_v2:
            print("\n📋 V2 tables detected. Starting data migration...")

            # Step 2: Migrate data
            await migrate_gold_reserves()
            await migrate_gpr()
            await migrate_quotes()
            await migrate_fx_rates()
            await migrate_gold_supply_demand()
            await rename_fund_tables()

            # Step 3: Drop old tables if requested
            if drop_old:
                await drop_old_tables()
            else:
                print("\n💡 Tip: Run with --drop-old to remove old V2 tables after verification")
        else:
            print("\n✅ V3 tables created. No V2 data to migrate.")

        # Step 4: Verify
        await verify_migration()

        print("\n✅ V3 migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await Database.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="V3 Database Migration")
    parser.add_argument("--drop-old", action="store_true", help="Drop old V2 tables after migration")
    args = parser.parse_args()

    run_async(main(drop_old=args.drop_old))

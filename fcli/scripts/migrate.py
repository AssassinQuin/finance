"""PostgreSQL database migration script.

Replaces MySQL with PostgreSQL - "Just Use Postgres" approach.
Uses UNLOGGED table for cache to avoid WAL overhead.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fcli.core.config import config
from fcli.core.database import Database

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# PostgreSQL DDL - tables and indexes
MIGRATIONS = [
    # Migration tracking table
    """
    CREATE TABLE IF NOT EXISTS migrations (
        id SERIAL PRIMARY KEY,
        version VARCHAR(50) UNIQUE NOT NULL,
        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        description TEXT
    )
    """,
    # Migration 1: Initial schema
    """
    CREATE TABLE IF NOT EXISTS gold_reserves (
        id SERIAL PRIMARY KEY,
        country_code VARCHAR(10) NOT NULL,
        country_name VARCHAR(100) NOT NULL,
        gold_tonnes DECIMAL(15, 3),
        change_1m DECIMAL(15, 3),
        change_3m DECIMAL(15, 3),
        change_6m DECIMAL(15, 3),
        change_12m DECIMAL(15, 3),
        fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        data_date DATE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(country_code, data_date)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_gold_country_date 
    ON gold_reserves(country_code, data_date DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_gold_data_date 
    ON gold_reserves(data_date DESC)
    """,
    # Central bank schedules
    """
    CREATE TABLE IF NOT EXISTS central_bank_schedules (
        id SERIAL PRIMARY KEY,
        country_code VARCHAR(10) UNIQUE NOT NULL,
        country_name VARCHAR(100) NOT NULL,
        release_frequency VARCHAR(20),
        release_day_of_month INTEGER,
        release_time TIME,
        timezone VARCHAR(50),
        data_source VARCHAR(100),
        source_url TEXT,
        notes TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # Fetch logs
    """
    CREATE TABLE IF NOT EXISTS fetch_logs (
        id SERIAL PRIMARY KEY,
        task_name VARCHAR(100) NOT NULL,
        status VARCHAR(20) NOT NULL,
        started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP WITH TIME ZONE,
        records_count INTEGER DEFAULT 0,
        error_message TEXT,
        details JSONB
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_fetch_logs_task_time 
    ON fetch_logs(task_name, started_at DESC)
    """,
    # Quotes table
    """
    CREATE TABLE IF NOT EXISTS quotes (
        id SERIAL PRIMARY KEY,
        code VARCHAR(20) NOT NULL,
        name VARCHAR(100),
        price DECIMAL(18, 4),
        change DECIMAL(18, 4),
        change_percent DECIMAL(8, 4),
        volume BIGINT,
        open DECIMAL(18, 4),
        high DECIMAL(18, 4),
        low DECIMAL(18, 4),
        prev_close DECIMAL(18, 4),
        market VARCHAR(10),
        quote_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(code, DATE(quote_time))
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_quotes_code_time 
    ON quotes(code, quote_time DESC)
    """,
    # Exchange rates
    """
    CREATE TABLE IF NOT EXISTS exchange_rates (
        id SERIAL PRIMARY KEY,
        base_currency VARCHAR(3) NOT NULL,
        quote_currency VARCHAR(3) NOT NULL,
        rate DECIMAL(18, 8) NOT NULL,
        fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(base_currency, quote_currency, DATE(fetched_at))
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_rates_base_quote_date 
    ON exchange_rates(base_currency, quote_currency, fetched_at DESC)
    """,
    # Watchlist assets
    """
    CREATE TABLE IF NOT EXISTS watchlist_assets (
        id SERIAL PRIMARY KEY,
        code VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(100) NOT NULL,
        market VARCHAR(10) NOT NULL,
        asset_type VARCHAR(20) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_watchlist_active 
    ON watchlist_assets(is_active) WHERE is_active = TRUE
    """,
    # GPR History
    """
    CREATE TABLE IF NOT EXISTS gpr_history (
        id SERIAL PRIMARY KEY,
        gpr_value DECIMAL(10, 4) NOT NULL,
        gpr_type VARCHAR(20) DEFAULT 'monthly',
        data_date DATE NOT NULL UNIQUE,
        fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_gpr_date 
    ON gpr_history(data_date DESC)
    """,
    # Gold supply demand
    """
    CREATE TABLE IF NOT EXISTS gold_supply_demand (
        id SERIAL PRIMARY KEY,
        year INTEGER NOT NULL,
        quarter INTEGER,
        supply_total DECIMAL(15, 3),
        demand_total DECIMAL(15, 3),
        data_source VARCHAR(50),
        fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(year, quarter)
    )
    """,
    # SPDR Gold Trust holdings
    """
    CREATE TABLE IF NOT EXISTS spdr_holdings (
        id SERIAL PRIMARY KEY,
        data_date DATE NOT NULL UNIQUE,
        holdings DECIMAL(12, 3) NOT NULL,
        change DECIMAL(12, 3) NOT NULL DEFAULT 0,
        value DECIMAL(20, 2) NOT NULL,
        fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_spdr_date
    ON spdr_holdings(data_date DESC)
    """,
    # UNLOGGED cache table - no WAL, faster for ephemeral data
    """
    CREATE UNLOGGED TABLE IF NOT EXISTS cache_entries (
        key VARCHAR(512) PRIMARY KEY,
        value JSONB NOT NULL,
        expires_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_cache_expires 
    ON cache_entries(expires_at) 
    WHERE expires_at IS NOT NULL
    """,
]


# Seed data for central banks
SEED_DATA = [
    # Central bank schedules
    (
        "US",
        "United States",
        "monthly",
        20,
        "15:00",
        "America/New_York",
        "FRED/Treasury",
        "https://fred.stlouisfed.org/",
        "Treasury International Capital data",
    ),
    (
        "DE",
        "Germany",
        "monthly",
        7,
        "14:00",
        "Europe/Berlin",
        "Bundesbank",
        "https://www.bundesbank.de/",
        "Monthly reserve assets",
    ),
    (
        "IT",
        "Italy",
        "monthly",
        7,
        "14:00",
        "Europe/Rome",
        "Banca d'Italia",
        "https://www.bancaditalia.it/",
        "Official reserve assets",
    ),
    (
        "FR",
        "France",
        "monthly",
        7,
        "14:00",
        "Europe/Paris",
        "Banque de France",
        "https://www.banque-france.fr/",
        "Reserve assets",
    ),
    (
        "CN",
        "China",
        "monthly",
        7,
        "15:00",
        "Asia/Shanghai",
        "SAFE",
        "http://www.safe.gov.cn/",
        "Official reserve assets",
    ),
    ("RU", "Russia", "monthly", 7, "12:00", "Europe/Moscow", "CBR", "https://www.cbr.ru/", "International reserves"),
    ("JP", "Japan", "monthly", 7, "09:00", "Asia/Tokyo", "BOJ", "https://www.boj.or.jp/", "Foreign reserves"),
    (
        "IN",
        "India",
        "monthly",
        7,
        "17:30",
        "Asia/Kolkata",
        "RBI",
        "https://www.rbi.org.in/",
        "Foreign exchange reserves",
    ),
    (
        "TR",
        "Turkey",
        "weekly",
        None,
        "14:30",
        "Europe/Istanbul",
        "CBRT",
        "https://www.tcmb.gov.tr/",
        "Weekly international reserves",
    ),
    (
        "CH",
        "Switzerland",
        "monthly",
        7,
        "08:00",
        "Europe/Zurich",
        "SNB",
        "https://www.snb.ch/",
        "Foreign currency reserves",
    ),
]


async def init_database() -> bool:
    """Initialize database connection."""
    try:
        await Database.init(config)
        return Database.is_enabled()
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False


async def run_migrations() -> bool:
    """Run all migrations."""
    if not Database.is_enabled():
        logger.error("Database not initialized")
        return False

    try:
        # Run DDL migrations
        for i, migration in enumerate(MIGRATIONS):
            try:
                await Database.execute(migration)
                logger.info(f"Applied migration {i + 1}")
            except Exception as e:
                # Ignore "already exists" errors
                if "already exists" not in str(e).lower():
                    logger.warning(f"Migration {i + 1} warning: {e}")
                else:
                    logger.info(f"Migration {i + 1} already applied")

        # Insert seed data
        for bank_data in SEED_DATA:
            try:
                await Database.execute(
                    """
                    INSERT INTO central_bank_schedules 
                    (country_code, country_name, release_frequency, release_day_of_month,
                     release_time, timezone, data_source, source_url, notes)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (country_code) DO NOTHING
                    """,
                    *bank_data,
                )
            except Exception as e:
                logger.warning(f"Failed to insert {bank_data[0]}: {e}")

        logger.info("All migrations completed successfully")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


async def reset_database() -> bool:
    """Reset all tables (DANGER: deletes all data)."""
    if not Database.is_enabled():
        logger.error("Database not initialized")
        return False

    try:
        # Drop all tables
        tables = [
            "cache_entries",
            "spdr_holdings",
            "gold_supply_demand",
            "gpr_history",
            "watchlist_assets",
            "exchange_rates",
            "quotes",
            "fetch_logs",
            "central_bank_schedules",
            "gold_reserves",
            "migrations",
        ]

        for table in tables:
            try:
                await Database.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                logger.info(f"Dropped table: {table}")
            except Exception as e:
                logger.warning(f"Failed to drop {table}: {e}")

        logger.info("Database reset completed")
        return True

    except Exception as e:
        logger.error(f"Reset failed: {e}")
        return False


async def show_status() -> None:
    """Show migration status."""
    if not Database.is_enabled():
        logger.error("Database not connected")
        return

    try:
        # Check if migrations table exists
        row = await Database.fetch_one(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'migrations'
            )
            """
        )

        if not row or not row[0]:
            logger.info("No migrations table found - database not initialized")
            return

        # Get applied migrations
        rows = await Database.fetch_all("SELECT version, applied_at, description FROM migrations ORDER BY applied_at")

        logger.info(f"Applied migrations: {len(rows)}")
        for row in rows:
            logger.info(f"  - {row['version']}: {row['applied_at']}")

        # Get table counts
        tables = [
            "gold_reserves",
            "central_bank_schedules",
            "fetch_logs",
            "quotes",
            "exchange_rates",
            "watchlist_assets",
            "gpr_history",
            "gold_supply_demand",
            "spdr_holdings",
        ]

        logger.info("Table row counts:")
        for table in tables:
            try:
                row = await Database.fetch_one(f"SELECT COUNT(*) as cnt FROM {table}")
                count = row["cnt"] if row else 0
                logger.info(f"  - {table}: {count} rows")
            except Exception:
                logger.info(f"  - {table}: not found")

        # Cache stats
        try:
            row = await Database.fetch_one("SELECT COUNT(*) as cnt FROM cache_entries")
            cache_count = row["cnt"] if row else 0
            row2 = await Database.fetch_one(
                """SELECT COUNT(*) as cnt FROM cache_entries 
                   WHERE expires_at < CURRENT_TIMESTAMP"""
            )
            expired = row2["cnt"] if row2 else 0
            logger.info(f"Cache entries: {cache_count} (expired: {expired})")
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Failed to get status: {e}")


async def cleanup_cache() -> int:
    """Clean up expired cache entries."""
    if not Database.is_enabled():
        logger.error("Database not initialized")
        return 0

    try:
        result = await Database.execute("DELETE FROM cache_entries WHERE expires_at < CURRENT_TIMESTAMP")
        # asyncpg execute returns a string like "DELETE 42"
        if isinstance(result, str):
            parts = result.split()
            count = int(parts[1]) if len(parts) > 1 else 0
        else:
            count = 0
        logger.info(f"Cleaned up {count} expired cache entries")
        return count
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        return 0


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="PostgreSQL database migration tool")
    parser.add_argument("command", choices=["migrate", "reset", "status", "cleanup"])
    args = parser.parse_args()

    async def run() -> int:
        if not await init_database():
            return 1

        try:
            if args.command == "migrate":
                return 0 if await run_migrations() else 1
            elif args.command == "reset":
                confirm = input("WARNING: This will DELETE ALL DATA. Type 'yes' to confirm: ")
                if confirm != "yes":
                    logger.info("Reset cancelled")
                    return 0
                return 0 if await reset_database() else 1
            elif args.command == "status":
                await show_status()
                return 0
            elif args.command == "cleanup":
                count = await cleanup_cache()
                return 0 if count >= 0 else 1
        finally:
            await Database.close()

        return 0

    return asyncio.run(run())


if __name__ == "__main__":
    sys.exit(main())

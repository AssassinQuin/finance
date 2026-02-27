"""Database migration script."""

import asyncio
from fcli.core.config import config
from fcli.core.database import Database


async def create_tables():
    """Create database tables with optimized indexes."""
    if not Database.is_enabled():
        print("Database not enabled")
        return False

    pool = Database.get_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Migration tracking
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    version VARCHAR(50) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Gold reserves - optimized schema
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS gold_reserves (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    country_code VARCHAR(3) NOT NULL,
                    country_name VARCHAR(100) NOT NULL,
                    amount_tonnes DECIMAL(12,2) NOT NULL,
                    gold_share_pct DECIMAL(8,4),
                    gold_value_usd_m DECIMAL(18,2),
                    report_date DATE NOT NULL,
                    data_source VARCHAR(20) NOT NULL,
                    fetch_time DATETIME NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_country_date (country_code, report_date),
                    INDEX idx_report_date (report_date),
                    INDEX idx_country_code (country_code)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # Central bank schedules
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS central_bank_schedules (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    country_code VARCHAR(3) NOT NULL UNIQUE,
                    country_name VARCHAR(100) NOT NULL,
                    release_day TINYINT,
                    release_frequency VARCHAR(20) DEFAULT 'monthly',
                    last_release_date DATE,
                    next_expected_date DATE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_is_active (is_active),
                    INDEX idx_next_expected_date (next_expected_date)
                )
            """)

            # Fetch logs
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS fetch_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    data_type VARCHAR(50) NOT NULL,
                    source VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    records_count INT DEFAULT 0,
                    duration_ms INT DEFAULT 0,
                    error_message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_data_type_timestamp (data_type, timestamp),
                    INDEX idx_status (status)
                )
            """)

            # Quotes
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    name VARCHAR(100),
                    type ENUM('stock', 'fund', 'index', 'forex', 'bond', 'other') NOT NULL,
                    exchange VARCHAR(20),
                    price DECIMAL(18, 4),
                    change_pct DECIMAL(8, 4),
                    volume BIGINT,
                    quote_date DATE NOT NULL,
                    quote_time DATETIME,
                    data_source VARCHAR(50),
                    extra_data JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_symbol_date (symbol, quote_date),
                    INDEX idx_quote_date (quote_date),
                    INDEX idx_type_date (type, quote_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # Exchange rates
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS exchange_rates (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    from_currency VARCHAR(10) NOT NULL,
                    to_currency VARCHAR(10) NOT NULL,
                    rate DECIMAL(18, 8) NOT NULL,
                    rate_date DATE NOT NULL,
                    data_source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_pair_date (from_currency, to_currency, rate_date),
                    INDEX idx_rate_date (rate_date),
                    INDEX idx_pair (from_currency, to_currency)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # Watchlist assets
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS watchlist_assets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    code VARCHAR(20) NOT NULL UNIQUE,
                    api_code VARCHAR(50),
                    name VARCHAR(100),
                    market ENUM('CN', 'US', 'HK', 'GLOBAL', 'FOREX', 'FUND') NOT NULL DEFAULT 'CN',
                    type ENUM('STOCK', 'FUND', 'INDEX', 'FOREX', 'BOND') NOT NULL DEFAULT 'STOCK',
                    extra JSON,
                    is_active BOOLEAN DEFAULT TRUE,
                    added_at DATETIME,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_market_type (market, type),
                    INDEX idx_is_active (is_active)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # GPR history (Geopolitical Risk Index)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS gpr_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    country_code VARCHAR(3) NOT NULL,
                    report_date DATE NOT NULL,
                    gpr_index DECIMAL(10,2),
                    gpr_threat DECIMAL(10,2),
                    gpr_act DECIMAL(10,2),
                    data_source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_country_date (country_code, report_date),
                    INDEX idx_report_date (report_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            print("Tables created successfully")


async def migrate():
    """Run migration."""
    try:
        success = await Database.init(config)
        if not success:
            print("Database not configured or connection failed")
            return

        await create_tables()

        from fcli.core.stores import CentralBankScheduleStore

        await CentralBankScheduleStore.init_default_schedules()

        print("Migration completed successfully")

    except Exception as e:
        print(f"Migration failed: {e}")
        raise


async def rollback():
    """Rollback migration."""
    try:
        success = await Database.init(config)
        if not success:
            print("Database not configured")
            return

        pool = Database.get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                tables = [
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
                    await cur.execute(f"DROP TABLE IF EXISTS {table}")
                print("Rollback completed")
    except Exception as e:
        print(f"Rollback failed: {e}")
        raise


async def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m fcli.scripts.migrate [migrate|rollback]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "migrate":
        await migrate()
    elif command == "rollback":
        await rollback()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

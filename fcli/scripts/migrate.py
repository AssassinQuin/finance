"""
Database migration script.
Creates and necessary tables for gold reserve tracking.
"""

import asyncio
import os
from datetime import datetime
from typing import List

from fcli.core.config import config
from fcli.core.database import Database


async def create_tables():
    """Create database tables"""
    if not Database.is_enabled():
        print("Database not enabled")
        return False
    
    pool = Database.get_pool()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Create migrations table
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    version VARCHAR(50) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create gold_reserves table
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS gold_reserves (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    country_code VARCHAR(3) NOT NULL,
                    country_name VARCHAR(100) NOT NULL,
                    amount_tonnes DECIMAL(10,2) NOT NULL,
                    percent_of_reserves DECIMAL(5,2),
                    report_date DATE NOT NULL,
                    data_source VARCHAR(20) NOT NULL,
                    fetch_time DATETIME NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_country_date (country_code, report_date),
                    INDEX idx_report_date (report_date),
                    INDEX idx_country_code (country_code)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLate=utf8mb4_unicode_ci;
            """)
            
            # Create central_bank_schedules table
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
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # Create fetch_logs table
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
                    INDEX idx_data_type_timestamp (data_type, timestamp)
                )
            """)
            
            print("Tables created successfully")
            return True


async def run_migration():
    """Run migration"""
    try:
        if not Database.is_enabled():
            print("Database not configured, skipping migration")
            return
        
        # Initialize database
        await Database.init(config)
        
        # Create tables
        await create_tables()
        
        # Insert default schedules
        from fcli.core.database import CentralBankScheduleStore, CentralBankSchedule
        
        await CentralBankScheduleStore.init_default_schedules()
        
        print("Migration completed successfully")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        raise


async def rollback():
    """Rollback migration"""
    if not Database.is_enabled():
        return
        
    pool = Database.get_pool()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DROP TABLE IF EXISTS gold_reserves")
            await cur.execute("DROP TABLE IF EXISTS central_bank_schedules")
            await cur.execute("DROP TABLE IF EXISTS fetch_logs")
            await cur.execute("DROP TABLE IF EXISTS migrations")
            print("Rollback completed")


async def main():
    import asyncio
    import sys
    from fcli.core.config import config
    from fcli.core.database import Database
    
    # Parse command line arguments
    command = sys.argv[1] if sys.argv[1] in ["migrate", "rollback"]:
        commands = {
            "migrate": run_migration,
            "rollback": rollback_migration,
        }
        
        if command == "migrate":
            asyncio.run(run_migration())
        elif command == "rollback":
            asyncio.run(rollback_migration())
        else:
            print(f"Unknown command: {command}")
            print("Usage: python migrate.py [migrate|rollback]")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python
"""Migrate cache.json data to PostgreSQL cache_entries table.

Usage:
    python -m fcli.scripts.migrate_cache_to_pg
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

try:
    import asyncpg
except ImportError:
    print("Error: asyncpg not installed. Run: pip install asyncpg")
    exit(1)

# PostgreSQL configuration
PG_CONFIG = {
    "host": os.getenv("FCLI_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("FCLI_DB_PORT", "5432")),
    "user": os.getenv("FCLI_DB_USER", "postgres"),
    "password": os.getenv("FCLI_DB_PASSWORD", "123456zx"),
    "database": os.getenv("FCLI_DB_DATABASE", "fcli"),
}

# Cache file path
CACHE_FILE = Path(__file__).parent.parent.parent.parent / "data" / "cache.json"

# Default TTL for cache entries (in seconds)
DEFAULT_TTL = 86400  # 24 hours


async def migrate_cache():
    print("=" * 60)
    print("Cache.json to PostgreSQL Migration")
    print("=" * 60)
    print(f"Cache file: {CACHE_FILE}")
    print(f"PostgreSQL: {PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}")
    print()

    # Check if cache file exists
    if not CACHE_FILE.exists():
        print(f"Error: Cache file not found: {CACHE_FILE}")
        return

    # Read cache data
    print("Reading cache.json...")
    with open(CACHE_FILE, encoding="utf-8") as f:
        cache_data = json.load(f)

    print(f"Found {len(cache_data)} cache entries")
    print()

    # Connect to PostgreSQL
    print("Connecting to PostgreSQL...")
    conn = await asyncpg.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
        database=PG_CONFIG["database"],
    )

    try:
        # Insert cache entries
        print("Inserting cache entries...")
        count = 0
        now = datetime.now()

        for key, value in cache_data.items():
            expires_at = now + timedelta(seconds=DEFAULT_TTL)

            try:
                await conn.execute(
                    """
                    INSERT INTO cache_entries (key, value, expires_at, created_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        expires_at = EXCLUDED.expires_at,
                        created_at = EXCLUDED.created_at
                    """,
                    key,
                    json.dumps(value),
                    expires_at,
                    now,
                )
                count += 1
                print(f"  [{count}] {key}")
            except Exception as e:
                print(f"  Error inserting {key}: {e}")

        print()
        print(f"Successfully migrated {count} cache entries")

        # Verify
        result = await conn.fetchval("SELECT COUNT(*) FROM cache_entries")
        print(f"Total cache entries in PostgreSQL: {result}")

    finally:
        await conn.close()

    print("\nMigration completed!")


if __name__ == "__main__":
    asyncio.run(migrate_cache())

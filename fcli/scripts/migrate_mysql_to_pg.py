#!/usr/bin/env python
"""MySQL to PostgreSQL data migration script.

Usage:
    python -m fcli.scripts.migrate_mysql_to_pg

This script reads data from MySQL and inserts it into PostgreSQL.
Both databases must be running and accessible.
"""

import asyncio
import os
import sys
from datetime import datetime
from decimal import Decimal
from typing import Any

try:
    import aiomysql
except ImportError:
    print("Error: aiomysql not installed. Run: pip install aiomysql")
    sys.exit(1)

try:
    import asyncpg
except ImportError:
    print("Error: asyncpg not installed. Run: pip install asyncpg")
    sys.exit(1)


# MySQL configuration
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "123456zx"),
    "db": os.getenv("MYSQL_DATABASE", "fcli"),
}

# PostgreSQL configuration
PG_CONFIG = {
    "host": os.getenv("FCLI_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("FCLI_DB_PORT", "5432")),
    "user": os.getenv("FCLI_DB_USER", "postgres"),
    "password": os.getenv("FCLI_DB_PASSWORD", "123456zx"),
    "database": os.getenv("FCLI_DB_DATABASE", "fcli"),
}


def decimal_to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


async def migrate_table(
    mysql_conn: aiomysql.Connection,
    pg_conn: asyncpg.Connection,
    table_name: str,
    column_mapping: dict[str, str],
    transform_row: callable,
) -> int:
    """Migrate a single table from MySQL to PostgreSQL."""
    async with mysql_conn.cursor() as cursor:
        await cursor.execute(f"SELECT * FROM {table_name}")
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

    if not rows:
        print(f"  {table_name}: 0 rows (empty)")
        return 0

    count = 0
    for row in rows:
        row_dict = dict(zip(columns, row, strict=False))
        pg_data = transform_row(row_dict)

        pg_columns = list(column_mapping.keys())
        pg_values = [pg_data.get(column_mapping[c]) for c in pg_columns]
        placeholders = ", ".join(f"${i + 1}" for i in range(len(pg_columns)))
        column_names = ", ".join(pg_columns)

        upsert_columns = [c for c in pg_columns if c not in ("id", "created_at")]
        upsert_sets = ", ".join(f"{c} = EXCLUDED.{c}" for c in upsert_columns)

        sql = f"""
            INSERT INTO {table_name} ({column_names})
            VALUES ({placeholders})
            ON CONFLICT DO UPDATE SET {upsert_sets}
        """

        try:
            await pg_conn.execute(sql, *pg_values)
            count += 1
        except Exception as e:
            print(f"  Error inserting row: {e}")
            print(f"  Row data: {pg_data}")

    print(f"  {table_name}: {count} rows migrated")
    return count


def transform_central_bank_schedules(row: dict) -> dict:
    return {
        "country_code": row["country_code"],
        "country_name": row["country_name"],
        "release_frequency": row.get("release_frequency", "monthly"),
        "release_day_of_month": row.get("release_day"),
        "last_release_date": row.get("last_release_date"),
        "next_expected_date": row.get("next_expected_date"),
        "is_active": bool(row.get("is_active", True)),
    }


def transform_exchange_rates(row: dict) -> dict:
    return {
        "base_currency": row["from_currency"],
        "quote_currency": row["to_currency"],
        "rate": decimal_to_float(row["rate"]),
        "fetched_at": row.get("created_at") or datetime.now(),
    }


def transform_fetch_logs(row: dict) -> dict:
    return {
        "task_name": row["data_type"],
        "status": row["status"],
        "started_at": row.get("timestamp") or datetime.now(),
        "completed_at": None,
        "records_count": row.get("records_count", 0),
        "error_message": row.get("error_message"),
        "details": {"source": row.get("source"), "duration_ms": row.get("duration_ms")},
    }


def transform_gold_reserves(row: dict) -> dict:
    return {
        "country_code": row["country_code"],
        "country_name": row["country_name"],
        "gold_tonnes": decimal_to_float(row["amount_tonnes"]),
        "change_1m": None,
        "change_3m": None,
        "change_6m": None,
        "change_12m": None,
        "fetched_at": row.get("fetch_time") or datetime.now(),
        "data_date": row["report_date"],
    }


def transform_gold_supply_demand(row: dict) -> dict:
    return {
        "year": row["year"],
        "quarter": row["quarter"],
        "supply_total": decimal_to_float(row.get("total_supply")),
        "demand_total": decimal_to_float(row.get("total_demand")),
        "data_source": row.get("data_source"),
        "fetched_at": row.get("fetch_time") or datetime.now(),
    }


def transform_gpr_history(row: dict) -> dict:
    return {
        "gpr_value": decimal_to_float(row["gpr_value"]),
        "gpr_type": "monthly",
        "data_date": row["period"],
        "fetched_at": row.get("created_at") or datetime.now(),
    }


def transform_quotes(row: dict) -> dict:
    return {
        "code": row["symbol"],
        "name": row.get("name"),
        "price": decimal_to_float(row.get("price")),
        "change": None,
        "change_percent": decimal_to_float(row.get("change_pct")),
        "volume": row.get("volume"),
        "open": None,
        "high": None,
        "low": None,
        "prev_close": None,
        "market": row.get("exchange", "CN"),
        "quote_time": row.get("quote_time") or row.get("created_at") or datetime.now(),
    }


def transform_watchlist_assets(row: dict) -> dict:
    return {
        "code": row["code"],
        "name": row.get("name"),
        "market": row.get("market", "CN"),
        "asset_type": row.get("type", "STOCK"),
        "is_active": bool(row.get("is_active", True)),
    }


def transform_migrations(row: dict) -> dict:
    return {
        "version": row["version"],
        "applied_at": row.get("applied_at") or datetime.now(),
        "description": None,
    }


TABLE_MIGRATIONS = {
    "migrations": {
        "columns": {
            "version": "version",
            "applied_at": "applied_at",
            "description": "description",
        },
        "transform": transform_migrations,
    },
    "central_bank_schedules": {
        "columns": {
            "country_code": "country_code",
            "country_name": "country_name",
            "release_frequency": "release_frequency",
            "release_day_of_month": "release_day_of_month",
            "is_active": "is_active",
        },
        "transform": transform_central_bank_schedules,
    },
    "exchange_rates": {
        "columns": {
            "base_currency": "base_currency",
            "quote_currency": "quote_currency",
            "rate": "rate",
            "fetched_at": "fetched_at",
        },
        "transform": transform_exchange_rates,
    },
    "fetch_logs": {
        "columns": {
            "task_name": "task_name",
            "status": "status",
            "started_at": "started_at",
            "completed_at": "completed_at",
            "records_count": "records_count",
            "error_message": "error_message",
            "details": "details",
        },
        "transform": transform_fetch_logs,
    },
    "gold_reserves": {
        "columns": {
            "country_code": "country_code",
            "country_name": "country_name",
            "gold_tonnes": "gold_tonnes",
            "change_1m": "change_1m",
            "change_3m": "change_3m",
            "change_6m": "change_6m",
            "change_12m": "change_12m",
            "fetched_at": "fetched_at",
            "data_date": "data_date",
        },
        "transform": transform_gold_reserves,
    },
    "gold_supply_demand": {
        "columns": {
            "year": "year",
            "quarter": "quarter",
            "supply_total": "supply_total",
            "demand_total": "demand_total",
            "data_source": "data_source",
            "fetched_at": "fetched_at",
        },
        "transform": transform_gold_supply_demand,
    },
    "gpr_history": {
        "columns": {
            "gpr_value": "gpr_value",
            "gpr_type": "gpr_type",
            "data_date": "data_date",
            "fetched_at": "fetched_at",
        },
        "transform": transform_gpr_history,
    },
    "quotes": {
        "columns": {
            "code": "code",
            "name": "name",
            "price": "price",
            "change": "change",
            "change_percent": "change_percent",
            "volume": "volume",
            "open": "open",
            "high": "high",
            "low": "low",
            "prev_close": "prev_close",
            "market": "market",
            "quote_time": "quote_time",
        },
        "transform": transform_quotes,
    },
    "watchlist_assets": {
        "columns": {
            "code": "code",
            "name": "name",
            "market": "market",
            "asset_type": "asset_type",
            "is_active": "is_active",
        },
        "transform": transform_watchlist_assets,
    },
}


async def main():
    print("=" * 60)
    print("MySQL to PostgreSQL Migration")
    print("=" * 60)
    print(f"MySQL: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['db']}")
    print(f"PostgreSQL: {PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}")
    print()

    # Connect to MySQL
    print("Connecting to MySQL...")
    mysql_conn = await aiomysql.connect(
        host=MYSQL_CONFIG["host"],
        port=MYSQL_CONFIG["port"],
        user=MYSQL_CONFIG["user"],
        password=MYSQL_CONFIG["password"],
        db=MYSQL_CONFIG["db"],
        charset="utf8mb4",
    )

    # Connect to PostgreSQL
    print("Connecting to PostgreSQL...")
    pg_conn = await asyncpg.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
        database=PG_CONFIG["database"],
    )

    print("\nMigrating tables...")
    print("-" * 40)

    total_rows = 0
    for table_name, config in TABLE_MIGRATIONS.items():
        try:
            count = await migrate_table(
                mysql_conn,
                pg_conn,
                table_name,
                config["columns"],
                config["transform"],
            )
            total_rows += count
        except Exception as e:
            print(f"  {table_name}: Error - {e}")

    print("-" * 40)
    print(f"\nTotal rows migrated: {total_rows}")

    # Close connections
    mysql_conn.close()
    await pg_conn.close()

    print("\nMigration completed!")


if __name__ == "__main__":
    asyncio.run(main())

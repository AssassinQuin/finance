"""Import SPDR holdings from cache.json to PostgreSQL."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fcli.core.config import config
from fcli.core.database import Database

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_FILE = project_root / "data" / "cache.json"


async def import_spdr_holdings() -> int:
    if not CACHE_FILE.exists():
        logger.error(f"Cache file not found: {CACHE_FILE}")
        return 0

    with open(CACHE_FILE, "r") as f:
        cache_data = json.load(f)

    spdr_data = cache_data.get("spdr:holdings", {}).get("data", [])
    if not spdr_data:
        logger.error("No SPDR holdings data found in cache")
        return 0

    logger.info(f"Found {len(spdr_data)} SPDR holdings records")

    await Database.init(config)
    if not Database.is_enabled():
        logger.error("Database not connected")
        return 0

    inserted = 0
    for record in spdr_data:
        try:
            data_date = datetime.strptime(record["date"], "%Y-%m-%d").date()
            await Database.execute(
                """
                INSERT INTO spdr_holdings (data_date, holdings, change, value)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (data_date) DO UPDATE SET
                    holdings = EXCLUDED.holdings,
                    change = EXCLUDED.change,
                    value = EXCLUDED.value,
                    fetched_at = CURRENT_TIMESTAMP
                """,
                data_date,
                record["holdings"],
                record["change"],
                record["value"],
            )
            inserted += 1
        except Exception as e:
            logger.warning(f"Failed to insert {record['date']}: {e}")

    await Database.close()
    logger.info(f"Imported/updated {inserted} records")
    return inserted


if __name__ == "__main__":
    count = asyncio.run(import_spdr_holdings())
    sys.exit(0 if count > 0 else 1)

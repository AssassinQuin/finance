"""
Import WGC Gold Supply/Demand data from Excel file to database.

Usage:
    # Import from local Excel file
    python -m fcli.scripts.import_wgc_data --file /path/to/GDT_Tables_Q425_CN.xlsx

    # Download and import latest data
    python -m fcli.scripts.import_wgc_data --download

    # Import specific year/quarter from WGC
    python -m fcli.scripts.import_wgc_data --year 2024 --quarter 4

    # Force overwrite existing data
    python -m fcli.scripts.import_wgc_data --file data.xlsx --force
"""

from __future__ import annotations

import argparse
import logging

from fcli.core.models.gold_supply_demand import GoldSupplyDemand
from fcli.core.stores.gold_supply_demand import gold_supply_demand_store
from fcli.infra.http_client import HttpClient, run_async
from fcli.services.scrapers.wgc_scraper import QuarterlySupplyDemand, WGCScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def convert_to_model(qsd: QuarterlySupplyDemand) -> GoldSupplyDemand:
    """Convert scraper dataclass to database model."""
    return GoldSupplyDemand(
        year=qsd.year,
        quarter=qsd.quarter,
        period=qsd.period,
        mine_production=qsd.mine_production,
        recycling=qsd.recycling,
        net_hedging=qsd.net_hedging,
        total_supply=qsd.total_supply,
        jewelry=qsd.jewelry,
        technology=qsd.technology,
        total_investment=qsd.total_investment,
        bars_coins=qsd.bars_coins,
        etfs=qsd.etfs,
        otc_investment=qsd.otc_investment,
        central_banks=qsd.central_banks,
        total_demand=qsd.total_demand,
        supply_demand_balance=qsd.supply_demand_balance,
        price_avg_usd=qsd.price_avg_usd,
        data_source=qsd.source,
    )


def print_summary(data: list[QuarterlySupplyDemand]) -> None:
    """Print a summary of the imported data."""
    if not data:
        print("\nNo data to display.")
        return

    print(f"\n{'Period':<12} {'Supply':>12} {'Demand':>12} {'Balance':>10} {'Price':>12}")
    print("-" * 60)

    for qsd in sorted(data, key=lambda x: (x.year, x.quarter), reverse=True)[:20]:
        balance = qsd.supply_demand_balance
        price_str = f"${qsd.price_avg_usd:,.0f}" if qsd.price_avg_usd else "N/A"
        print(
            f"{qsd.period:<12} {qsd.total_supply:>12,.1f} {qsd.total_demand:>12,.1f} {balance:>10,.1f} {price_str:>12}"
        )

    if len(data) > 20:
        print(f"... and {len(data) - 20} more quarters")

    print(f"\nTotal: {len(data)} quarters")


async def import_from_file(file_path: str, force: bool = False) -> int:
    """
    Import data from a local Excel file.

    Args:
        file_path: Path to the WGC Excel file
        force: Force overwrite existing data

    Returns:
        Number of quarters imported
    """
    logger.info(f"Importing from file: {file_path}")

    scraper = WGCScraper(http_client=HttpClient())
    data = scraper.fetch_from_local(file_path)
    if not data:
        logger.error("No data found in file")
        return 0

    logger.info(f"Found {len(data)} quarters in file")
    print_summary(data)

    # Save to database
    saved = 0
    for qsd in data:
        # Check if exists
        if not force:
            existing = await gold_supply_demand_store.get_by_quarter(qsd.year, qsd.quarter)
            if existing:
                logger.debug(f"Data exists for {qsd.year} Q{qsd.quarter}, skipping")
                continue

        model = convert_to_model(qsd)
        success = await gold_supply_demand_store.save_quarterly(model)
        if success:
            saved += 1
            logger.info(f"Imported {qsd.year} Q{qsd.quarter}")

    logger.info(f"Total imported: {saved} quarters")
    return saved


async def import_from_download(force: bool = False) -> int:
    """
    Download and import latest data from WGC.

    Args:
        force: Force overwrite existing data

    Returns:
        Number of quarters imported
    """
    logger.info("Downloading latest WGC data...")

    scraper = WGCScraper(http_client=HttpClient())
    data = await scraper.fetch_latest()
    if not data:
        logger.error("Could not download any data")
        return 0

    logger.info(f"Downloaded {len(data)} quarters")
    print_summary(data)

    saved = 0
    for qsd in data:
        if not force:
            existing = await gold_supply_demand_store.get_by_quarter(qsd.year, qsd.quarter)
            if existing:
                continue

        model = convert_to_model(qsd)
        success = await gold_supply_demand_store.save_quarterly(model)
        if success:
            saved += 1

    logger.info(f"Total imported: {saved} quarters")
    return saved


async def main_async(args: argparse.Namespace) -> int:
    """Main async entry point."""
    if args.file:
        return await import_from_file(args.file, args.force)
    elif args.download:
        return await import_from_download(args.force)
    else:
        logger.error("Please specify --file or --download")
        return 0


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Import WGC gold supply/demand data to database")
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        help="Path to WGC Excel file (e.g., GDT_Tables_Q425_CN.xlsx)",
    )
    parser.add_argument(
        "--download",
        "-d",
        action="store_true",
        help="Download latest data from WGC",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite existing data",
    )

    args = parser.parse_args()
    run_async(main_async(args))


if __name__ == "__main__":
    main()

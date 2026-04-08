"""
Save gold reserves history to database using IMF SDMX 3.0 API.

Data source: IMF IRFCL (International Reserves and Foreign Currency Liquidity)

Usage:
    python -m fcli.scripts.save_gold_reserves
    python -m fcli.scripts.save_gold_reserves --countries USA,CHN,DEU
    python -m fcli.scripts.save_gold_reserves --years 5
    python -m fcli.scripts.save_gold_reserves --latest  # 仅获取最新一个月
"""

import argparse
import logging
from datetime import date, datetime

from fcli.core.config import config
from fcli.core.database import Database
from fcli.core.models import GoldReserve
from fcli.core.stores.gold import gold_reserve_store
from fcli.infra.http_client import HttpClient, run_async
from fcli.services.scrapers.imf_scraper import IMFScraper
from fcli.utils.time_util import MONTH_FORMAT, utcnow

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# 黄金价格用于USD转换为吨数 (从配置获取)
GRAMS_PER_OUNCE = 31.1035


def _get_gold_price() -> float:
    """获取黄金价格配置"""
    return config.gold.price_usd_per_ounce


def usd_to_tonnes(usd_millions: float, gold_price: float | None = None) -> float:
    """
    将百万美元黄金储备转换为吨数

    Args:
        usd_millions: 黄金储备价值 (百万美元)
        gold_price: 黄金价格 (美元/盎司)

    Returns:
        黄金储备 (吨)
    """
    if not usd_millions or usd_millions <= 0:
        return 0.0

    # 百万美元 -> 美元
    usd = usd_millions * 1_000_000

    # 美元 -> 盎司
    if gold_price is None:
        gold_price = _get_gold_price()
    ounces = usd / gold_price

    # 盎司 -> 克 -> 吨
    grams = ounces * GRAMS_PER_OUNCE
    tonnes = grams / 1_000_000

    return round(tonnes, 2)


async def save_latest_reserves(scraper: IMFScraper, country_codes: list[str] | None = None) -> int:
    """
    保存各国最新一个月的黄金储备

    Args:
        scraper: IMF爬虫实例
        country_codes: 国家代码列表

    Returns:
        保存的记录数
    """
    logger.info("Fetching latest gold reserves for all countries...")

    results = await scraper.batch_get_latest_reserves(country_codes)

    if not results:
        logger.warning("No data fetched")
        return 0

    reserves = []
    fetch_time = utcnow()

    for item in results:
        period = item.get("period", "")
        report_date = date.today()
        if period:
            try:
                # period格式: YYYY-MM
                report_date = datetime.strptime(period, MONTH_FORMAT).date()
            except (ValueError, TypeError):
                pass

        value = item.get("value", 0)
        # IMF scraper returns tonnes directly, no conversion needed
        tonnes = value if value else 0.0
        reserve = GoldReserve(
            country_code=item["country_code"],
            country_name=item.get("country_name", item["country_code"]),
            amount_tonnes=tonnes,
            percent_of_reserves=None,
            report_date=report_date,
            data_source="IMF",
            fetch_time=fetch_time,
        )
        reserves.append(reserve)

    saved = await gold_reserve_store.save_batch(reserves)
    logger.info(f"Saved {saved} latest reserve records")

    return saved


async def save_history_reserves(scraper: IMFScraper, country_codes: list[str] | None = None, years: int = 10) -> int:
    """
    保存各国近N年的月度黄金储备历史

    Args:
        scraper: IMF爬虫实例
        country_codes: 国家代码列表
        years: 年数

    Returns:
        保存的记录数
    """
    logger.info(f"Fetching {years} years of gold reserves history...")

    results = await scraper.batch_get_history(country_codes, years)

    if not results:
        logger.warning("No data fetched")
        return 0

    all_reserves = []
    fetch_time = utcnow()

    for country_data in results:
        country_code = country_data.get("country_code")
        country_name = country_data.get("country_name", country_code)
        data = country_data.get("data", {})

        print(f"  Processing {country_code}: {len(data)} periods in data")

        if not data:
            print(f"    WARNING: No data for {country_code}")
            continue

        for period, value_usd in data.items():
            # 解析多种period格式: "2024", "2024-M01", "2024-01", "2024-Q1"
            try:
                if "-M" in period:
                    # 月度格式: 2024-M01 -> 2024-01
                    parts = period.split("-M")
                    report_date = datetime(int(parts[0]), int(parts[1]), 1).date()
                elif "-Q" in period:
                    # 季度格式: 2024-Q1 -> 季度末
                    parts = period.split("-Q")
                    quarter = int(parts[1])
                    month = quarter * 3
                    report_date = datetime(int(parts[0]), month, 1).date()
                elif len(period) == 7 and "-" in period:
                    # 已转换的月度格式: 2025-02 -> date
                    year, month = period.split("-")
                    report_date = datetime(int(year), int(month), 1).date()
                else:
                    # 年度格式: 2024 -> 年末
                    report_date = datetime(int(period), 12, 1).date()
            except (ValueError, TypeError, IndexError) as e:
                print(f"    Skipping invalid period: {period} ({e})")
                continue
            # IMF scraper returns tonnes directly, no conversion needed
            tonnes = value_usd if value_usd else 0.0

            reserve = GoldReserve(
                country_code=country_code,
                country_name=country_name,
                amount_tonnes=tonnes,
                percent_of_reserves=None,
                report_date=report_date,
                data_source="IMF",
                fetch_time=fetch_time,
            )
            all_reserves.append(reserve)

    print(f"Total reserves created: {len(all_reserves)}")

    if not all_reserves:
        logger.warning("No valid reserve records to save")
        return 0

    logger.info(f"Total {len(all_reserves)} records to save...")

    # 分批保存，每批500条
    batch_size = 500
    total_saved = 0

    for i in range(0, len(all_reserves), batch_size):
        batch = all_reserves[i : i + batch_size]
        saved = await gold_reserve_store.save_batch(batch)
        total_saved += saved
        logger.info(f"Saved batch {i // batch_size + 1}: {saved} records")

    logger.info(f"Total saved: {total_saved} history records")

    return total_saved


async def verify_data():
    """验证保存的数据"""
    logger.info("Verifying saved data...")

    pool = Database.get_pool()
    if not pool:
        logger.warning("Database pool not available")
        return

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT country_code, country_name,
                   COUNT(*) as records,
                   MIN(report_date) as min_date,
                   MAX(report_date) as max_date,
                   (SELECT gr2.gold_tonnes FROM gold_reserves gr2
                    WHERE gr2.country_code = gr.country_code
                    ORDER BY gr2.report_date DESC LIMIT 1) as latest_amount
            FROM gold_reserves gr
            GROUP BY country_code, country_name
            ORDER BY latest_amount DESC
            LIMIT 30
        """)

        if rows:
            print(f"\n{'国家':<20} {'记录数':<8} {'最早':<12} {'最新':<12} {'最新储量(吨)':<15}")
            print("-" * 70)
            for row in rows:
                code = row["country_code"]
                name = row["country_name"]
                count = row["records"]
                min_date = row["min_date"]
                max_date = row["max_date"]
                amount = row["latest_amount"]
                name_display = name[:18] if name else code
                amount_str = f"{amount:.2f}" if amount else "N/A"
                print(f"{name_display:<20} {count:<8} {min_date} {max_date} {amount_str:<15}")

            print(f"\n共 {len(rows)} 个国家/地区")
        else:
            print("No data found")


async def main():
    parser = argparse.ArgumentParser(description="Save gold reserves from IMF API")
    parser.add_argument("--countries", type=str, help="Comma-separated country codes (e.g., USA,CHN,DEU)")
    parser.add_argument("--years", type=int, default=10, help="Years of history to fetch (default: 10)")
    parser.add_argument("--latest", action="store_true", help="Only fetch latest month data")
    args = parser.parse_args()

    # 解析国家代码
    country_codes = None
    if args.countries:
        country_codes = [c.strip().upper() for c in args.countries.split(",")]

    # 初始化数据库
    success = await Database.init(config)
    if not success:
        logger.error("Database connection failed")
        return

    try:
        scraper = IMFScraper(http_client=HttpClient(), settings=config)

        if args.latest:
            saved = await save_latest_reserves(scraper, country_codes)
        else:
            saved = await save_history_reserves(scraper, country_codes, args.years)

        if saved > 0:
            await verify_data()
        else:
            logger.warning("No data saved")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise
    finally:
        await Database.close()


if __name__ == "__main__":
    run_async(main())

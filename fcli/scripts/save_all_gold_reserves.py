"""
Save all official gold reserves history to database.

Data sources:
1. WGC local JSON file (gold_reserves_history.json) - Top 20 countries
2. SAFE official data - China monthly data

Usage:
    python -m fcli.scripts.save_all_gold_reserves       # Save all data
    python -m fcli.scripts.save_all_gold_reserves --verify  # Verify saved data
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from fcli.core.config import config
from fcli.core.database import Database, GoldReserveStore, GoldReserve
from fcli.services.scrapers.safe_scraper import SAFEScraper


# Local data file path
LOCAL_DATA_FILE = Path(__file__).parent.parent.parent / "data" / "gold_reserves_history.json"


async def save_wgc_history():
    """Save WGC historical data from local JSON file."""
    
    if not LOCAL_DATA_FILE.exists():
        print(f"Local data file not found: {LOCAL_DATA_FILE}")
        return 0
    
    try:
        with open(LOCAL_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load local data: {e}")
        return 0
    
    reserves_data = data.get("reserves", {})
    print(f"Found {len(reserves_data)} countries in local data")
    
    fetch_time = datetime.now()
    reserves = []
    
    for country_code, country_data in reserves_data.items():
        country_name = country_data.get("country_name", country_code)
        percent_of_reserves = country_data.get("percent_of_reserves")
        history = country_data.get("history", [])
        
        for item in history:
            try:
                date_str = item.get("date", "")
                amount = float(item.get("amount", 0))
                
                if not date_str or amount <= 0:
                    continue
                
                # Parse date from "YYYY-MM" format
                report_date = datetime.strptime(date_str, "%Y-%m").date()
                
                reserve = GoldReserve(
                    country_code=country_code,
                    country_name=country_name,
                    amount_tonnes=amount,
                    percent_of_reserves=percent_of_reserves,
                    report_date=report_date,
                    data_source="WGC",
                    fetch_time=fetch_time,
                )
                reserves.append(reserve)
            except Exception as e:
                print(f"Failed to parse {country_code} {item}: {e}")
                continue
    
    if not reserves:
        print("No WGC records to save")
        return 0
    
    # Save to database
    saved = await GoldReserveStore.save_batch(reserves)
    print(f"Saved {saved} WGC records")
    return saved


async def save_safe_history():
    """Save China gold reserve history from SAFE official source."""
    
    print("Fetching China gold reserve history from SAFE...")
    scraper = SAFEScraper()
    result = await scraper.fetch()
    
    if not result or not result.get("data"):
        print("No data fetched from SAFE")
        return 0
    
    print(f"Fetched {len(result['data'])} records from SAFE")
    
    fetch_time = datetime.now()
    reserves = []
    
    for item in result["data"]:
        try:
            date_str = item.get("date", "")
            report_date = datetime.strptime(date_str, "%Y-%m").date()
            
            reserve = GoldReserve(
                country_code=item["country_code"],
                country_name=item["country_name"],
                amount_tonnes=float(item["amount"]),
                percent_of_reserves=None,
                report_date=report_date,
                data_source="SAFE",
                fetch_time=fetch_time,
            )
            reserves.append(reserve)
        except Exception as e:
            print(f"Failed to parse SAFE item {item}: {e}")
            continue
    
    if not reserves:
        print("No SAFE records to save")
        return 0
    
    saved = await GoldReserveStore.save_batch(reserves)
    print(f"Saved {saved} SAFE records")
    return saved


async def save_all_gold_reserves():
    """Save all official gold reserve history to database."""
    
    # Initialize database
    success = await Database.init(config)
    if not success:
        print("Database connection failed")
        return False
    
    try:
        total_saved = 0
        
        # 1. Save WGC historical data
        print("\n=== Saving WGC historical data ===")
        wgc_saved = await save_wgc_history()
        total_saved += wgc_saved
        
        # 2. Save SAFE (China) data - will override WGC China data for overlapping months
        print("\n=== Saving SAFE (China) data ===")
        safe_saved = await save_safe_history()
        total_saved += safe_saved
        
        print(f"\n=== Total: {total_saved} records saved ===")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        await Database.close()


async def verify_data():
    """Verify saved data."""
    
    success = await Database.init(config)
    if not success:
        print("Database connection failed")
        return
    
    try:
        # Get all countries with data
        pool = Database.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT country_code, country_name, data_source, 
                           COUNT(*) as records, 
                           MIN(report_date) as min_date, 
                           MAX(report_date) as max_date
                    FROM gold_reserves
                    GROUP BY country_code, country_name, data_source
                    ORDER BY MAX(report_date) DESC
                """)
                rows = await cur.fetchall()
                
                print(f"\n{'国家':<15} {'代码':<5} {'来源':<10} {'记录数':<8} {'最早日期':<12} {'最新日期'}")
                print("-" * 75)
                
                for row in rows:
                    country_code, country_name, source, count, min_date, max_date = row
                    print(f"{country_name:<15} {country_code:<5} {source:<10} {count:<8} {min_date} {max_date}")
                
                print(f"\n总计: {len(rows)} 个国家/来源组合")
                
    finally:
        await Database.close()


async def main():
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        await verify_data()
    else:
        success = await save_all_gold_reserves()
        if success:
            print("\n✅ All gold reserve history saved to database")
            await verify_data()
        else:
            print("\n❌ Failed to save gold reserve history")


if __name__ == "__main__":
    asyncio.run(main())

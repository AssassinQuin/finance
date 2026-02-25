#!/usr/bin/env python3
"""
FRED API 脚本 - 获取美国黄金储备数据

正确的 FRED Series ID:
- FKKYGTA: U.S. Mint Held Gold Deep Storage: Fort Knox, KY (Fine Troy Ounces)
- DNVCOGTA: U.S. Mint Held Gold Deep Storage: Denver, CO (Fine Troy Ounces)
- WPNYGTA: U.S. Mint Held Gold Deep Storage: West Point, NY (Fine Troy Ounces)
- FRVGBSAM: Federal Reserve Bank Held Gold Bullion: NY Vault (Fine Troy Ounces)

使用方法:
    python test_fred_api.py              # 获取最新数据
    python test_fred_api.py --history    # 获取历史数据 (24个月)
    python test_fred_api.py --save       # 保存到数据库
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Optional

# FRED API Token
FRED_API_KEY = "660aa94e7df28909d71e1262807b8b58"

# FRED Series ID - 美国黄金储备
FRED_GOLD_SERIES = {
    "FKKYGTA": {"name": "Fort Knox", "location": "Kentucky"},
    "DNVCOGTA": {"name": "Denver", "location": "Colorado"},
    "WPNYGTA": {"name": "West Point", "location": "New York"},
    "FRVGBSAM": {"name": "Federal Reserve NY Vault", "location": "New York"},
}

# 单位转换: Fine Troy Ounces -> Tonnes
OZ_TO_TONNE = 0.0000311034768


async def fetch_series(
    session: aiohttp.ClientSession,
    series_id: str,
    start_date: str = "2024-01-01",
    end_date: str = None,
) -> Optional[Dict]:
    """使用 aiohttp 获取 FRED 数据系列"""
    base_url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start_date,
    }
    if end_date:
        params["observation_end"] = end_date

    try:
        async with session.get(base_url, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                text = await resp.text()
                return {"error": f"HTTP {resp.status}: {text[:100]}"}
    except Exception as e:
        return {"error": str(e)}


async def fetch_all_components() -> Dict:
    """获取所有美国黄金储备组成部分"""
    print("=" * 60)
    print("获取美国黄金储备数据")
    print("=" * 60)
    
    results = {}
    
    # 创建带代理的 session
    async with aiohttp.ClientSession() as session:
        for series_id, info in FRED_GOLD_SERIES.items():
            print(f"\n📡 获取 {info['name']} ({series_id})...")
            data = await fetch_series(session, series_id, "2024-01-01")
            
            if "error" in data:
                print(f"  ❌ {data['error']}")
                continue
            
            if "observations" in data:
                obs = [
                    o
                    for o in data["observations"]
                    if o.get("value") and o["value"] != "."
                ]
                if obs:
                    latest = obs[-1]
                    oz = float(latest["value"])
                    tonnes = oz * OZ_TO_TONNE
                    
                    results[series_id] = {
                        "name": info["name"],
                        "location": info["location"],
                        "date": latest["date"],
                        "ounces": oz,
                        "tonnes": round(tonnes, 2),
                        "history": obs,
                    }
                    print(f"  ✅ {latest['date']}: {oz:,.0f} oz = {tonnes:.2f} 吨")
                else:
                    print("  ⚠️ 无有效数据")
            else:
                print("  ❌ 数据格式错误")
    
    return results


def print_summary(results: Dict):
    """打印汇总信息"""
    print("\n" + "=" * 60)
    print("美国黄金储备汇总")
    print("=" * 60)

    total_oz = 0
    total_tonnes = 0

    print(f"\n{'存储地点':<25} {'盎司':>18} {'吨':>12}")
    print("-" * 60)

    for series_id, data in results.items():
        oz = data["ounces"]
        tonnes = data["tonnes"]
        total_oz += oz
        total_tonnes += tonnes
        print(f"{data['name']:<25} {oz:>18,.0f} {tonnes:>12.2f}")

    print("-" * 60)
    print(f"{'总计':<25} {total_oz:>18,.0f} {total_tonnes:>12.2f}")
    print(f"\n官方数据: 261,498,899 oz = 8,133.46 吨")


async def save_to_database(results: Dict):
    """保存到数据库"""
    print("\n" + "=" * 60)
    print("保存到数据库")
    print("=" * 60)

    try:
        import sys

        sys.path.insert(0, ".")

        from fcli.core.config import config
        from fcli.core.database import Database, GoldReserveStore, GoldReserve

        success = await Database.init(config)
        if not success:
            print("❌ 数据库连接失败")
            return

        fetch_time = datetime.now()

        # 计算总储备
        total_oz = sum(d["ounces"] for d in results.values())
        total_tonnes = total_oz * OZ_TO_TONNE

        # 获取最新日期
        latest_date = max(d["date"] for d in results.values())
        report_date = datetime.strptime(latest_date[:10], "%Y-%m-%d").date()

        reserve = GoldReserve(
            country_code="USA",
            country_name="美国",
            amount_tonnes=round(total_tonnes, 2),
            percent_of_reserves=None,
            report_date=report_date,
            data_source="FRED",
            fetch_time=fetch_time,
        )

        saved = await GoldReserveStore.save_batch([reserve])
        print(f"✅ 保存 {saved} 条记录 (美国黄金储备: {total_tonnes:.2f} 吨)")

        await Database.close()

    except ImportError as e:
        print(f"❌ 导入失败: {e}")


async def get_history(results: Dict, months: int = 24):
    """获取历史数据"""
    print("\n" + "=" * 60)
    print(f"美国黄金储备历史 ({months} 个月)")
    print("=" * 60)

    # 合并所有组成部分的历史数据
    monthly_totals = {}

    for series_id, data in results.items():
        for obs in data.get("history", []):
            date = obs["date"][:7]  # YYYY-MM
            if obs["value"] and obs["value"] != ".":
                oz = float(obs["value"])
                if date not in monthly_totals:
                    monthly_totals[date] = 0
                monthly_totals[date] += oz

    # 转换为吨并打印
    print(f"\n{'日期':<12} {'储备量(吨)':<15} {'月变化'}")
    print("-" * 45)

    prev_tonnes = None
    for date in sorted(monthly_totals.keys())[-months:]:
        oz = monthly_totals[date]
        tonnes = oz * OZ_TO_TONNE

        change = ""
        if prev_tonnes:
            diff = tonnes - prev_tonnes
            change = f"{diff:+.2f}"

        print(f"{date:<12} {tonnes:<15.2f} {change}")
        prev_tonnes = tonnes


async def main():
    import sys

    results = await fetch_all_components()

    if not results:
        print("\n❌ 无法获取任何数据")
        return

    print_summary(results)

    if "--history" in sys.argv:
        await get_history(results)

    if "--save" in sys.argv:
        await save_to_database(results)


if __name__ == "__main__":
    asyncio.run(main())

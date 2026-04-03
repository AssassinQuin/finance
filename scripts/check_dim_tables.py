"""检查 dim_asset 和 dim_currency 表结构"""

import asyncio

from fcli.core.config import config
from fcli.core.database import Database


async def main():
    await Database.init(config)

    print("=== 检查维度表结构 ===\n")

    print("--- dim_asset ---")
    assets = await Database.fetch_all("SELECT * FROM dim_asset ORDER BY id")
    print(f"行数: {len(assets)}")
    for a in assets:
        print(f"  id={a['id']}, code={a['asset_code']}, name={a['asset_name']}, type={a.get('asset_type')}")

    print("\n--- dim_currency ---")
    currencies = await Database.fetch_all("SELECT * FROM dim_currency ORDER BY id")
    print(f"行数: {len(currencies)}")
    for c in currencies:
        print(f"  id={c['id']}, code={c['currency_code']}, name={c.get('currency_name')}")

    print("\n--- dim_data_source ---")
    sources = await Database.fetch_all("SELECT * FROM dim_data_source ORDER BY id")
    print(f"行数: {len(sources)}")
    for s in sources:
        print(f"  id={s['id']}, name={s['source_name']}, type={s.get('source_type')}")

    await Database.close()


if __name__ == "__main__":
    asyncio.run(main())

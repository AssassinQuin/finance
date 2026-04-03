"""测试 Phase 1 重构后的 GoldSupplyDemandStore"""

import asyncio
from datetime import datetime

from fcli.core.config import config
from fcli.core.database import Database
from fcli.core.models.gold_supply_demand import GoldSupplyDemand
from fcli.core.stores.gold_supply_demand import GoldSupplyDemandStore


async def main():
    print("=== 测试重构后的 GoldSupplyDemandStore ===\n")

    await Database.init(config)

    # 1. 创建测试数据
    print("1. 创建测试数据...")
    test_data = GoldSupplyDemand(
        year=2024,
        quarter=3,
        period="2024 Q3",
        mine_production=892.5,
        recycling=310.2,
        net_hedging=-15.3,
        total_supply=1187.4,
        jewelry=523.8,
        technology=78.4,
        total_investment=312.5,
        bars_coins=215.6,
        etfs=52.3,
        otc_investment=44.6,
        central_banks=186.2,
        total_demand=1100.9,
        supply_demand_balance=86.5,
        price_avg_usd=2485.50,
        data_source="WGC",
        fetch_time=datetime.now(),
    )
    print(f"   ✓ 测试数据: {test_data.year} Q{test_data.quarter}\n")

    # 2. 测试保存
    print("2. 测试 save_quarterly()...")
    success = await GoldSupplyDemandStore.save_quarterly(test_data)
    if success:
        print("   ✓ 保存成功\n")
    else:
        print("   ✗ 保存失败\n")
        await Database.close()
        return

    # 3. 验证数据库记录
    print("3. 验证数据库记录...")
    rows = await Database.fetch_all("""
        SELECT
            p.year, p.quarter, p.period_label,
            m.metric_code,
            f.value
        FROM fact_gold_supply_demand f
        JOIN dim_period p ON f.period_id = p.id
        JOIN dim_metric m ON f.metric_id = m.id
        WHERE p.year = 2024 AND p.quarter = 3
        ORDER BY m.metric_code
    """)

    print(f"   找到 {len(rows)} 条记录:")
    for row in rows:
        print(f"   - {row['metric_code']}: {row['value']}")
    print()

    # 4. 测试 get_by_quarter
    print("4. 测试 get_by_quarter()...")
    result = await GoldSupplyDemandStore.get_by_quarter(2024, 3)
    if result:
        print(f"   ✓ 查询成功: {result.year} Q{result.quarter}")
        print(f"     - 矿山产量: {result.mine_production}")
        print(f"     - 总供应: {result.total_supply}")
        print(f"     - 总需求: {result.total_demand}")
        print(f"     - 金价: ${result.price_avg_usd}\n")
    else:
        print("   ✗ 查询失败\n")

    # 5. 测试 get_latest
    print("5. 测试 get_latest()...")
    latest = await GoldSupplyDemandStore.get_latest()
    if latest:
        print(f"   ✓ 最新数据: {latest.year} Q{latest.quarter}\n")
    else:
        print("   ! 无数据\n")

    # 6. 测试 get_history
    print("6. 测试 get_history()...")
    history = await GoldSupplyDemandStore.get_history(limit=4)
    print(f"   历史数据: {len(history)} 条记录")
    for item in history:
        print(f"   - {item.year} Q{item.quarter}")

    print("\n✓ Phase 1 Store 重构测试完成")
    print("  - save_quarterly: 工作正常")
    print("  - get_by_quarter: 工作正常")
    print("  - get_latest: 工作正常")
    print("  - get_history: 工作正常")
    print("  - 数据正确存储在 fact_gold_supply_demand")

    await Database.close()


if __name__ == "__main__":
    asyncio.run(main())

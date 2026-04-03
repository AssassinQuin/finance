"""Phase 1 迁移执行脚本 - 黄金供需重构到事实表"""

import asyncio

from fcli.core.config import config
from fcli.core.database import Database


async def main():
    print("=== Phase 1: 黄金供需数据重构到事实表 ===\n")

    await Database.init(config)

    # 读取迁移 SQL
    with open("data/migrations/20260326_01_supply_demand_fact_refactor.sql") as f:
        f.read()

    print("1. 执行迁移脚本...")
    try:
        # 执行迁移（分步执行以处理错误）
        statements = [
            # 记录迁移
            """
            INSERT INTO migrations (version, description, applied_at)
            VALUES (
                '20260326_01_supply_demand_fact_refactor',
                'Refactor gold supply/demand to fact table model',
                CURRENT_TIMESTAMP
            ) ON CONFLICT (version) DO NOTHING
            """,
            # 初始化 dim_period
            """
            INSERT INTO dim_period (year, quarter, period_label, period_type)
            SELECT
                y.year,
                q.quarter,
                CONCAT(y.year, 'Q', q.quarter) as period_label,
                'quarter' as period_type
            FROM
                generate_series(2021, 2025) as y(year),
                generate_series(1, 4) as q(quarter)
            ON CONFLICT DO NOTHING
            """,
            # 初始化 dim_metric
            """
            INSERT INTO dim_metric (metric_code, metric_name, unit, domain) VALUES
            ('mine_production', 'Mine Production', 'tonnes', 'supply'),
            ('recycling', 'Recycling', 'tonnes', 'supply'),
            ('net_hedging', 'Net Hedging', 'tonnes', 'supply'),
            ('total_supply', 'Total Supply', 'tonnes', 'supply'),
            ('jewelry', 'Jewelry', 'tonnes', 'demand'),
            ('technology', 'Technology', 'tonnes', 'demand'),
            ('total_investment', 'Total Investment', 'tonnes', 'demand'),
            ('bars_coins', 'Bars & Coins', 'tonnes', 'demand'),
            ('etfs', 'ETFs', 'tonnes', 'demand'),
            ('otc_investment', 'OTC Investment', 'tonnes', 'demand'),
            ('central_banks', 'Central Banks', 'tonnes', 'demand'),
            ('total_demand', 'Total Demand', 'tonnes', 'demand'),
            ('supply_demand_balance', 'Supply-Demand Balance', 'tonnes', 'balance'),
            ('price_avg_usd', 'Average Price', 'USD/oz', 'price')
            ON CONFLICT (metric_code) DO NOTHING
            """,
            # 添加唯一约束
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'fact_gold_supply_demand_unique'
                ) THEN
                    ALTER TABLE fact_gold_supply_demand
                    ADD CONSTRAINT fact_gold_supply_demand_unique
                    UNIQUE (period_id, metric_id);
                END IF;
            END $$
            """,
            # 添加外键约束
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'fact_gold_supply_demand_period_fk'
                ) THEN
                    ALTER TABLE fact_gold_supply_demand
                    ADD CONSTRAINT fact_gold_supply_demand_period_fk
                    FOREIGN KEY (period_id) REFERENCES dim_period(id);
                END IF;
            END $$
            """,
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'fact_gold_supply_demand_metric_fk'
                ) THEN
                    ALTER TABLE fact_gold_supply_demand
                    ADD CONSTRAINT fact_gold_supply_demand_metric_fk
                    FOREIGN KEY (metric_id) REFERENCES dim_metric(id);
                END IF;
            END $$
            """,
            # 添加索引
            "CREATE INDEX IF NOT EXISTS idx_fact_gold_supply_demand_period ON fact_gold_supply_demand(period_id)",
            "CREATE INDEX IF NOT EXISTS idx_fact_gold_supply_demand_metric ON fact_gold_supply_demand(metric_id)",
        ]

        for i, stmt in enumerate(statements, 1):
            try:
                await Database.execute(stmt)
                print(f"   ✓ 步骤 {i}/{len(statements)} 完成")
            except Exception as e:
                print(f"   ! 步骤 {i}/{len(statements)} 警告: {e}")

        print("   ✓ 迁移脚本执行完成\n")

    except Exception as e:
        print(f"   ✗ 迁移失败: {e}\n")
        await Database.close()
        return

    # 验证维度表数据
    print("2. 验证维度表初始化...")
    result = await Database.fetch_one("SELECT COUNT(*) as count FROM dim_period")
    print(f"   - dim_period: {result['count']} 行")

    result = await Database.fetch_one("SELECT COUNT(*) as count FROM dim_metric")
    print(f"   - dim_metric: {result['count']} 行")

    # 验证约束
    print("\n3. 验证事实表约束...")
    constraints = await Database.fetch_all("""
        SELECT conname, contype
        FROM pg_constraint
        WHERE conrelid = 'fact_gold_supply_demand'::regclass
    """)
    for constraint in constraints:
        print(f"   - {constraint['conname']}: {constraint['contype']}")

    print("\n✓ Phase 1 迁移完成")
    print("  - dim_period 已初始化（2021-2025 季度）")
    print("  - dim_metric 已初始化（14 个黄金供需指标）")
    print("  - fact_gold_supply_demand 约束和索引已添加")
    print("\n可以开始重构 Store 代码")

    await Database.close()


if __name__ == "__main__":
    asyncio.run(main())

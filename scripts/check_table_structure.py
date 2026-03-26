"""检查黄金供需相关表结构"""
import asyncio
from fcli.core.database import Database
from fcli.core.config import config


async def main():
    await Database.init(config)
    
    tables = [
        'gold_supply_demand',
        'fact_gold_supply_demand',
        'dim_metric',
        'dim_period'
    ]
    
    for table in tables:
        print(f"\n=== {table} 表结构 ===")
        try:
            columns = await Database.fetch_all(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """)
            if columns:
                for col in columns:
                    nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
                    print(f"  {col['column_name']}: {col['data_type']} ({nullable})")
            else:
                print("  表不存在或无列")
        except Exception as e:
            print(f"  ERROR: {e}")
    
    await Database.close()


if __name__ == "__main__":
    asyncio.run(main())

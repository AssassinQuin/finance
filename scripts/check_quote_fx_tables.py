"""检查 fact_quote 和 fact_fx_rate 表结构"""
import asyncio
from fcli.core.database import Database
from fcli.core.config import config


async def main():
    await Database.init(config)
    
    print("=== 检查 Quote/FX 相关表结构 ===\n")
    
    tables_to_check = [
        "fact_quote",
        "fact_fx_rate",
        "quotes",
        "exchange_rates",
    ]
    
    for table in tables_to_check:
        print(f"--- {table} ---")
        exists = await Database.fetch_one(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = $1
            )
        """, table)
        
        if exists and exists["exists"]:
            columns = await Database.fetch_all(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position
            """, table)
            
            count = await Database.fetch_one(f'SELECT COUNT(*) as cnt FROM {table}')
            
            print(f"  存在: Yes")
            print(f"  行数: {count['cnt']}")
            print(f"  列:")
            for col in columns:
                nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
                print(f"    - {col['column_name']}: {col['data_type']} {nullable}")
        else:
            print(f"  存在: No")
        print()
    
    await Database.close()


if __name__ == "__main__":
    asyncio.run(main())

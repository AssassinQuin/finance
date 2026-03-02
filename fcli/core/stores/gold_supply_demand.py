"""Gold supply/demand store for quarterly data persistence."""

from datetime import datetime
from typing import List, Optional

from ..models.gold_supply_demand import GoldSupplyDemand
from .base import BaseStore


class GoldSupplyDemandStore(BaseStore[GoldSupplyDemand]):
    """Store for gold quarterly supply/demand data."""

    table_name = "gold_supply_demand"
    model_class = GoldSupplyDemand
    pk_field = "id"

    @classmethod
    def _row_to_model(cls, row: dict) -> GoldSupplyDemand:
        """Convert database row to GoldSupplyDemand model."""
        return GoldSupplyDemand(
            id=row.get("id"),
            year=row["year"],
            quarter=row["quarter"],
            period=row.get("period", ""),
            mine_production=row.get("mine_production", 0.0),
            recycling=row.get("recycling", 0.0),
            net_hedging=row.get("net_hedging", 0.0),
            total_supply=row.get("total_supply", 0.0),
            jewelry=row.get("jewelry", 0.0),
            technology=row.get("technology", 0.0),
            total_investment=row.get("total_investment", 0.0),
            bars_coins=row.get("bars_coins", 0.0),
            etfs=row.get("etfs", 0.0),
            otc_investment=row.get("otc_investment", 0.0),
            central_banks=row.get("central_banks", 0.0),
            total_demand=row.get("total_demand", 0.0),
            supply_demand_balance=row.get("supply_demand_balance", 0.0),
            price_avg_usd=row.get("price_avg_usd"),
            data_source=row.get("data_source", ""),
            fetch_time=row.get("fetch_time"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    @classmethod
    async def save_quarterly(cls, data: GoldSupplyDemand) -> bool:
        """Save or update quarterly supply/demand data.

        Uses year+quarter as unique key for upsert.
        """
        if not cls._is_enabled():
            return False

        pool = cls._pool()
        if not pool:
            return False

        now = datetime.now()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""
                    INSERT INTO {cls.table_name} (
                        year, quarter, period,
                        mine_production, recycling, net_hedging, total_supply,
                        jewelry, technology, total_investment, bars_coins, etfs,
                        otc_investment, central_banks, total_demand,
                        supply_demand_balance, price_avg_usd,
                        data_source, fetch_time, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON DUPLICATE KEY UPDATE
                        period = VALUES(period),
                        mine_production = VALUES(mine_production),
                        recycling = VALUES(recycling),
                        net_hedging = VALUES(net_hedging),
                        total_supply = VALUES(total_supply),
                        jewelry = VALUES(jewelry),
                        technology = VALUES(technology),
                        total_investment = VALUES(total_investment),
                        bars_coins = VALUES(bars_coins),
                        etfs = VALUES(etfs),
                        otc_investment = VALUES(otc_investment),
                        central_banks = VALUES(central_banks),
                        total_demand = VALUES(total_demand),
                        supply_demand_balance = VALUES(supply_demand_balance),
                        price_avg_usd = VALUES(price_avg_usd),
                        data_source = VALUES(data_source),
                        fetch_time = VALUES(fetch_time),
                        updated_at = VALUES(updated_at)
                    """,
                    (
                        data.year,
                        data.quarter,
                        data.period,
                        data.mine_production,
                        data.recycling,
                        data.net_hedging,
                        data.total_supply,
                        data.jewelry,
                        data.technology,
                        data.total_investment,
                        data.bars_coins,
                        data.etfs,
                        data.otc_investment,
                        data.central_banks,
                        data.total_demand,
                        data.supply_demand_balance,
                        data.price_avg_usd,
                        data.data_source,
                        data.fetch_time,
                        now,
                        now,
                    ),
                )
                return True

    @classmethod
    async def get_by_quarter(cls, year: int, quarter: int) -> Optional[GoldSupplyDemand]:
        """Get supply/demand data for a specific quarter."""
        if not cls._is_enabled():
            return None

        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT * FROM {cls.table_name} WHERE year = %s AND quarter = %s",
                    (year, quarter),
                )
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return cls._row_to_model(dict(zip(columns, row)))
                return None

    @classmethod
    async def get_latest(cls) -> Optional[GoldSupplyDemand]:
        """Get the most recent quarter's data."""
        if not cls._is_enabled():
            return None

        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"SELECT * FROM {cls.table_name} ORDER BY year DESC, quarter DESC LIMIT 1")
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return cls._row_to_model(dict(zip(columns, row)))
                return None

    @classmethod
    async def get_history(cls, limit: int = 8) -> List[GoldSupplyDemand]:
        """Get historical supply/demand data (last N quarters)."""
        if not cls._is_enabled():
            return []

        pool = cls._pool()
        if not pool:
            return []

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT * FROM {cls.table_name} ORDER BY year DESC, quarter DESC LIMIT %s",
                    (limit,),
                )
                rows = await cursor.fetchall()
                if rows:
                    columns = [desc[0] for desc in cursor.description]
                    return [cls._row_to_model(dict(zip(columns, row))) for row in rows]
                return []

"""Gold supply/demand store for quarterly data persistence using fact table model."""

from datetime import datetime

from ..models.gold_supply_demand import GoldSupplyDemand
from .base import BaseStore


class GoldSupplyDemandStore(BaseStore[GoldSupplyDemand]):
    """Store for gold quarterly supply/demand data using V2 fact table."""

    table_name = "fact_gold_supply_demand"
    model_class = GoldSupplyDemand
    pk_field = "id"

    METRIC_MAPPING = {
        "mine_production": "mine_production",
        "recycling": "recycling",
        "net_hedging": "net_hedging",
        "total_supply": "total_supply",
        "jewelry": "jewelry",
        "technology": "technology",
        "total_investment": "total_investment",
        "bars_coins": "bars_coins",
        "etfs": "etfs",
        "otc_investment": "otc_investment",
        "central_banks": "central_banks",
        "total_demand": "total_demand",
        "supply_demand_balance": "supply_demand_balance",
        "price_avg_usd": "price_avg_usd",
    }

    @classmethod
    def _row_to_model(cls, row: dict) -> GoldSupplyDemand:
        """Convert aggregated fact rows to GoldSupplyDemand model."""
        return GoldSupplyDemand(
            id=row.get("id"),
            year=row.get("year", 0),
            quarter=row.get("quarter", 0),
            period=row.get("period_label", ""),
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
            data_source=row.get("source_name", ""),
            fetch_time=row.get("fetch_time"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    @classmethod
    async def _get_period_id(cls, year: int, quarter: int) -> int | None:
        """Get period_id from dim_period."""
        if not cls._is_enabled():
            return None
        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM dim_period WHERE year = $1 AND quarter = $2",
                year,
                quarter,
            )
            return row["id"] if row else None

    @classmethod
    async def _get_metric_id(cls, metric_code: str) -> int | None:
        """Get metric_id from dim_metric."""
        if not cls._is_enabled():
            return None
        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM dim_metric WHERE metric_code = $1",
                metric_code,
            )
            return row["id"] if row else None

    @classmethod
    async def save_quarterly(cls, data: GoldSupplyDemand) -> bool:
        """Save or update quarterly supply/demand data.

        Stores each metric as a separate row in fact_gold_supply_demand.
        Uses period_id + metric_id as unique key for upsert.
        """
        if not cls._is_enabled():
            return False

        pool = cls._pool()
        if not pool:
            return False

        period_id = await cls._get_period_id(data.year, data.quarter)
        if not period_id:
            return False

        now = datetime.now()

        metrics = [
            ("mine_production", data.mine_production),
            ("recycling", data.recycling),
            ("net_hedging", data.net_hedging),
            ("total_supply", data.total_supply),
            ("jewelry", data.jewelry),
            ("technology", data.technology),
            ("total_investment", data.total_investment),
            ("bars_coins", data.bars_coins),
            ("etfs", data.etfs),
            ("otc_investment", data.otc_investment),
            ("central_banks", data.central_banks),
            ("total_demand", data.total_demand),
            ("supply_demand_balance", data.supply_demand_balance),
            ("price_avg_usd", data.price_avg_usd),
        ]

        async with pool.acquire() as conn:
            for metric_code, value in metrics:
                metric_id = await cls._get_metric_id(metric_code)
                if not metric_id:
                    continue

                await conn.execute(
                    """
                    INSERT INTO fact_gold_supply_demand (
                        period_id, metric_id, value, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (period_id, metric_id) DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = EXCLUDED.updated_at
                    """,
                    period_id,
                    metric_id,
                    value,
                    now,
                    now,
                )
            return True

    @classmethod
    async def get_by_quarter(cls, year: int, quarter: int) -> GoldSupplyDemand | None:
        """Get supply/demand data for a specific quarter."""
        if not cls._is_enabled():
            return None

        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    p.year, p.quarter, p.period_label,
                    m.metric_code,
                    f.value,
                    f.created_at,
                    f.updated_at
                FROM fact_gold_supply_demand f
                JOIN dim_period p ON f.period_id = p.id
                JOIN dim_metric m ON f.metric_id = m.id
                WHERE p.year = $1 AND p.quarter = $2
                """,
                year,
                quarter,
            )

            if not rows:
                return None

            aggregated = {
                "year": year,
                "quarter": quarter,
                "period_label": rows[0]["period_label"],
                "created_at": rows[0]["created_at"],
                "updated_at": rows[0]["updated_at"],
            }

            for row in rows:
                metric_code = row["metric_code"]
                if metric_code in cls.METRIC_MAPPING:
                    aggregated[metric_code] = row["value"]

            return cls._row_to_model(aggregated)

    @classmethod
    async def get_latest(cls) -> GoldSupplyDemand | None:
        """Get the most recent quarter's data."""
        if not cls._is_enabled():
            return None

        pool = cls._pool()
        if not pool:
            return None

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT p.year, p.quarter
                FROM fact_gold_supply_demand f
                JOIN dim_period p ON f.period_id = p.id
                ORDER BY p.year DESC, p.quarter DESC
                LIMIT 1
                """
            )

            if not row:
                return None

            return await cls.get_by_quarter(row["year"], row["quarter"])

    @classmethod
    async def get_history(cls, limit: int = 8) -> list[GoldSupplyDemand]:
        """Get historical supply/demand data (last N quarters)."""
        if not cls._is_enabled():
            return []

        pool = cls._pool()
        if not pool:
            return []

        async with pool.acquire() as conn:
            periods = await conn.fetch(
                """
                SELECT DISTINCT p.year, p.quarter
                FROM fact_gold_supply_demand f
                JOIN dim_period p ON f.period_id = p.id
                ORDER BY p.year DESC, p.quarter DESC
                LIMIT $1
                """,
                limit,
            )

            results = []
            for period in periods:
                data = await cls.get_by_quarter(period["year"], period["quarter"])
                if data:
                    results.append(data)

            return results

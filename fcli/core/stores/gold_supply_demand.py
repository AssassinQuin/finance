"""Gold supply/demand store for quarterly data using wide table schema.

V3: One row per period with all metrics as columns.
Replaces EAV pattern (period_id + metric_id + value) for simplicity and performance.
"""

from datetime import datetime

from ..database import Database
from ..models.gold_supply_demand import GoldSupplyDemand


class GoldSupplyDemandStore:
    """Store for gold quarterly supply/demand data using wide table."""

    @classmethod
    async def _get_or_create_period(cls, year: int, quarter: int) -> int | None:
        """Get or create a period_id in dim_period."""
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            "SELECT id FROM dim_period WHERE year = $1 AND quarter = $2",
            year,
            quarter,
        )
        if row:
            return row["id"]

        period_label = f"{year} Q{quarter}"
        result = await Database.fetch_one(
            """
            INSERT INTO dim_period (year, quarter, period_label)
            VALUES ($1, $2, $3)
            ON CONFLICT (year, quarter) DO UPDATE SET period_label = EXCLUDED.period_label
            RETURNING id
            """,
            year,
            quarter,
            period_label,
        )
        return result["id"] if result else None

    @classmethod
    async def _get_or_create_source(cls, source_name: str) -> int | None:
        """Get or create source_id in dim_data_source."""
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            "SELECT id FROM dim_data_source WHERE source_name = $1",
            source_name,
        )
        if row:
            return row["id"]

        result = await Database.fetch_one(
            """
            INSERT INTO dim_data_source (source_name)
            VALUES ($1)
            ON CONFLICT (source_name) DO NOTHING
            RETURNING id
            """,
            source_name,
        )
        if result:
            return result["id"]

        row = await Database.fetch_one(
            "SELECT id FROM dim_data_source WHERE source_name = $1",
            source_name,
        )
        return row["id"] if row else None

    @classmethod
    async def save_quarterly(cls, data: GoldSupplyDemand) -> bool:
        """Save or update quarterly supply/demand data.

        Single INSERT with all metrics as columns — no EAV, no N+1.
        """
        if not Database.is_enabled():
            return False

        period_id = await cls._get_or_create_period(data.year, data.quarter)
        if not period_id:
            return False

        source_id = await cls._get_or_create_source(data.data_source or "WGC")

        try:
            await Database.execute(
                """
                INSERT INTO fact_gold_supply_demand (
                    period_id,
                    mine_production, recycling, net_hedging, total_supply,
                    jewelry, technology, total_investment, bars_coins, etfs,
                    otc_investment, central_banks, total_demand,
                    supply_demand_balance, price_avg_usd,
                    source_id, created_at, updated_at
                ) VALUES (
                    $1,
                    $2, $3, $4, $5,
                    $6, $7, $8, $9, $10,
                    $11, $12, $13,
                    $14, $15,
                    $16, NOW(), NOW()
                )
                ON CONFLICT (period_id) DO UPDATE SET
                    mine_production = EXCLUDED.mine_production,
                    recycling = EXCLUDED.recycling,
                    net_hedging = EXCLUDED.net_hedging,
                    total_supply = EXCLUDED.total_supply,
                    jewelry = EXCLUDED.jewelry,
                    technology = EXCLUDED.technology,
                    total_investment = EXCLUDED.total_investment,
                    bars_coins = EXCLUDED.bars_coins,
                    etfs = EXCLUDED.etfs,
                    otc_investment = EXCLUDED.otc_investment,
                    central_banks = EXCLUDED.central_banks,
                    total_demand = EXCLUDED.total_demand,
                    supply_demand_balance = EXCLUDED.supply_demand_balance,
                    price_avg_usd = EXCLUDED.price_avg_usd,
                    source_id = EXCLUDED.source_id,
                    updated_at = NOW()
                """,
                period_id,
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
                source_id,
            )
            return True
        except Exception:
            return False

    @classmethod
    async def get_by_quarter(cls, year: int, quarter: int) -> GoldSupplyDemand | None:
        """Get supply/demand data for a specific quarter."""
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            """
            SELECT
                f.id,
                p.year, p.quarter, p.period_label,
                f.mine_production, f.recycling, f.net_hedging, f.total_supply,
                f.jewelry, f.technology, f.total_investment,
                f.bars_coins, f.etfs, f.otc_investment,
                f.central_banks, f.total_demand,
                f.supply_demand_balance, f.price_avg_usd,
                ds.source_name,
                f.created_at, f.updated_at
            FROM fact_gold_supply_demand f
            JOIN dim_period p ON f.period_id = p.id
            LEFT JOIN dim_data_source ds ON f.source_id = ds.id
            WHERE p.year = $1 AND p.quarter = $2
            """,
            year,
            quarter,
        )

        if not row:
            return None

        return cls._row_to_model(row)

    @classmethod
    async def get_latest(cls) -> GoldSupplyDemand | None:
        """Get the most recent quarter's data."""
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            """
            SELECT
                f.id,
                p.year, p.quarter, p.period_label,
                f.mine_production, f.recycling, f.net_hedging, f.total_supply,
                f.jewelry, f.technology, f.total_investment,
                f.bars_coins, f.etfs, f.otc_investment,
                f.central_banks, f.total_demand,
                f.supply_demand_balance, f.price_avg_usd,
                ds.source_name,
                f.created_at, f.updated_at
            FROM fact_gold_supply_demand f
            JOIN dim_period p ON f.period_id = p.id
            LEFT JOIN dim_data_source ds ON f.source_id = ds.id
            ORDER BY p.year DESC, p.quarter DESC
            LIMIT 1
            """
        )

        if not row:
            return None

        return cls._row_to_model(row)

    @classmethod
    async def get_history(cls, limit: int = 8) -> list[GoldSupplyDemand]:
        """Get historical supply/demand data (last N quarters).

        Single query — no N+1 round trips.
        """
        if not Database.is_enabled():
            return []

        rows = await Database.fetch_all(
            """
            SELECT
                f.id,
                p.year, p.quarter, p.period_label,
                f.mine_production, f.recycling, f.net_hedging, f.total_supply,
                f.jewelry, f.technology, f.total_investment,
                f.bars_coins, f.etfs, f.otc_investment,
                f.central_banks, f.total_demand,
                f.supply_demand_balance, f.price_avg_usd,
                ds.source_name,
                f.created_at, f.updated_at
            FROM fact_gold_supply_demand f
            JOIN dim_period p ON f.period_id = p.id
            LEFT JOIN dim_data_source ds ON f.source_id = ds.id
            ORDER BY p.year DESC, p.quarter DESC
            LIMIT $1
            """,
            limit,
        )

        return [cls._row_to_model(row) for row in rows]

    @classmethod
    def _row_to_model(cls, row) -> GoldSupplyDemand:
        """Convert database row to GoldSupplyDemand model."""
        return GoldSupplyDemand(
            id=row.get("id"),
            year=row.get("year", 0),
            quarter=row.get("quarter", 0),
            period=row.get("period_label", ""),
            mine_production=float(row["mine_production"]) if row.get("mine_production") else None,
            recycling=float(row["recycling"]) if row.get("recycling") else None,
            net_hedging=float(row["net_hedging"]) if row.get("net_hedging") else None,
            total_supply=float(row["total_supply"]) if row.get("total_supply") else None,
            jewelry=float(row["jewelry"]) if row.get("jewelry") else None,
            technology=float(row["technology"]) if row.get("technology") else None,
            total_investment=float(row["total_investment"]) if row.get("total_investment") else None,
            bars_coins=float(row["bars_coins"]) if row.get("bars_coins") else None,
            etfs=float(row["etfs"]) if row.get("etfs") else None,
            otc_investment=float(row["otc_investment"]) if row.get("otc_investment") else None,
            central_banks=float(row["central_banks"]) if row.get("central_banks") else None,
            total_demand=float(row["total_demand"]) if row.get("total_demand") else None,
            supply_demand_balance=float(row["supply_demand_balance"]) if row.get("supply_demand_balance") else None,
            price_avg_usd=float(row["price_avg_usd"]) if row.get("price_avg_usd") else None,
            data_source=row.get("source_name") or "WGC",
            fetch_time=row.get("updated_at"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

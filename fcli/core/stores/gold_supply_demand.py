"""Gold supply/demand store for quarterly data using flat table.

Single table with all metrics as columns — no dimension joins needed.
"""

from ..database import Database
from ..models.gold_supply_demand import GoldSupplyDemand
from ...utils.logger import get_logger

_logger = get_logger("fcli.stores.gold_supply_demand")


class GoldSupplyDemandStore:
    """Store for gold quarterly supply/demand data using flat table."""

    async def save_quarterly(self, data: GoldSupplyDemand) -> bool:
        if not Database.is_enabled():
            return False

        try:
            await Database.execute(
                """
                INSERT INTO gold_supply_demand (
                    year, quarter,
                    mine_production, recycling, net_hedging, total_supply,
                    jewelry, technology, total_investment, bars_coins, etfs,
                    otc_investment, central_banks, total_demand,
                    supply_demand_balance, price_avg_usd,
                    data_source, created_at, updated_at
                ) VALUES (
                    $1, $2,
                    $3, $4, $5, $6,
                    $7, $8, $9, $10, $11,
                    $12, $13, $14,
                    $15, $16,
                    $17, NOW(), NOW()
                )
                ON CONFLICT (year, quarter) DO UPDATE SET
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
                    data_source = EXCLUDED.data_source,
                    updated_at = NOW()
                """,
                data.year,
                data.quarter,
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
                data.data_source or "WGC",
            )
            return True
        except Exception as e:
            _logger.error(f"Failed to save gold supply/demand {data.year}Q{data.quarter}: {e}")
            return False

    async def get_by_quarter(self, year: int, quarter: int) -> GoldSupplyDemand | None:
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            """
            SELECT *
            FROM gold_supply_demand
            WHERE year = $1 AND quarter = $2
            """,
            year,
            quarter,
        )

        if not row:
            return None

        return self._row_to_model(row)

    async def get_latest(self) -> GoldSupplyDemand | None:
        if not Database.is_enabled():
            return None

        row = await Database.fetch_one(
            """
            SELECT *
            FROM gold_supply_demand
            ORDER BY year DESC, quarter DESC
            LIMIT 1
            """
        )

        if not row:
            return None

        return self._row_to_model(row)

    async def get_history(self, limit: int = 8) -> list[GoldSupplyDemand]:
        if not Database.is_enabled():
            return []

        rows = await Database.fetch_all(
            """
            SELECT *
            FROM gold_supply_demand
            ORDER BY year DESC, quarter DESC
            LIMIT $1
            """,
            limit,
        )

        return [self._row_to_model(row) for row in rows]

    def _row_to_model(self, row) -> GoldSupplyDemand:
        year = row.get("year", 0)
        quarter = row.get("quarter", 0)
        return GoldSupplyDemand(
            id=row.get("id"),
            year=year,
            quarter=quarter,
            period=f"{year} Q{quarter}",
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
            data_source=row.get("data_source") or "WGC",
            fetch_time=row.get("updated_at"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )


gold_supply_demand_store = GoldSupplyDemandStore()

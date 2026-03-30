"""Fund store for database operations."""

import json
import logging
from datetime import date

from ..database import Database
from ..models import Fund, FundScale, FundType, InvestType
from ..models.base import Market
from .base import BaseStore

logger = logging.getLogger(__name__)


class FundStore(BaseStore[Fund]):
    """Store for fund data operations."""

    table_name = "dim_fund"
    pk_field = "fund_code"
    model_class = Fund

    @classmethod
    async def _ensure_initialized(cls) -> bool:
        return await Database._ensure_initialized()

    @classmethod
    async def save(cls, fund: Fund) -> bool:
        if not await cls._ensure_initialized():
            return False

        pool = cls._pool()
        if not pool:
            return False

        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO dim_fund (
                        fund_code, fund_name, fund_name_short, fund_type, market,
                        invest_type, management_fee, custody_fee,
                        fund_company, tracking_index, inception_date, listing_date,
                        is_active, extra
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    ON CONFLICT (fund_code) DO UPDATE SET
                        fund_name = EXCLUDED.fund_name,
                        fund_name_short = EXCLUDED.fund_name_short,
                        fund_type = EXCLUDED.fund_type,
                        market = EXCLUDED.market,
                        invest_type = EXCLUDED.invest_type,
                        management_fee = EXCLUDED.management_fee,
                        custody_fee = EXCLUDED.custody_fee,
                        fund_company = EXCLUDED.fund_company,
                        tracking_index = EXCLUDED.tracking_index,
                        inception_date = EXCLUDED.inception_date,
                        listing_date = EXCLUDED.listing_date,
                        is_active = EXCLUDED.is_active,
                        extra = EXCLUDED.extra
                    """,
                    fund.code,
                    fund.name,
                    fund.name_short,
                    fund.fund_type.value,
                    fund.market.value,
                    fund.invest_type.value if fund.invest_type else None,
                    fund.management_fee,
                    fund.custody_fee,
                    fund.fund_company,
                    fund.tracking_index,
                    fund.inception_date,
                    fund.listing_date,
                    fund.is_active,
                    fund.extra,
                )
                return True
        except Exception as e:
            logger.error(f"Failed to save fund {fund.code}: {e}")
            return False

    @classmethod
    async def save_batch(cls, funds: list[Fund]) -> int:
        if not await cls._ensure_initialized():
            return 0

        saved_count = 0
        for fund in funds:
            if await cls.save(fund):
                saved_count += 1
        return saved_count

    @classmethod
    async def save_scale(cls, scale: FundScale) -> bool:
        if not await cls._ensure_initialized():
            return False

        pool = cls._pool()
        if not pool:
            return False

        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO fact_fund_scale (
                        fund_id, report_date, scale, share, nav, fetched_at
                    ) SELECT id, $2, $3, $4, $5, $6 FROM dim_fund WHERE fund_code = $1
                    ON CONFLICT (fund_id, report_date) DO UPDATE SET
                        scale = EXCLUDED.scale,
                        share = EXCLUDED.share,
                        nav = EXCLUDED.nav,
                        fetched_at = EXCLUDED.fetched_at
                    """,
                    scale.fund_code,
                    scale.report_date,
                    scale.scale,
                    scale.share,
                    scale.nav,
                    scale.fetched_at,
                )
                return True
        except Exception as e:
            logger.error(f"Failed to save fund scale {scale.fund_code}: {e}")
            return False

    @classmethod
    async def get_by_code(cls, code: str) -> Fund | None:
        if not await cls._ensure_initialized():
            return None

        pool = cls._pool()
        if not pool:
            return None

        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT fund_code, fund_name, fund_name_short, fund_type, market,
                           invest_type, management_fee, custody_fee,
                           fund_company, tracking_index, inception_date, listing_date,
                           is_active, extra
                    FROM dim_fund
                    WHERE fund_code = $1
                    """,
                    code,
                )
                if not row:
                    return None
                return cls._row_to_model(dict(row))
        except Exception as e:
            logger.error(f"Failed to get fund {code}: {e}")
            return None

    @classmethod
    async def search(
        cls,
        query: str,
        fund_type: FundType | None = None,
        limit: int = 20,
    ) -> list[Fund]:
        if not await cls._ensure_initialized():
            return []

        pool = cls._pool()
        if not pool:
            return []

        try:
            async with pool.acquire() as conn:
                # Set lower similarity threshold for better fuzzy matching
                await conn.execute("SELECT set_limit(0.2)")

                sql = """
                    SELECT fund_code, fund_name, fund_name_short, fund_type, market,
                           invest_type, management_fee, custody_fee,
                           fund_company, tracking_index, inception_date, listing_date,
                           is_active, extra
                    FROM dim_fund
                    WHERE fund_code % $1
                       OR fund_name % $1
                       OR COALESCE(fund_name_short, fund_name) % $1
                """
                params: list[str | int | str] = [query]

                if fund_type:
                    sql += " AND fund_type = $2"
                    params.append(fund_type.value)

                sql += (
                    """ ORDER BY GREATEST(
                    similarity(fund_code, $1),
                    similarity(fund_name, $1),
                    similarity(COALESCE(fund_name_short, fund_name), $1)
                ) DESC LIMIT $2"""
                    if not fund_type
                    else """ ORDER BY GREATEST(
                    similarity(fund_code, $1),
                    similarity(fund_name, $1),
                    similarity(COALESCE(fund_name_short, fund_name), $1)
                ) DESC LIMIT $3"""
                )
                params.append(limit)

                rows = await conn.fetch(sql, *params)
                return [cls._row_to_model(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to search funds: {e}")
            return []

    @classmethod
    async def get_stale_funds(cls, days: int = 30) -> list[str]:
        if not await cls._ensure_initialized():
            return []

        pool = cls._pool()
        if not pool:
            return []

        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT f.fund_code
                    FROM dim_fund f
                    LEFT JOIN fact_fund_scale s ON f.id = s.fund_id
                    WHERE s.fetched_at < NOW() - INTERVAL '1 day' * $1::interval
                       OR s.fetched_at IS NULL
                    """,
                    days,
                )
                return [row["fund_code"] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get stale funds: {e}")
            return []

    @classmethod
    async def get_scale_history(cls, code: str, limit: int = 12) -> list[FundScale]:
        if not await cls._ensure_initialized():
            return []

        pool = cls._pool()
        if not pool:
            return []

        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT f.fund_code, s.report_date, s.scale, s.share, s.nav, s.fetched_at
                    FROM fact_fund_scale s
                    JOIN dim_fund f ON s.fund_id = f.id
                    WHERE f.fund_code = $1
                    ORDER BY s.report_date DESC
                    LIMIT $2
                    """,
                    code,
                    limit,
                )
                return [
                    FundScale(
                        fund_code=row["fund_code"],
                        report_date=row["report_date"],
                        scale=row["scale"],
                        share=row["share"],
                        nav=row["nav"],
                        fetched_at=row["fetched_at"],
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get scale history for {code}: {e}")
            return []

    @classmethod
    def _row_to_model(cls, row: dict) -> Fund:
        extra_raw = row.get("extra")
        if isinstance(extra_raw, str):
            extra = json.loads(extra_raw) if extra_raw else {}
        else:
            extra = extra_raw or {}

        invest_type_raw = row.get("invest_type")
        invest_type = InvestType(invest_type_raw) if invest_type_raw else None

        return Fund(
            code=row["fund_code"],
            name=row["fund_name"],
            name_short=row.get("fund_name_short"),
            fund_type=FundType(row["fund_type"]),
            market=Market(row["market"]),
            invest_type=invest_type,
            management_fee=float(row["management_fee"]) if row.get("management_fee") else None,
            custody_fee=float(row["custody_fee"]) if row.get("custody_fee") else None,
            fund_company=row.get("fund_company"),
            tracking_index=row.get("tracking_index"),
            inception_date=row.get("inception_date"),
            listing_date=row.get("listing_date"),
            is_active=row.get("is_active", True),
            extra=extra,
        )

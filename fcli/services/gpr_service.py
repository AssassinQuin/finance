"""
GPR (地缘政治风险指数) 服务模块
"""

from datetime import date, datetime, timedelta, timezone

from dateutil.relativedelta import relativedelta

from ..core.config import Settings
from ..core.config import config as _config
from ..core.database import Database
from ..core.models import GPRHistory
from ..core.stores.gpr import gpr_history_store
from ..utils.logger import get_logger
from .scrapers.gpr_scraper import GPRScraper

logger = get_logger("fcli.gpr")


class GPRService:
    def __init__(
        self,
        settings: Settings | None = None,
        gpr_scraper: GPRScraper | None = None,
    ):
        self._config = settings or _config
        self._gpr_scraper = gpr_scraper or GPRScraper()

    async def _check_and_update_stale_data(self) -> None:
        if not Database.is_enabled():
            return

        await gpr_history_store.ensure_schema()

        last_update = await gpr_history_store.get_last_update_time()
        now = datetime.now(timezone.utc)

        if last_update is not None:
            if last_update.tzinfo is None:
                last_update = last_update.replace(tzinfo=timezone.utc)
            if now - last_update < timedelta(days=7):
                return

        logger.info("GPR data cache expired (7 days), triggering auto-update...")
        result = await self.update_data(full=True)
        if result.get("success"):
            logger.info(f"Auto-updated GPR data: {result.get('records', 0)} records")
        else:
            logger.warning(f"Auto-update failed: {result.get('error', 'Unknown error')}")

    async def _load_from_db(
        self,
        country_code: str = "WLD",
        index_type: str = "GPR",
    ) -> dict[str, float]:
        if not Database.is_enabled():
            logger.warning("Database not available for GPR data.")
            return {}
        records = await gpr_history_store.get_history(
            country_code=country_code,
            index_type=index_type,
            months=600,
        )
        return {f"{r.report_date.year}-{r.report_date.month:02d}": r.gpr_index for r in records}

    async def get_gpr_history(
        self,
        months: int = 12,
        country_code: str = "WLD",
        index_type: str = "GPR",
    ) -> list[dict]:
        await self._check_and_update_stale_data()

        records = await gpr_history_store.get_history(
            country_code=country_code,
            index_type=index_type,
            months=months,
        )
        return [
            {
                "date": f"{r.report_date.year}-{r.report_date.month:02d}",
                "value": r.gpr_index,
            }
            for r in reversed(records)
        ]

    async def get_gpr_analysis(
        self,
        country_code: str = "WLD",
        index_type: str = "GPR",
    ) -> dict:
        await self._check_and_update_stale_data()

        data = await self._load_from_db(
            country_code=country_code,
            index_type=index_type,
        )
        dates = sorted(data.keys(), reverse=True)
        if not dates:
            return {}

        latest_date_str = dates[0]
        latest_val = data[latest_date_str]

        latest_year, latest_month = map(int, latest_date_str.split("-"))
        latest_report_date = date(latest_year, latest_month, 1)

        def get_val_at_offset(months: int) -> float | None:
            try:
                target_date = latest_report_date - relativedelta(months=months)
                target_key = f"{target_date.year}-{target_date.month:02d}"

                if target_key in data:
                    return data[target_key]

                for d in dates:
                    d_date_parts = d.split("-")
                    d_date = date(int(d_date_parts[0]), int(d_date_parts[1]), 1)
                    if d_date <= target_date:
                        return data[d]
                return None
            except Exception:
                return None

        analysis = {
            "latest": {"date": latest_date_str, "value": latest_val},
            "country_code": country_code,
            "index_type": index_type,
            "horizons": {},
        }

        horizons = {"1M": 1, "3M": 3, "6M": 6, "1Y": 12, "5Y": 60, "10Y": 120}

        for label, months in horizons.items():
            prev_val = get_val_at_offset(months)
            if prev_val is not None:
                change = latest_val - prev_val
                analysis["horizons"][label] = {
                    "value": prev_val,
                    "change": change,
                    "change_pct": (change / prev_val) * 100 if prev_val != 0 else 0,
                }
            else:
                analysis["horizons"][label] = None

        values = list(data.values())
        if values:
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            analysis["stats"] = {
                "mean": round(sum(sorted_vals) / n, 2),
                "median": round(sorted_vals[n // 2], 2),
                "min": round(sorted_vals[0], 2),
                "max": round(sorted_vals[-1], 2),
                "percentile_75": round(sorted_vals[int(n * 0.75)], 2),
            }

        risk_level = "正常 (Normal)"
        risk_color = "white"
        if latest_val > 250:
            risk_level = "极高 (Extreme)"
            risk_color = "bold red"
        elif latest_val > 150:
            risk_level = "高风险 (Elevated)"
            risk_color = "red"
        elif latest_val > 100:
            risk_level = "中等 (Moderate)"
            risk_color = "yellow"

        analysis["risk"] = {"level": risk_level, "color": risk_color}

        return analysis

    async def get_multi_country_comparison(
        self,
        country_codes: list[str],
    ) -> list[dict]:
        if not country_codes:
            return []

        await self._check_and_update_stale_data()

        records = await gpr_history_store.get_multi_country_latest(
            country_codes=country_codes,
        )

        results = []
        for r in records:
            results.append(
                {
                    "country_code": r.country_code,
                    "country_name": r.country_name,
                    "report_date": f"{r.report_date.year}-{r.report_date.month:02d}",
                    "gpr_index": r.gpr_index,
                }
            )

        results.sort(key=lambda x: x["gpr_index"], reverse=True)
        return results

    async def update_data(self, full: bool = False) -> dict:
        try:
            logger.info("Starting GPR data update...")

            await gpr_history_store.ensure_schema()

            scraper = self._gpr_scraper
            async with scraper:
                if full:
                    raw_data = await scraper.fetch_full_data(include_countries=True)
                else:
                    raw_data = await scraper.fetch_gpr_data()
                    raw_data = [
                        {"period": k, "country_code": "WLD", "index_type": "GPR", "value": v}
                        for k, v in raw_data.items()
                    ]

            logger.info(f"Fetched {len(raw_data)} GPR data points from remote")

            if not raw_data:
                return {"success": False, "error": "No data fetched from remote source"}

            records = []
            for item in raw_data:
                try:
                    period = item["period"]
                    year, month = map(int, period.split("-"))
                    report_date = date(year, month, 1)

                    record = GPRHistory(
                        country_code=item.get("country_code", "WLD"),
                        report_date=report_date,
                        gpr_index=item["value"],
                        index_type=item.get("index_type", "GPR"),
                        data_source="Caldara-Iacoviello",
                    )
                    records.append(record)
                except Exception as e:
                    logger.debug(f"Skipping item {item}: {e}")
                    continue

            if not records:
                return {"success": False, "error": "No valid records to save"}

            saved_count = await gpr_history_store.save_batch(records)
            logger.info(f"Saved {saved_count} records to database")

            return {
                "success": True,
                "records": saved_count,
                "total_fetched": len(raw_data),
            }

        except Exception as e:
            logger.error(f"GPR data update failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

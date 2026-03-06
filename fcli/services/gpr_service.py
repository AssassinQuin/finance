"""
GPR (地缘政治风险指数) 服务模块
"""

import json
import logging
from datetime import date

from dateutil.relativedelta import relativedelta

from ..core.config import settings
from ..core.database import Database
from ..core.models import GPRHistory
from ..core.stores import GPRHistoryStore
from .scrapers.gpr_scraper import GPRScraper

logger = logging.getLogger(__name__)


class GPRService:
    def __init__(self):
        self.storage_file = settings.data_dir / "gpr_history.json"
        self._ensure_storage()

    def _ensure_storage(self):
        if not settings.data_dir.exists():
            settings.data_dir.mkdir(parents=True)

    async def _check_and_update_stale_data(self) -> None:
        if not Database.is_enabled():
            return

        today = date.today()
        last_month = today - relativedelta(months=1)
        target_date = date(last_month.year, last_month.month, 1)

        latest_date = await GPRHistoryStore.get_latest_date()

        if latest_date is None or latest_date < target_date:
            logger.info("GPR data is stale, triggering auto-update...")
            result = await self.update_data()
            if result.get("success"):
                logger.info(f"Auto-updated GPR data: {result.get('records', 0)} records")
            else:
                logger.warning(f"Auto-update failed: {result.get('error', 'Unknown error')}")

    def load_data(self) -> dict[str, float]:
        if not self.storage_file.exists():
            logger.warning("No GPR data file found. Run 'fcli gpr --update' to fetch data.")
            return {}
        with open(self.storage_file, encoding="utf-8") as f:
            return json.load(f)

    async def get_gpr_history(self, months: int = 12) -> list[dict]:
        await self._check_and_update_stale_data()

        data = self.load_data()
        sorted_dates = sorted(data.keys())

        history = []
        for d in sorted_dates:
            history.append({"date": d, "value": data[d]})

        return history[-months:]

    async def get_gpr_analysis(self) -> dict:
        await self._check_and_update_stale_data()

        data = self.load_data()
        dates = sorted(data.keys(), reverse=True)
        if not dates:
            return {}

        latest_date = dates[0]
        latest_val = data[latest_date]

        def get_val_at_offset(months: int) -> float | None:
            try:
                ly, lm = map(int, latest_date.split("-"))
                target_m = lm - months
                target_y = ly
                while target_m <= 0:
                    target_m += 12
                    target_y -= 1
                target_date = f"{target_y}-{target_m:02d}"

                if target_date in data:
                    return data[target_date]

                for d in dates:
                    if d <= target_date:
                        return data[d]
                return None
            except Exception:
                return None

        analysis = {"latest": {"date": latest_date, "value": latest_val}, "horizons": {}}

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

    async def update_data(self) -> dict:
        try:
            logger.info("Starting GPR data update...")

            async with GPRScraper() as scraper:
                raw_data = await scraper.fetch_gpr_data()
                logger.info(f"Fetched {len(raw_data)} GPR data points from remote")

            if not raw_data:
                return {"success": False, "error": "No data fetched from remote source"}

            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Updated local JSON file: {self.storage_file}")

            records = []
            for period, gpr_value in raw_data.items():
                try:
                    year, month = map(int, period.split("-"))
                    report_date = date(year, month, 1)

                    record = GPRHistory(
                        country_code="WLD",
                        report_date=report_date,
                        gpr_index=gpr_value,
                        data_source="Caldara-Iacoviello",
                    )
                    records.append(record)
                except Exception as e:
                    logger.debug(f"Skipping period {period}: {e}")
                    continue

            if not records:
                return {"success": False, "error": "No valid records to save"}

            saved_count = await GPRHistoryStore.save_batch(records)
            logger.info(f"Saved {saved_count} records to database")

            return {
                "success": True,
                "records": saved_count,
                "total_fetched": len(raw_data),
            }

        except Exception as e:
            logger.error(f"GPR data update failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


gpr_service = GPRService()

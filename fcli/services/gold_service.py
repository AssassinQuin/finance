import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from ..core.config import config
from ..sources.gold import gold_source


class GoldService:
    def __init__(self):
        self.storage_file = config.data_dir / "gold_stats.json"
        self._ensure_storage()

    def _ensure_storage(self):
        if not config.data_dir.exists():
            config.data_dir.mkdir(parents=True)
        if not self.storage_file.exists():
            with open(self.storage_file, "w") as f:
                json.dump({"reserves": [], "balance": {}}, f)

    async def update_gold_data(self):
        """
        Fetch latest gold reserves and global supply/demand.
        """
        major_countries = ["US", "DE", "IT", "FR", "RU", "CN", "CH", "JP", "IN"]

        # 1. Fetch IMF Reserves
        reserves_data = await gold_source.fetch_imf_reserves(major_countries)

        # 2. Fetch Global Balance
        balance_data = await gold_source.fetch_global_supply_demand()

        # 3. Save to local storage (incremental update)
        self._save_data(reserves_data, balance_data)

        return len(reserves_data)

    def _save_data(self, reserves: List[Dict], balance: Dict):
        with open(self.storage_file, "r") as f:
            data = json.load(f)

        # Merge reserves (by country and date)
        existing_reserves = {(r["country"], r["date"]): r for r in data["reserves"]}
        for r in reserves:
            existing_reserves[(r["country"], r["date"])] = r

        data["reserves"] = sorted(
            existing_reserves.values(),
            key=lambda x: (x["date"], x["amount"]),
            reverse=True,
        )
        data["balance"] = balance
        data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.storage_file, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_latest_report(self) -> Dict:
        """
        Get the latest gold reserves for major countries and their changes (1m, 1y).
        """
        if not self.storage_file.exists():
            return {}

        with open(self.storage_file, "r") as f:
            data = json.load(f)

        reserves = data.get("reserves", [])
        if not reserves:
            return {}

        # Group by country and sort by date descending
        country_groups = {}
        for r in reserves:
            c = r["country"]
            if c not in country_groups:
                country_groups[c] = []
            country_groups[c].append(r)

        for c in country_groups:
            country_groups[c].sort(key=lambda x: x["date"], reverse=True)

        report = []
        for c, records in country_groups.items():
            latest = records[0]

            # Helper to calculate previous month date string
            def get_prev_month(date_str):
                y, m = map(int, date_str.split("-"))
                if m == 1:
                    return f"{y - 1}-12"
                return f"{y}-{m - 1:02d}"

            # 1 Month Change (MoM)
            change_1m = None
            change_1m_pct = 0.0
            target_date_1m = get_prev_month(latest["date"])

            for r in records[1:]:
                if r["date"] == target_date_1m:
                    change_1m = latest["amount"] - r["amount"]
                    if r["amount"] > 0:
                        change_1m_pct = (change_1m / r["amount"]) * 100
                    break

            # 1 Year Change (YoY)
            change_1y = None
            change_1y_pct = 0.0

            latest_date = latest["date"]
            try:
                ly, lm = map(int, latest_date.split("-"))
                target_date_1y = f"{ly - 1}-{lm:02d}"

                for r in records[1:]:
                    if r["date"] == target_date_1y:
                        change_1y = latest["amount"] - r["amount"]
                        if r["amount"] > 0:
                            change_1y_pct = (change_1y / r["amount"]) * 100
                        break
            except (ValueError, IndexError):
                pass

            report.append(
                {
                    "country": c,
                    "code": latest.get("code", ""),
                    "amount": latest["amount"],
                    "date": latest["date"],
                    "change_1m": change_1m,
                    "change_1m_pct": change_1m_pct,
                    "change_1y": change_1y,
                    "change_1y_pct": change_1y_pct,
                }
            )

        # Sort by amount descending
        report.sort(key=lambda x: x["amount"], reverse=True)

        return {
            "reserves": report,
            "balance": data.get("balance", {}),
            "last_update": data.get("last_update"),
        }

    def get_history_report(self, country_id: str) -> List[Dict]:
        """
        Get 12-month history for a specific country (by name or code).
        """
        if not self.storage_file.exists():
            return []

        with open(self.storage_file, "r") as f:
            data = json.load(f)

        reserves = data.get("reserves", [])

        # Filter by country name or code
        target = country_id.upper()
        history = [
            r
            for r in reserves
            if r["country"] == target or r.get("code", "").upper() == target
        ]

        # Sort by date descending, take top 12
        history.sort(key=lambda x: x["date"], reverse=True)
        return history[:12]


gold_service = GoldService()

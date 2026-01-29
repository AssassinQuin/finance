import json
from datetime import datetime
from typing import Dict, List, Optional

from ..core.config import config


class GPRService:
    def __init__(self):
        self.storage_file = config.data_dir / "gpr_history.json"
        # Initial baseline data (Benchmark GPR Index)
        self.baseline = {
            "2026-01": 135.24,
            "2025-12": 121.45,
            "2025-11": 118.30,
            "2025-10": 112.85,
            "2025-09": 110.12,
            "2025-08": 109.45,
            "2025-07": 108.56,
            "2025-06": 107.20,
            "2025-01": 104.25,
            "2024-10": 115.40,
            "2024-01": 102.15,
            "2023-10": 264.30,  # Peak (Gaza)
            "2022-02": 328.50,  # Peak (Ukraine)
            "2021-01": 98.65,
            "2020-01": 145.20,
            "2016-01": 92.45,
            "2015-01": 88.30,
            "2014-01": 85.12,
        }
        self._ensure_storage()

    def _ensure_storage(self):
        if not config.data_dir.exists():
            config.data_dir.mkdir(parents=True)
        if not self.storage_file.exists():
            with open(self.storage_file, "w") as f:
                json.dump(self.baseline, f, ensure_ascii=False, indent=2)

    def load_data(self) -> Dict[str, float]:
        if not self.storage_file.exists():
            return self.baseline
        with open(self.storage_file, "r") as f:
            return json.load(f)

    def get_gpr_history(self, months: int = 12) -> List[Dict]:
        """
        Get GPR historical data for plotting.
        """
        data = self.load_data()
        sorted_dates = sorted(data.keys())
        
        history = []
        for d in sorted_dates:
            history.append({"date": d, "value": data[d]})
            
        return history[-months:]

    def get_gpr_analysis(self) -> Dict:
        """
        Calculate GPR index changes for multiple horizons: 1m, 3m, 6m, 1y, 5y, 10y.
        """
        data = self.load_data()
        dates = sorted(data.keys(), reverse=True)
        if not dates:
            return {}

        latest_date = dates[0]
        latest_val = data[latest_date]

        def get_val_at_offset(months: int) -> Optional[float]:
            try:
                ly, lm = map(int, latest_date.split("-"))
                target_m = lm - months
                target_y = ly
                while target_m <= 0:
                    target_m += 12
                    target_y -= 1
                target_date = f"{target_y}-{target_m:02d}"
                
                # Try exact match
                if target_date in data:
                    return data[target_date]
                
                # Try finding closest date before target
                for d in dates:
                    if d <= target_date:
                        return data[d]
                return None
            except Exception:
                return None

        analysis = {
            "latest": {"date": latest_date, "value": latest_val},
            "horizons": {}
        }

        horizons = {
            "1M": 1,
            "3M": 3,
            "6M": 6,
            "1Y": 12,
            "5Y": 60,
            "10Y": 120
        }

        for label, months in horizons.items():
            prev_val = get_val_at_offset(months)
            if prev_val is not None:
                change = latest_val - prev_val
                analysis["horizons"][label] = {
                    "value": prev_val,
                    "change": change,
                    "change_pct": (change / prev_val) * 100 if prev_val != 0 else 0
                }
            else:
                analysis["horizons"][label] = None

        # Risk Level
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

gpr_service = GPRService()

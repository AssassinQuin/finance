"""
World Gold Council (WGC) Supply/Demand Data Scraper.

Data source: https://www.gold.org/goldhub/data/demand-and-supply
Quarterly gold supply and demand statistics.

Excel Structure (GDT_Tables_Q425_CN.xlsx):
- Sheet "黄金供需" contains supply/demand data
- Row 5: Year/Quarter headers
- Rows 6-28: Data rows with labels in column B
- Columns 3-18: Annual data (2010-2025)
- Columns 24+: Quarterly data (2010 Q1 onwards)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from ...infra.http_client import http_client

logger = logging.getLogger(__name__)


# Excel Row Mapping (Row number -> Field name)
ROW_MAPPING = {
    6: "total_supply",  # 总供应量
    7: "mine_production",  # 金矿产量
    8: "net_hedging",  # 生产商净套保
    10: "recycling",  # 回收金
    11: "total_demand",  # 总需求量
    12: "jewelry",  # 金饰制造
    15: "technology",  # 科技
    19: "total_investment",  # 投资
    20: "bars_coins",  # 金条和金币总需求量
    24: "etfs",  # 黄金ETF及类似产品
    25: "central_banks",  # 各央行和官方机构
    27: "otc_investment",  # 场外投资及其他
    28: "price_avg_usd",  # LBMA黄金价格
}


@dataclass
class QuarterlySupplyDemand:
    """Gold supply and demand data for a single quarter"""

    year: int
    quarter: int
    period: str

    # Supply (tonnes)
    mine_production: float = 0.0
    recycling: float = 0.0
    net_hedging: float = 0.0
    total_supply: float = 0.0

    # Demand (tonnes)
    jewelry: float = 0.0
    technology: float = 0.0
    total_investment: float = 0.0
    bars_coins: float = 0.0
    etfs: float = 0.0
    otc_investment: float = 0.0
    central_banks: float = 0.0
    total_demand: float = 0.0

    # Balance & Price
    supply_demand_balance: float = 0.0
    price_avg_usd: float = 0.0

    source: str = "WGC"


class WGCScraper:
    """WGC Gold Supply/Demand Data Scraper"""

    # Known Excel file URLs (can be extended)
    KNOWN_EXCEL_URLS: dict[tuple[int, int], str] = {
        (2024, 4): "https://www.gold.org/sites/default/files/2024-11/GDT_Tables_Q424_CN.xlsx",
        (2024, 3): "https://www.gold.org/sites/default/files/2024-11/GDT_Tables_Q424_CN.xlsx",
        (2024, 2): "https://www.gold.org/sites/default/files/2024-08/GDT_Tables_Q224_CN.xlsx",
        (2024, 1): "https://www.gold.org/sites/default/files/2024-05/GDT_Tables_Q124_CN.xlsx",
    }

    def __init__(self):
        pass

    async def close(self):
        """Close resources (no-op for WGCScraper, uses global http_client)"""
        pass

    async def download_excel(self, year: int, quarter: int) -> bytes | None:
        """
        Download WGC Excel file for a specific quarter.

        Args:
            year: Year (e.g., 2024)
            quarter: Quarter (1-4)

        Returns:
            Excel file bytes or None if not available
        """
        url = self.KNOWN_EXCEL_URLS.get((year, quarter))
        if not url:
            logger.debug(f"No known URL for {year} Q{quarter}")
            return None

        try:
            content = await http_client.get_binary(url)
            if content is None:
                logger.debug(f"No content returned for {year} Q{quarter}")
                return None
            logger.info(f"Downloaded WGC Excel for {year} Q{quarter}: {len(content)} bytes")
            return content
        except Exception as e:
            logger.error(f"Failed to download WGC Excel: {e}")
            return None

    def parse_excel(self, excel_path: str | Path | bytes) -> list[QuarterlySupplyDemand]:
        """
        Parse WGC Excel file and extract quarterly supply/demand data.

        Args:
            excel_path: Path to Excel file or bytes content

        Returns:
            List of QuarterlySupplyDemand records
        """
        try:
            if isinstance(excel_path, bytes):
                workbook = load_workbook(BytesIO(excel_path), data_only=True)
            else:
                workbook = load_workbook(Path(excel_path), data_only=True)
        except Exception as e:
            logger.debug(f"Failed to load Excel: {e}")
            return []

        # Get the sheet
        ws = workbook.active
        if ws.title != "黄金供需":
            logger.debug("Sheet '黄金供需' not found")
            return []

        results: list[QuarterlySupplyDemand] = []

        # Find quarterly data columns (columns 24+)
        for col_idx in range(24, ws.max_column + 1):
            # Check if column has a year/quarter header (e.g., "2024 Q1")
            cell_value = ws.cell(row=5, column=col_idx).value
            if cell_value is None:
                continue

            # Parse quarter from cell value like "2024 Q1"
            header_str = str(cell_value).strip()
            if " Q" not in header_str:
                continue

            # Parse year and quarter
            try:
                parts = header_str.split(" Q")
                year = int(parts[0])
                quarter = int(parts[1])
            except (ValueError, TypeError, IndexError):
                continue

            # Extract data
            data = self._extract_quarter_data(ws, col_idx, year, quarter)
            if data:
                results.append(data)

        return results

    def _extract_quarter_data(
        self, ws: Worksheet, col_idx: int, year: int, quarter: int
    ) -> QuarterlySupplyDemand | None:
        """Extract data for a specific quarter from a column."""

        # Read all values from the column
        values: dict[str, float] = {}

        for row_idx, field_name in ROW_MAPPING.items():
            cell_value = ws.cell(row=row_idx, column=col_idx).value
            if cell_value is not None:
                try:
                    values[field_name] = float(cell_value)
                except (ValueError, TypeError):
                    pass

        # Skip if no meaningful data
        if not values or values.get("total_supply", 0) == 0:
            return None

        # Calculate balance
        balance = values.get("total_supply", 0) - values.get("total_demand", 0)

        return QuarterlySupplyDemand(
            year=year,
            quarter=quarter,
            period=f"{year} Q{quarter}",
            mine_production=values.get("mine_production", 0),
            recycling=values.get("recycling", 0),
            net_hedging=values.get("net_hedging", 0),
            total_supply=values.get("total_supply", 0),
            jewelry=values.get("jewelry", 0),
            technology=values.get("technology", 0),
            total_investment=values.get("total_investment", 0),
            bars_coins=values.get("bars_coins", 0),
            etfs=values.get("etfs", 0),
            otc_investment=values.get("otc_investment", 0),
            central_banks=values.get("central_banks", 0),
            total_demand=values.get("total_demand", 0),
            supply_demand_balance=balance,
            price_avg_usd=values.get("price_avg_usd", 0),
        )

    async def fetch_latest(self) -> list[QuarterlySupplyDemand]:
        """Fetch latest available quarterly data."""
        current_year = datetime.now().year
        current_quarter = (datetime.now().month - 1) // 3 + 1

        # Try recent quarters
        for year in range(current_year, current_year - 3, -1):
            for quarter in range(4, 0, -1):
                if year == current_year and quarter > current_quarter:
                    continue

                excel_bytes = await self.download_excel(year, quarter)
                if excel_bytes:
                    return self.parse_excel(excel_bytes)

        return []

    async def fetch_supply_demand(self) -> list[QuarterlySupplyDemand]:
        """Alias for fetch_latest for backward compatibility."""
        return await self.fetch_latest()

    def fetch_from_local(self, file_path: str | Path) -> list[QuarterlySupplyDemand]:
        """
        Parse a local WGC Excel file.

        Args:
            file_path: Path to the Excel file

        Returns:
            List of QuarterlySupplyDemand records
        """
        return self.parse_excel(file_path)


# Singleton instance
wgc_scraper = WGCScraper()

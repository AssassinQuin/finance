"""
World Gold Council (WGC) Supply/Demand Data Scraper.

Data source: https://www.gold.org/goldhub/research/gold-demand-trends/
Parses HTML tables from WGC Gold Demand Trends quarterly reports.

Report pages contain a standard supply/demand table with:
- Annual columns (current year, previous year)
- Quarterly columns (Q4 current, Q4 previous)
- Rows: Mine Production, Net Hedging, Recycling, Jewelry, Technology, Investment, Central Banks, etc.
"""

from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup

from ...core.config import Settings, config
from ...core.models.gold_supply_demand import GoldSupplyDemand
from ...infra.http_client import HttpClient
from ...utils.logger import get_logger
from ...utils.time_util import utcnow

logger = get_logger("fcli.scraper.wgc")

ROW_LABEL_MAP: dict[str, str] = {
    "Mine Production": "mine_production",
    "Net Producer Hedging": "net_hedging",
    "Total Mine Supply": "total_mine_supply",
    "Recycled Gold": "recycling",
    "Total Supply": "total_supply",
    "Jewellery Fabrication": "jewelry",
    "Technology": "technology",
    "Total Bar and Coin": "bars_coins",
    "ETFs & Similar Products": "etfs",
    "Central Banks & Other inst.": "central_banks",
    "Gold Demand": "total_demand",
    "OTC and Other": "otc_investment",
    "Total Demand": "total_demand_check",
    "LBMA Gold Price (US$/oz)": "price_avg_usd",
    "Investment": "total_investment",
}


class WGCScraper:
    """WGC Gold Supply/Demand Data Scraper - HTML report parsing."""

    def __init__(self, http_client: HttpClient, settings: Settings | None = None):
        self._http_client = http_client
        self._config = settings or config
        self._report_urls = self._build_report_urls()

    async def close(self):
        pass

    async def fetch_latest(self) -> list[GoldSupplyDemand]:
        for url in self._report_urls:
            html = await self._http_client.fetch(url, text_mode=True)
            if not html or len(html) < 5000:
                logger.debug("No valid HTML from %s", url)
                continue
            logger.info("Downloaded WGC report page: %d chars from %s", len(html), url)
            results = self.parse_html(html)
            if results:
                return results
        logger.warning("No valid WGC data found from any report URL")
        return []

    def _build_report_urls(self) -> list[str]:
        current_year = utcnow().year
        lookback_years = self._config.datasource.gold.wgc_lookback_years
        urls: list[str] = []
        for year in range(current_year, current_year - lookback_years, -1):
            urls.append(f"https://www.gold.org/goldhub/research/gold-demand-trends/gold-demand-trends-full-year-{year}")
            for quarter in range(4, 0, -1):
                urls.append(
                    "https://www.gold.org/goldhub/research/gold-demand-trends/"
                    f"gold-demand-trends-full-year-and-q{quarter}-{year}"
                )
        return urls

    def parse_html(self, html: str) -> list[GoldSupplyDemand]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            logger.warning("No <table> found in WGC report page")
            return []

        headers = self._parse_headers(table)
        if not headers:
            logger.warning("No column headers parsed from WGC table")
            return []

        rows = self._parse_rows(table)
        if not rows:
            logger.warning("No data rows parsed from WGC table")
            return []

        return self._build_records(headers, rows)

    def _parse_headers(self, table) -> list[dict]:
        header_row = table.find("tr")
        if not header_row:
            return []
        cells = header_row.find_all(["th", "td"])
        headers = []
        for cell in cells:
            text = cell.get_text(strip=True)
            headers.append({"text": text})
        return headers

    def _parse_rows(self, table) -> dict[str, dict[str, float]]:
        rows: dict[str, dict[str, float]] = {}
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            label = cells[0].get_text(strip=True)
            field_name = self._match_label(label)
            if not field_name:
                continue
            values: dict[str, float] = {}
            for i, cell in enumerate(cells[1:], start=1):
                raw = cell.get_text(strip=True).replace(",", "").replace(" ", "")
                val = self._parse_number(raw)
                if val is not None:
                    values[str(i)] = val
            rows[field_name] = values
        return rows

    def _match_label(self, label: str) -> str | None:
        clean = re.sub(r"\s+", " ", label).strip()
        for pattern, field in ROW_LABEL_MAP.items():
            if pattern.lower() in clean.lower():
                return field
        return None

    @staticmethod
    def _parse_number(text: str) -> float | None:
        text = text.strip()
        if not text or text in ("-", "–", "—", "N/A", "n/a"):
            return None
        match = re.match(r"[-+]?\d+\.?\d*", text)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None

    def _build_records(self, headers: list[dict], rows: dict[str, dict[str, float]]) -> list[GoldSupplyDemand]:
        if not headers or not rows:
            return []

        col_meta = self._identify_columns(headers)
        if not col_meta:
            logger.warning("Could not identify year/quarter columns from headers")
            logger.debug("Headers: %s", [h.get("text") for h in headers])
            return []

        results: list[GoldSupplyDemand] = []
        for col_idx, meta in col_meta.items():
            record = self._extract_record(rows, col_idx, meta)
            if record:
                results.append(record)
        return results

    def _identify_columns(self, headers: list[dict]) -> dict[int, dict]:
        result: dict[int, dict] = {}
        # First header cell is the row label column; data columns start from index 1.
        for col_idx, h in enumerate(headers[1:], start=1):
            text = h.get("text", "")
            parsed = self._parse_header_text(text)
            if parsed:
                result[col_idx] = parsed
        return result

    @staticmethod
    def _parse_header_text(text: str) -> dict | None:
        text = text.strip()
        if not text:
            return None

        # Skip non-data columns such as y/y percentage columns.
        if "y/y" in text.lower():
            return None

        year: int | None = None
        quarter = None

        m = re.match(r"^(\d{4})$", text)
        if m:
            year = int(m.group(1))
            return {"year": year, "quarter": None, "type": "annual"}

        # Header formats seen on WGC pages:
        # - Q4'24 / Q4’24
        # - Q4 2024
        short_q = re.search(r"Q([1-4])\s*['’]\s*(\d{2})", text, re.IGNORECASE)
        if short_q:
            quarter = int(short_q.group(1))
            year = 2000 + int(short_q.group(2))
            return {"year": year, "quarter": quarter, "type": "quarterly"}

        long_q = re.search(r"Q([1-4])\s*(\d{4})", text, re.IGNORECASE)
        if long_q:
            quarter = int(long_q.group(1))
            year = int(long_q.group(2))
            return {"year": year, "quarter": quarter, "type": "quarterly"}

        if year:
            return {"year": year, "quarter": quarter, "type": "quarterly" if quarter else "annual"}

        return None

    def _extract_record(self, rows: dict[str, dict[str, float]], col_idx: int, meta: dict) -> GoldSupplyDemand | None:
        def get_val(field: str) -> float | None:
            vals = rows.get(field, {})
            return vals.get(str(col_idx))

        total_supply = get_val("total_supply")
        if total_supply is None or total_supply == 0:
            return None

        total_demand = get_val("total_demand") or get_val("total_demand_check") or 0
        total_investment = get_val("total_investment") or 0
        if total_investment == 0:
            bars = get_val("bars_coins") or 0
            etfs = get_val("etfs") or 0
            cb = get_val("central_banks") or 0
            otc = get_val("otc_investment") or 0
            total_investment = bars + etfs + cb + otc

        balance = total_supply - total_demand
        quarter = meta.get("quarter") or 0

        return GoldSupplyDemand(
            year=meta["year"],
            quarter=quarter,
            period=f"{meta['year']}" + (f" Q{quarter}" if quarter else ""),
            mine_production=get_val("mine_production") or 0,
            recycling=get_val("recycling") or 0,
            net_hedging=get_val("net_hedging") or 0,
            total_supply=total_supply,
            jewelry=get_val("jewelry") or 0,
            technology=get_val("technology") or 0,
            total_investment=total_investment,
            bars_coins=get_val("bars_coins") or 0,
            etfs=get_val("etfs") or 0,
            otc_investment=get_val("otc_investment") or 0,
            central_banks=get_val("central_banks") or 0,
            total_demand=total_demand,
            supply_demand_balance=balance,
            price_avg_usd=get_val("price_avg_usd"),
            data_source="WGC",
            fetch_time=utcnow(),
        )

    def fetch_from_local(self, file_path: str | Path) -> list[GoldSupplyDemand]:
        content = Path(file_path).read_text(encoding="utf-8")
        return self.parse_html(content)

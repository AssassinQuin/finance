"""
WGC Excel scraper for gold reserve data with monthly changes.
Downloads and parses Excel files from World Gold Council.
Falls back to local data when network is unavailable.
"""

import json
import logging
import re
import tempfile
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional

import openpyxl

from .base import BaseScraper, ScraperResult
from ...core.database import GoldReserve
from ...infra.http_client import http_client

logger = logging.getLogger(__name__)

LOCAL_DATA_FILE = Path(__file__).parent.parent.parent.parent / "data" / "gold_reserves_history.json"


class WGCScraper(BaseScraper):
    """
    WGC (World Gold Council) scraper for gold reserves.
    
    Downloads Excel files containing monthly gold reserve changes.
    Falls back to local data file when network is unavailable.
    """
    
    BASE_URL = "https://www.gold.org"
    DATA_PAGE_URL = "https://www.gold.org/goldhub/data/monthly-central-bank-statistics"
    
    def __init__(self):
        super().__init__()
        self._source_name = "WGC"
        self._cache: Dict[str, bytes] = {}
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    async def fetch(self) -> Any:
        # 首先尝试在线获取
        try:
            excel_data = await self._fetch_excel()
            if excel_data:
                return {"type": "excel", "data": excel_data}
        except Exception as e:
            logger.warning(f"Excel download failed: {e}")
        
        # 降级到本地数据
        logger.info("Falling back to local data file")
        local_data = self._load_local_data()
        if local_data:
            return {"type": "local", "data": local_data}
        
        return None
    
    def _load_local_data(self) -> Optional[Dict]:
        """从本地 JSON 文件加载数据"""
        try:
            if LOCAL_DATA_FILE.exists():
                with open(LOCAL_DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"Loaded local data with {len(data.get('reserves', {}))} countries")
                    return data
        except Exception as e:
            logger.error(f"Failed to load local data: {e}")
        return None
    
    async def _get_excel_urls(self) -> Dict[str, str]:
        """Scrape the WGC data page to find current Excel download URLs."""
        html = await http_client.fetch(self.DATA_PAGE_URL, text_mode=True)
        if not html:
            return {}
        
        urls = {}
        xlsx_links = re.findall(r'href="(/download/file/\d+/[^"]+\.xlsx)"', html)
        
        for link in xlsx_links:
            full_url = f"{self.BASE_URL}{link}"
            link_lower = link.lower()
            
            if 'changes' in link_lower:
                urls['monthly_changes'] = full_url
            elif 'holdings' in link_lower or 'reserves' in link_lower:
                urls['reserves'] = full_url
        
        if not urls and xlsx_links:
            urls['reserves'] = f"{self.BASE_URL}{xlsx_links[0]}"
        
        logger.info(f"Found WGC Excel URLs: {urls}")
        return urls
    
    async def _fetch_excel(self) -> Optional[bytes]:
        """Download WGC Excel file."""
        urls = await self._get_excel_urls()
        
        for key in ['reserves', 'monthly_changes']:
            url = urls.get(key)
            if not url:
                continue
            
            try:
                logger.info(f"Downloading WGC Excel: {url}")
                response = await http_client.fetch(url, binary_mode=True)
                
                if response and isinstance(response, bytes) and len(response) > 1000:
                    if response[:4] == b'PK\x03\x04':
                        logger.info(f"Successfully downloaded {len(response)} bytes")
                        return response
                    else:
                        logger.warning(f"Response is not a valid ZIP/Excel file")
                        
            except Exception as e:
                logger.warning(f"Failed to download {url}: {e}")
                continue
        
        return None
    
    def parse(self, raw_data: Any) -> List[GoldReserve]:
        if not raw_data:
            return []
        
        reserves = []
        fetch_time = datetime.now()
        
        if raw_data.get("type") == "excel":
            reserves = self._parse_excel_data(raw_data.get("data"), fetch_time)
        elif raw_data.get("type") == "local":
            reserves = self._parse_local_data(raw_data.get("data"), fetch_time)
        
        return reserves
    
    def _parse_local_data(self, data: Dict, fetch_time: datetime) -> List[GoldReserve]:
        """解析本地 JSON 数据"""
        reserves = []
        reserves_data = data.get("reserves", {})
        
        for country_code, country_data in reserves_data.items():
            try:
                history = country_data.get("history", [])
                if not history:
                    continue
                
                # 获取最新数据
                latest = history[-1]
                
                reserves.append(GoldReserve(
                    country_code=country_code,
                    country_name=country_data.get("country_name", country_code),
                    amount_tonnes=float(latest.get("amount", 0)),
                    percent_of_reserves=country_data.get("percent_of_reserves"),
                    report_date=self._parse_date(latest.get("date")),
                    data_source="WGC_LOCAL",
                    fetch_time=fetch_time,
                ))
            except Exception as e:
                logger.warning(f"Failed to parse local data for {country_code}: {e}")
                continue
        
        logger.info(f"Parsed {len(reserves)} records from local data")
        return reserves
    
    def _parse_excel_data(self, content: bytes, fetch_time: datetime) -> List[GoldReserve]:
        """解析 Excel 数据"""
        if not content:
            return []
        
        parsed = self._parse_excel_content(content)
        reserves = []
        
        for item in parsed:
            try:
                country_code = self.country_name_to_code(item["country"])
                
                reserves.append(GoldReserve(
                    country_code=country_code,
                    country_name=item["country"],
                    amount_tonnes=float(item.get("amount", 0)),
                    percent_of_reserves=item.get("percent"),
                    report_date=date.today(),
                    data_source="WGC",
                    fetch_time=fetch_time,
                ))
            except Exception as e:
                logger.warning(f"Failed to parse item: {e}")
                continue
        
        return reserves
    
    def _parse_date(self, date_str: str) -> date:
        """解析日期字符串"""
        if not date_str:
            return date.today()
        try:
            return datetime.strptime(date_str, "%Y-%m").date()
        except ValueError:
            return date.today()
    
    def _parse_excel_content(self, content: bytes) -> List[Dict]:
        if not content:
            return []
        
        results = []
        tmp_path = None
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                tmp.write(content)
                tmp.flush()
                tmp_path = tmp.name
            
            wb = openpyxl.load_workbook(tmp_path, data_only=True)
            
            sheet_name = wb.sheetnames[0] if wb.sheetnames else None
            if not sheet_name:
                logger.warning("No sheets found in Excel file")
                return []
            
            ws = wb[sheet_name]
            
            header_row = None
            country_col = None
            tonnes_col = None
            percent_col = None
            
            for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
                if row_idx > 10:
                    break
                
                for col_idx, cell in enumerate(row):
                    if cell is None:
                        continue
                    
                    cell_str = str(cell).lower().strip()
                    
                    if any(kw in cell_str for kw in ["country", "国家", "countries"]):
                        country_col = col_idx
                        header_row = row_idx
                    elif any(kw in cell_str for kw in ["tonnes", "吨", "tonnage", "holdings"]):
                        tonnes_col = col_idx
                    elif any(kw in cell_str for kw in ["%", "percent"]):
                        percent_col = col_idx
            
            if header_row is None or country_col is None:
                logger.warning("Could not find header row or country column")
                return []
            
            for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
                if not row or len(row) <= country_col:
                    continue
                
                country = row[country_col]
                if not country or not isinstance(country, str):
                    continue
                
                country_str = str(country).strip().lower()
                if any(kw in country_str for kw in ["country", "total", "world", "other"]):
                    continue
                
                amount = 0.0
                if tonnes_col is not None and len(row) > tonnes_col:
                    try:
                        val = row[tonnes_col]
                        amount = float(val) if val is not None else 0.0
                    except (ValueError, TypeError):
                        amount = 0.0
                
                if amount <= 0:
                    continue
                
                percent = None
                if percent_col is not None and len(row) > percent_col:
                    try:
                        val = row[percent_col]
                        percent = float(val) if val is not None else None
                    except (ValueError, TypeError):
                        percent = None
                
                results.append({
                    "country": country.strip(),
                    "amount": amount,
                    "percent": percent,
                })
            
            logger.info(f"Parsed {len(results)} records from WGC Excel")
            
        except Exception as e:
            logger.error(f"Failed to parse Excel: {e}")
        finally:
            if tmp_path:
                try:
                    import os
                    os.unlink(tmp_path)
                except:
                    pass
        
        return results

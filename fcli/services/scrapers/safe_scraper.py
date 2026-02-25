"""
国家外汇管理局 (SAFE) 官方黄金储备爬虫
数据来源: https://www.safe.gov.cn
权威数据，比 AkShare 更准确

数据获取方式: 从年度页面获取 Excel 文件下载链接，解析 Excel 获取月度数据
"""

import re
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from io import BytesIO

from .base import BaseScraper
from ...core.database import GoldReserve
from ...infra.http_client import http_client

logger = logging.getLogger(__name__)


class SAFEScraper(BaseScraper):
    """
    国家外汇管理局官方黄金储备数据爬虫
    
    数据来源: https://www.safe.gov.cn/safe/whcb/index.html
    更新频率: 每月7日左右
    数据获取: 从年度页面下载 Excel 文件解析
    
    黄金储备单位: 万盎司 (需转换为吨)
    转换公式: 1万盎司 = 0.311035吨
    """
    
    # 万盎司转吨
    WAN_OZ_TO_TONNE = 0.311035
    BASE_URL = "https://www.safe.gov.cn"
    INDEX_URL = "https://www.safe.gov.cn/safe/whcb/index.html"
    
    # 官方储备资产历史URL (每年一份页面，包含 Excel 下载链接)
    # 注意: 旧版 URL 可能失效，实际使用时会从索引页动态发现
    YEAR_URLS = {
        2026: "https://www.safe.gov.cn/safe/2026/0205/27113.html",
        2025: "https://www.safe.gov.cn/safe/2025/0206/25745.html",
        2020: "https://www.safe.gov.cn/safe/2020/0207/26908.html",
    }
    
    def __init__(self):
        super().__init__()
        self._source_name = "SAFE"
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    async def fetch(self) -> Any:
        """
        从国家外汇管理局获取所有历史黄金储备数据
        
        Returns:
            dict: {"type": "safe", "data": [...]}
        """
        all_data = []
        
        # 首先从索引页动态发现所有有 Excel 的页面
        discovered_urls = await self._discover_excel_pages()
        
        # 合并发现的 URL 和硬编码的 URL
        all_year_urls = {**self.YEAR_URLS, **discovered_urls}
        
        # 获取最近5年数据
        current_year = datetime.now().year
        years_to_fetch = range(current_year, current_year - 5, -1)
        
        for year in years_to_fetch:
            url = all_year_urls.get(year)
            if not url:
                continue
            
            try:
                logger.info(f"Fetching SAFE data for {year}...")
                
                # 1. 获取年度页面 HTML
                html = await http_client.fetch(url, text_mode=True)
                
                if not html:
                    continue
                
                # 2. 从 HTML 中提取 Excel 下载链接
                xlsx_url = self._find_xlsx_url(html)
                if not xlsx_url:
                    logger.warning(f"No Excel file found for {year}")
                    continue
                
                # 3. 下载并解析 Excel
                monthly_data = await self._fetch_and_parse_excel(xlsx_url, year)
                
                if monthly_data:
                    all_data.extend(monthly_data)
                
                # 避免请求过快
                import asyncio
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Failed to fetch SAFE data for {year}: {e}")
                continue
        
        if not all_data:
            return None
        
        return {
            "type": "safe",
            "data": all_data,
        }
    
    async def fetch_by_month(self, year: int, month: int) -> Optional[Dict]:
        """
        获取指定年月的黄金储备数据
        
        Args:
            year: 年份
            month: 月份 (1-12)
            
        Returns:
            该月的数据字典
        """
        url = self.YEAR_URLS.get(year)
        if not url:
            logger.warning(f"No URL for year {year}")
            return None
        
        try:
            html = await http_client.fetch(url, text_mode=True)
            
            if not html:
                return None
            
            xlsx_url = self._find_xlsx_url(html)
            if not xlsx_url:
                return None
            
            monthly_data = await self._fetch_and_parse_excel(xlsx_url, year)
            
            # 查找指定月份
            period = f"{year}.{month:02d}"
            for data in monthly_data:
                if data.get("date") == period:
                    return data
            
            logger.warning(f"No data found for {period}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch SAFE data for {year}-{month}: {e}")
            return None
    
    async def _discover_excel_pages(self) -> Dict[int, str]:
        """
        从索引页动态发现有 Excel 文件的年度页面
        
        Returns:
            dict: {year: url}
        """
        discovered = {}
        
        try:
            html = await http_client.fetch(self.INDEX_URL, text_mode=True)
            if not html:
                return discovered
            
            # 找到所有年度报告链接
            link_pattern = r'href=["\']([^"\']*/safe/(\d{4})/\d{4}/\d+\.html)["\']'
            matches = re.findall(link_pattern, html)
            
            # 对每个链接检查是否有 Excel 文件
            checked_urls = set()
            for path, year_str in matches:
                year = int(year_str)
                if year in discovered:
                    continue
                
                full_url = self.BASE_URL + path
                if full_url in checked_urls:
                    continue
                checked_urls.add(full_url)
                
                # 检查该页面是否有 Excel 文件
                try:
                    page_html = await http_client.fetch(full_url, text_mode=True)
                    if page_html and '.xlsx' in page_html.lower():
                        discovered[year] = full_url
                        logger.debug(f"Discovered Excel page for {year}: {full_url}")
                except Exception:
                    pass
                
                # 避免请求过快
                import asyncio
                await asyncio.sleep(0.3)
        
        except Exception as e:
            logger.warning(f"Failed to discover Excel pages: {e}")
        
        return discovered
    
    def _find_xlsx_url(self, html: str) -> Optional[str]:
        """
        从 HTML 页面中提取 Excel 文件下载链接
        
        Args:
            html: HTML 内容
            
        Returns:
            Excel 文件的完整 URL，如果找不到则返回 None
        """
        # 查找 .xlsx 文件链接
        xlsx_pattern = r'href=["\']([^"\']*.xlsx[^"\']*)["\']'
        matches = re.findall(xlsx_pattern, html, re.IGNORECASE)
        
        if matches:
            # 返回第一个匹配的 Excel 文件
            path = matches[0]
            if path.startswith('http'):
                return path
            return self.BASE_URL + path
        
        return None
    
    async def _fetch_and_parse_excel(self, xlsx_url: str, year: int) -> List[Dict]:
        """
        下载并解析 Excel 文件
        
        Args:
            xlsx_url: Excel 文件 URL
            year: 数据年份
            
        Returns:
            月度数据列表
        """
        try:
            import pandas as pd
            
            # 下载 Excel 文件
            content = await http_client.fetch(xlsx_url, binary_mode=True)
            if not content:
                logger.warning(f"Failed to download Excel from {xlsx_url}")
                return []
            
            # 解析 Excel
            df = pd.read_excel(BytesIO(content), header=None)
            
            # 查找表头行 (包含 2026.01 等月份)
            header_row = None
            for i, row in df.iterrows():
                row_str = ' '.join([str(x) for x in row.values if pd.notna(x)])
                if re.search(r'\d{4}\.\d{2}', row_str):
                    header_row = i
                    break
            
            if header_row is None:
                logger.warning(f"Could not find header row in Excel for {year}")
                return []
            
            # 获取月份列表
            headers = df.iloc[header_row].values
            months = []
            for h in headers:
                if pd.notna(h) and re.match(r'\d{4}\.\d{2}', str(h)):
                    months.append(str(h))
            
            # 查找黄金万盎司数据行 (包含 "万盎司" 的行)
            gold_oz_row = None
            for i, row in df.iterrows():
                row_str = ' '.join([str(x) for x in row.values if pd.notna(x)])
                if '万盎司' in row_str:
                    gold_oz_row = i
                    break
            
            if gold_oz_row is None:
                logger.warning(f"Could not find gold 万盎司 row for {year}")
                return []
            
            # 提取每月数据
            results = []
            oz_values = df.iloc[gold_oz_row].values
            
            for i, month in enumerate(months):
                # Excel 中月份和数据的对应关系
                # 列结构: 项目 | 2026.01亿美元 | 2026.01亿SDR | 2026.02亿美元 | ...
                # 万盎司行: | 7419万盎司 | 7419万盎司 | ...
                # 每个月有两列数据 (亿美元和亿SDR)，万盎司重复出现
                
                # 数据列索引: 每月占2列，从第1列开始 (第0列是项目名)
                data_col = i * 2 + 1  # 取第一个值 (亿美元列对应的万盎司)
                
                if data_col < len(oz_values):
                    oz_str = oz_values[data_col]
                    if pd.notna(oz_str):
                        # 提取数字
                        oz_match = re.search(r'([\d.]+)', str(oz_str))
                        if oz_match:
                            try:
                                gold_wan_oz = float(oz_match.group(1))
                                gold_tonnes = gold_wan_oz * self.WAN_OZ_TO_TONNE
                                
                                # 转换日期格式: 2026.01 -> 2026-01
                                date_str = month.replace('.', '-')
                                
                                results.append({
                                    "country_code": "CHN",
                                    "country_name": "中国",
                                    "amount": round(gold_tonnes, 2),
                                    "amount_wan_oz": gold_wan_oz,
                                    "date": date_str,
                                })
                            except ValueError:
                                continue
            
            logger.info(f"Parsed {len(results)} monthly records for {year}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to parse Excel for {year}: {e}")
            return []
    
    def parse(self, raw_data: Any) -> List[GoldReserve]:
        """
        解析 SAFE 数据为 GoldReserve 对象列表
        
        Args:
            raw_data: SAFE 返回的原始数据
            
        Returns:
            List[GoldReserve]: 黄金储备对象列表
        """
        if not raw_data or raw_data.get("type") != "safe":
            return []
        
        reserves = []
        fetch_time = datetime.now()
        
        for item in raw_data.get("data", []):
            try:
                # 解析日期
                report_date = date.today()
                date_str = item.get("date")
                if date_str:
                    try:
                        report_date = datetime.strptime(date_str, "%Y-%m").date()
                    except ValueError:
                        pass
                
                reserves.append(GoldReserve(
                    country_code=item["country_code"],
                    country_name=item["country_name"],
                    amount_tonnes=float(item["amount"]),
                    percent_of_reserves=None,
                    report_date=report_date,
                    data_source="SAFE",
                    fetch_time=fetch_time,
                ))
            except Exception as e:
                logger.warning(f"Failed to parse SAFE item: {e}")
                continue
        
        return reserves
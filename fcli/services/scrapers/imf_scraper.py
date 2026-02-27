"""
IMF SDMX 3.0 API Gold Reserves Scraper
使用 IMF IRFCL (International Reserves and Foreign Currency Liquidity) 数据集
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import aiohttp

from fcli.core.config import config

logger = logging.getLogger(__name__)

# IMF SDMX 3.0 API配置
IMF_API_BASE = "https://api.imf.org/external/sdmx/3.0"

# 使用 International Liquidity (IL) 数据集获取黄金储备
# RGV_REVS = Reserve Assets > Gold > Reserve Assets (Value)
# FTO = Fine Troy Ounces (百万金衡盎司)
# M = Monthly (月度)
IL_DATAFLOW = "IMF.STA/IL"
GOLD_INDICATOR = "RGV_REVS"
GOLD_UNIT = "FTO"  # Fine Troy Ounces
GOLD_FREQ = "M"  # Monthly
# 主要黄金持有国ISO代码 (IMF格式) - 中文名称
GOLD_COUNTRY_CODES = {
    "USA": "美国",
    "DEU": "德国",
    "IMF": "国际货币基金组织",
    "ITA": "意大利",
    "FRA": "法国",
    "RUS": "俄罗斯",
    "CHN": "中国",
    "CHE": "瑞士",
    "JPN": "日本",
    "IND": "印度",
    "TUR": "土耳其",
    "NLD": "荷兰",
    "SAU": "沙特阿拉伯",
    "GBR": "英国",
    "LBN": "黎巴嫩",
    "KAZ": "哈萨克斯坦",
    "PRT": "葡萄牙",
    "UZB": "乌兹别克斯坦",
    "AUT": "奥地利",
    "SGP": "新加坡",
    "KOR": "韩国",
    "BRA": "巴西",
    "BEL": "比利时",
    "ARG": "阿根廷",
    "THA": "泰国",
    "VEN": "委内瑞拉",
    "MEX": "墨西哥",
    "SWE": "瑞典",
    "POL": "波兰",
    "AUS": "澳大利亚",
    "PHL": "菲律宾",
    "IDN": "印度尼西亚",
    "MYS": "马来西亚",
    "CAN": "加拿大",
    "ESP": "西班牙",
    "FIN": "芬兰",
    "NOR": "挪威",
    "DNK": "丹麦",
    "CZE": "捷克",
    "HUN": "匈牙利",
    "ROU": "罗马尼亚",
    "GRC": "希腊",
    "ISR": "以色列",
    "EGY": "埃及",
    "ZAF": "南非",
    "NGA": "尼日利亚",
    "VNM": "越南",
}


class IMFScraper:
    """IMF SDMX 3.0 API 黄金储备爬虫"""

    def __init__(self):
        self.api_key = self._get_api_key()
        self.headers = {
            "Accept": "application/json",
        }
        if self.api_key:
            self.headers["Ocp-Apim-Subscription-Key"] = self.api_key
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()

    def _get_api_key(self) -> Optional[str]:
        """获取IMF API密钥（可选）"""
        return config.api.imf_primary

    def _get_proxy(self) -> Optional[str]:
        """获取代理配置"""
        if config.proxy.enabled:
            return config.proxy.http
        return None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建带有代理支持的session"""
        async with self._session_lock:
            if self._session is None or self._session.closed:
                connector = aiohttp.TCPConnector(ssl=False)
                self._session = aiohttp.ClientSession(
                    connector=connector, trust_env=True
                )
            return self._session

    async def close(self):
        """关闭session"""
        if self._session and not self._session.closed:
            connector = self._session.connector
            await self._session.close()
            if connector and not connector.closed:
                await connector.close()
            self._session = None

    def _build_data_url(
        self,
        country_code: str,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
    ) -> str:
        """
        构建IMF SDMX 3.0数据查询URL

        使用 International Liquidity (IL) 数据集获取黄金储备
        示例: https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/IL/+/SGP.RGV_REVS.FTO.M

        Args:
            country_code: 国家ISO代码 (如 USA, CHN, SGP)
            start_period: 开始期间 (YYYY-MM 或 YYYY)
            end_period: 结束期间 (YYYY-MM 或 YYYY)

        Returns:
            完整的API URL
        """
        # key格式: {COUNTRY}.{INDICATOR}.{UNIT}.{FREQ}
        # 例如: SGP.RGV_REVS.FTO.M (新加坡, 黄金储备, 百万金衡盎司, 月度)
        key = f"{country_code}.{GOLD_INDICATOR}.{GOLD_UNIT}.{GOLD_FREQ}"

        url = f"{IMF_API_BASE}/data/dataflow/{IL_DATAFLOW}/+/{key}"

        # 使用 c[TIME_PERIOD] 参数格式
        params = []
        if start_period:
            params.append(f"c[TIME_PERIOD]=ge:{start_period}")
        if end_period:
            params.append(f"c[TIME_PERIOD]=le:{end_period}")

        if params:
            url += "?" + "&".join(params)

        return url

    async def fetch_gold_reserves(
        self,
        country_code: str,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
    ) -> dict:
        """
        获取指定国家的黄金储备数据

        Args:
            country_code: 国家ISO代码
            start_period: 开始期间
            end_period: 结束期间

        Returns:
            包含时间序列数据的字典 {period: value}
        """
        url = self._build_data_url(country_code, start_period, end_period)
        proxy = self._get_proxy()
        session = await self._get_session()

        timeout = aiohttp.ClientTimeout(total=60, connect=30)

        async with session.get(
            url, headers=self.headers, proxy=proxy, timeout=timeout
        ) as response:
            if response.status == 200:
                data = await response.json()
                return self._parse_response(data)
            else:
                text = await response.text()
                raise Exception(f"IMF API error: {response.status} - {text}")

        # Rate limiting: wait 0.3s between requests to avoid rate limiting
        await asyncio.sleep(0.3)

    def _parse_response(self, data: dict) -> dict:
        """
        解析IMF SDMX 3.0 JSON响应

        SDMX 3.0 JSON结构:
        {
          "data": {
            "dataSets": [{"series": {"0:0:0:0": {"observations": {"0": ["7072000", ...]}}}}],
            "structures": [{"dimensions": {"observation": [{"id": "TIME_PERIOD", "values": [...]}]}}]
          }
        }

        Returns:
            {period: gold_tonnes} 黄金吨数
        """
        result = {}

        try:
            # SDMX 3.0: data.dataSets 和 data.structures
            data_sets = data.get("data", {}).get("dataSets", [])
            structures = data.get("data", {}).get("structures", [])

            if not data_sets:
                logger.debug(f"No dataSets in response, keys: {list(data.keys())}")
                return result

            # 获取时间周期
            time_periods = []
            for structure in structures:
                dimensions = structure.get("dimensions", {})
                obs_dims = dimensions.get("observation", [])
                for dim in obs_dims:
                    if dim.get("id") == "TIME_PERIOD":
                        time_periods = [v.get("value") for v in dim.get("values", [])]
                        break

            if not time_periods:
                logger.debug("No TIME_PERIOD dimension found")
                return result

            # 提取观测值
            for data_set in data_sets:
                series = data_set.get("series", {})

                for series_key, series_data in series.items():
                    observations = series_data.get("observations", {})

                    for obs_idx, obs_value in observations.items():
                        if not obs_value:
                            continue

                        try:
                            # obs_value 格式: ["7072000", null, 0, null]
                            raw_value = (
                                obs_value[0]
                                if isinstance(obs_value, list)
                                else obs_value
                            )
                            if raw_value is None:
                                continue

                            raw_value = float(raw_value)

                            # 转换为吨数
                            # IMF FTO 单位是百万金衡盎司 (Millions of Fine Troy Ounces)
                            # 原始值已经是以千盎司为单位
                            # 1 金衡盎司 = 0.0311034768 公斤
                            # 转换: raw_value (千盎司) * 0.0311034768 / 1000 = 吨
                            # 转换: raw_value * 0.0311034768 / 1000 = 吨
                            troy_oz_to_kg = 0.0311034768  # 金衡盎司转公斤
                            gold_tonnes = raw_value * troy_oz_to_kg / 1000  # 转为吨

                            period_idx = int(obs_idx)
                            if period_idx < len(time_periods):
                                period_raw = time_periods[period_idx]
                                # 解析期间格式 (如 "2025-M01" -> "2025-01")
                                if "-M" in str(period_raw):
                                    period = period_raw.replace("-M", "-")
                                else:
                                    period = period_raw

                                if gold_tonnes > 0:
                                    result[period] = round(gold_tonnes, 2)

                        except (ValueError, TypeError, IndexError) as e:
                            continue

        except Exception as e:
            print(f"  Error parsing IMF response: {e}")

        return result

    async def get_latest_gold_reserve(self, country_code: str) -> Optional[dict]:
        """
        获取最新一个月的黄金储备

        Args:
            country_code: 国家ISO代码

        Returns:
            {"period": "2024-12", "value": 8133.5} 或 None
        """
        # 获取最近12个月的数据，取最新
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        start_period = start_date.strftime("%Y-%m")
        end_period = end_date.strftime("%Y-%m")

        data = await self.fetch_gold_reserves(
            country_code, start_period=start_period, end_period=end_period
        )

        if not data:
            return None

        # 取最新的一个月
        latest_period = max(data.keys())
        return {
            "period": latest_period,
            "value": data[latest_period],
            "country_code": country_code,
            "country_name": GOLD_COUNTRY_CODES.get(country_code, country_code),
        }

    async def get_gold_reserves_history(
        self, country_code: str, years: int = 10
    ) -> dict:
        """
        获取指定国家近N年的月度黄金储备历史数据
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)

        start_period = start_date.strftime("%Y-%m")
        end_period = end_date.strftime("%Y-%m")

        data = await self.fetch_gold_reserves(
            country_code, start_period=start_period, end_period=end_period
        )

        print(f"  {country_code}: fetched {len(data)} periods")
        if data:
            sample = list(data.items())[:3]
            print(f"    Sample: {sample}")

        return {
            "country_code": country_code,
            "country_name": GOLD_COUNTRY_CODES.get(country_code, country_code),
            "start_period": start_period,
            "end_period": end_period,
            "data": data,
        }

    async def batch_get_latest_reserves(
        self, country_codes: Optional[list[str]] = None
    ) -> list[dict]:
        """
        批量获取多国最新黄金储备

        Args:
            country_codes: 国家代码列表，默认为所有主要国家

        Returns:
            [{"country_code": "USA", "period": "2024-12", "value": 8133.5}, ...]
        """
        if country_codes is None:
            country_codes = list(GOLD_COUNTRY_CODES.keys())

        tasks = [self.get_latest_gold_reserve(code) for code in country_codes]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤成功结果
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error fetching {country_codes[i]}: {result}")
            elif result:
                valid_results.append(result)

        # 按储备量降序排序
        valid_results.sort(key=lambda x: x.get("value", 0), reverse=True)

        return valid_results

    async def batch_get_history(
        self, country_codes: Optional[list[str]] = None, years: int = 10
    ) -> list[dict]:
        """
        批量获取多国近N年月度黄金储备历史

        Args:
            country_codes: 国家代码列表
            years: 年数

        Returns:
            [{"country_code": "USA", "data": {...}}, ...]
        """
        if country_codes is None:
            country_codes = list(GOLD_COUNTRY_CODES.keys())

        tasks = [self.get_gold_reserves_history(code, years) for code in country_codes]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error fetching history for {country_codes[i]}: {result}")
            elif result and result.get("data"):
                valid_results.append(result)

        return valid_results


# 便捷函数
async def get_latest_gold(country_code: str) -> Optional[dict]:
    """获取单个国家最新黄金储备"""
    scraper = IMFScraper()
    try:
        return await scraper.get_latest_gold_reserve(country_code)
    finally:
        await scraper.close()


async def get_all_latest_gold() -> list[dict]:
    """获取所有主要国家最新黄金储备"""
    scraper = IMFScraper()
    try:
        return await scraper.batch_get_latest_reserves()
    finally:
        await scraper.close()


async def get_gold_history(country_code: str, years: int = 10) -> dict:
    """获取单个国家黄金储备历史"""
    scraper = IMFScraper()
    try:
        return await scraper.get_gold_reserves_history(country_code, years)
    finally:
        await scraper.close()


async def get_all_gold_history(years: int = 10) -> list[dict]:
    """获取所有主要国家黄金储备历史"""
    scraper = IMFScraper()
    try:
        return await scraper.batch_get_history(years=years)
    finally:
        await scraper.close()

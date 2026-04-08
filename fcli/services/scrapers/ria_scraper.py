"""
RIA Novosti 数据源爬虫 - 俄罗斯黄金储备数据
数据来源: ria.ru (РИА Новости) - 俄罗斯国家通讯社

通过搜索 RIA 新闻文章获取俄罗斯央行 (ЦБ РФ) 公布的黄金储备物理量数据。
CBR 官方 API/Web 仅提供美元价值数据，物理量数据由 RIA 从 CBR 获取后发布。

搜索端点: ria.ru/services/search/getmore/
关键词: золотой запас ЦБ

数据格式示例:
- "74,3 миллиона тройских унций" -> 74.3 百万金衡盎司
- "2329,65 тонны" -> 2329.65 吨
"""

import re
from datetime import date
from typing import Any

from bs4 import BeautifulSoup

from ...core.models.gold import GoldReserve
from ...infra.http_client import HttpClient
from ...utils.logger import get_logger
from ...utils.time_util import utcnow
from .base import BaseScraper

logger = get_logger("fcli.scraper.ria")

TROY_OZ_TO_GRAMS = 31.1034768
TROY_OZ_TO_TONNES = TROY_OZ_TO_GRAMS / 1_000_000
MILLION_TROY_OZ_TO_TONNES = TROY_OZ_TO_TONNES * 1_000_000

SEARCH_URL = "https://ria.ru/services/search/getmore/"
SEARCH_QUERY = "золотой запас ЦБ"

GOLD_KEYWORDS = re.compile(r"золот[оы][ей]?\s*(?:запас|резерв)", re.IGNORECASE)

PATTERN_MLN_OZ = re.compile(
    r"(\d+[\.,]\d+)\s*(?:млн|миллиона?)\s*(?:тройских\s*)?унций",
    re.IGNORECASE,
)
PATTERN_TONNES = re.compile(
    r"(\d+[\.,]?\d*)\s*(?:тысяч[иа]?\s*)?тонн",
    re.IGNORECASE,
)
PATTERN_THOUSAND_TONNES = re.compile(
    r"(\d+[\.,]\d+)\s*тысяч[иа]?\s*тонн",
    re.IGNORECASE,
)

RU_MONTH_MAP = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}

RU_PREP_MONTH_MAP = {
    "январе": 1,
    "феврале": 2,
    "марте": 3,
    "апреле": 4,
    "мае": 5,
    "июне": 6,
    "июле": 7,
    "августе": 8,
    "сентябре": 9,
    "октябре": 10,
    "ноябре": 11,
    "декабре": 12,
}


def _ru_to_float(s: str) -> float:
    return float(s.replace(",", "."))


def _parse_ru_date(text: str) -> date | None:
    m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", text)
    if not m:
        return None
    day = int(m.group(1))
    month_str = m.group(2).lower()
    year = int(m.group(3))
    month = RU_MONTH_MAP.get(month_str)
    if not month:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


class RIAScraper(BaseScraper[GoldReserve]):
    """RIA Novosti scraper for Russian gold reserve physical volume data."""

    def __init__(self, http_client: HttpClient):
        super().__init__()
        self._http_client = http_client
        self._source_name = "RIA"

    @property
    def source_name(self) -> str:
        return self._source_name

    async def fetch(self) -> Any:
        article_url = await self._find_gold_article()
        if not article_url:
            logger.warning("No relevant gold reserve article found on RIA")
            return None

        logger.info("Fetching RIA article: %s", article_url)
        html = await self._http_client.fetch(article_url, text_mode=True)
        if not html:
            logger.warning("Failed to fetch RIA article content")
            return None

        return {
            "type": "ria_article",
            "url": article_url,
            "html": html,
        }

    async def _find_gold_article(self, max_pages: int = 3) -> str | None:
        for page in range(max_pages):
            offset = page * 20
            params = {
                "query": SEARCH_QUERY,
                "type": "article",
                "sort": "dt",
                "offset": str(offset),
                "limit": "20",
            }
            logger.debug("RIA search page %d: offset=%d", page + 1, offset)
            html = await self._http_client.fetch(SEARCH_URL, params=params, text_mode=True)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            links = soup.select("a.list-item__title")
            if not links:
                links = soup.find_all("a", class_=re.compile(r"list-item__title"))

            for link in links:
                title = link.get_text(strip=True)
                if GOLD_KEYWORDS.search(title):
                    href = link.get("href", "")
                    if href and href.startswith("http"):
                        return href

            if not links:
                break

        return None

    def parse(self, raw_data: Any) -> list[GoldReserve]:
        if not raw_data or raw_data.get("type") != "ria_article":
            return []

        html = raw_data.get("html", "")
        article_url = raw_data.get("url", "")
        article_date = self._extract_date_from_url(article_url)

        soup = BeautifulSoup(html, "html.parser")

        sources = []
        for tag in soup.find_all("meta", attrs={"name": "description"}):
            content = tag.get("content", "")
            if content:
                sources.append(content)

        title_tag = soup.find("title")
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            title_text = re.sub(r"\s*-\s*РИА Новости.*$", "", title_text)
            sources.append(title_text)

        page_title_m = re.search(r"'page_title'\s*:\s*'([^']+)'", html)
        if page_title_m:
            sources.append(page_title_m.group(1))

        article_body = soup.find("div", class_=re.compile(r"article__body"))
        if article_body:
            body_text = article_body.get_text(separator=" ", strip=True)
            if len(body_text) > 50:
                sources.append(body_text)

        desc_text = sources[0] if sources else ""
        report_date = self._extract_report_date(desc_text, article_date)

        amount_tonnes = None
        matched_text = ""
        for text in sources:
            amount_tonnes = self._extract_tonnes(text)
            if amount_tonnes is not None:
                matched_text = text[:120]
                logger.debug("Extracted from: %s", matched_text)
                break

        if amount_tonnes is None:
            logger.warning("Could not extract gold volume from RIA article: %s", article_url)
            logger.debug("Tried sources: %s", [s[:100] for s in sources])
            return []

        logger.info(
            "RIA parsed: RUS gold reserves = %.2f tonnes (date: %s)",
            amount_tonnes,
            report_date,
        )

        return [
            GoldReserve(
                country_code="RUS",
                country_name="俄罗斯",
                amount_tonnes=round(amount_tonnes, 2),
                report_date=report_date,
                data_source="RIA",
                fetch_time=utcnow(),
            )
        ]

    def _extract_tonnes(self, text: str) -> float | None:
        m = PATTERN_THOUSAND_TONNES.search(text)
        if m:
            return _ru_to_float(m.group(1)) * 1000

        m = PATTERN_TONNES.search(text)
        if m:
            return _ru_to_float(m.group(1))

        m = PATTERN_MLN_OZ.search(text)
        if m:
            return _ru_to_float(m.group(1)) * MILLION_TROY_OZ_TO_TONNES

        return None

    def _extract_date_from_url(self, url: str) -> date:
        m = re.search(r"ria\.ru/(\d{4})(\d{2})(\d{2})/", url)
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass
        return date.today()

    def _extract_report_date(self, text: str, article_date: date) -> date:
        for month_name, month_num in RU_PREP_MONTH_MAP.items():
            if month_name in text.lower():
                year = article_date.year
                if month_num > article_date.month:
                    year -= 1
                try:
                    return date(year, month_num, 1)
                except ValueError:
                    pass
        if article_date.month == 1:
            return date(article_date.year - 1, 12, 1)
        return date(article_date.year, article_date.month - 1, 1)

    async def get_russia_latest(self) -> GoldReserve | None:
        raw = await self.fetch()
        if not raw:
            return None
        records = self.parse(raw)
        return records[0] if records else None

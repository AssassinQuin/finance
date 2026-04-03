import re
from datetime import datetime, time
from zoneinfo import ZoneInfo

from fcli.core.config import config
from fcli.core.models.base import Market

MARKET_TIMEZONES: dict[Market, ZoneInfo] = {
    Market.CN: ZoneInfo("Asia/Shanghai"),
    Market.HK: ZoneInfo("Asia/Hong_Kong"),
    Market.US: ZoneInfo("America/New_York"),
    Market.GLOBAL: ZoneInfo("UTC"),
}


def utcnow() -> datetime:
    return datetime.utcnow()


def now_for_market(market: Market) -> datetime:
    tz = MARKET_TIMEZONES.get(market, ZoneInfo("UTC"))
    return datetime.now(tz).replace(tzinfo=None)


def normalize_time(time_str: str) -> str:
    """
    Normalize time string to unified format: YYYY-MM-DD HH:mm
    """
    if not time_str or time_str in ["Parse Error", "N/A", ""]:
        return "-"

    time_str = time_str.replace("/", "-").strip()

    match = re.match(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})(?::\d{2})?", time_str)
    if match:
        return f"{match.group(1)} {match.group(2)}"

    match = re.match(r"^(\d{4}-\d{2}-\d{2})$", time_str)
    if match:
        return f"{match.group(1)} 00:00"

    match = re.match(r"^(\d{2}:\d{2})(?::\d{2})?$", time_str)
    if match:
        today = datetime.now().strftime("%Y-%m-%d")
        return f"{today} {match.group(1)}"

    return time_str


def _parse_time(time_str: str) -> time:
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))


def is_trading_hours(market: Market, check_time: datetime | None = None) -> bool:
    if check_time is None:
        check_time = now_for_market(market)

    current_time = check_time.time()
    weekday = check_time.weekday()

    if weekday >= 5:
        return False

    th = config.trading_hours

    if market == Market.CN:
        morning_start = _parse_time(th.cn_morning_start)
        morning_end = _parse_time(th.cn_morning_end)
        afternoon_start = _parse_time(th.cn_afternoon_start)
        afternoon_end = _parse_time(th.cn_afternoon_end)

        return (morning_start <= current_time <= morning_end) or (afternoon_start <= current_time <= afternoon_end)

    elif market == Market.HK:
        morning_start = _parse_time(th.hk_morning_start)
        morning_end = _parse_time(th.hk_morning_end)
        afternoon_start = _parse_time(th.hk_afternoon_start)
        afternoon_end = _parse_time(th.hk_afternoon_end)

        return (morning_start <= current_time <= morning_end) or (afternoon_start <= current_time <= afternoon_end)

    elif market == Market.US:
        start = _parse_time(th.us_pre_market_start)
        end = _parse_time(th.us_pre_market_end)

        if start > end:
            return current_time >= start or current_time <= end
        else:
            return start <= current_time <= end

    elif market == Market.GLOBAL:
        return weekday < 5

    return False

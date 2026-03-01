from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path
from typing import List, Optional


class DatabaseSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "fcli"
    pool_min: int = 2
    pool_max: int = 10

    model_config = SettingsConfigDict(env_prefix="FCLI_DB_", env_file=".env", env_file_encoding="utf-8", extra="ignore")


class TradingHoursSettings(BaseSettings):
    cn_morning_start: str = Field(default="09:30")
    cn_morning_end: str = Field(default="11:30")
    cn_afternoon_start: str = Field(default="13:00")
    cn_afternoon_end: str = Field(default="15:00")
    hk_morning_start: str = Field(default="09:30")
    hk_morning_end: str = Field(default="12:00")
    hk_afternoon_start: str = Field(default="13:00")
    hk_afternoon_end: str = Field(default="16:00")
    us_pre_market_start: str = Field(default="21:30")
    us_pre_market_end: str = Field(default="04:00")

    model_config = SettingsConfigDict(
        env_prefix="FCLI_TRADING_HOURS_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class CacheSettings(BaseSettings):
    search_ttl: int = Field(default=86400)
    quote_ttl: int = Field(default=300)
    quote_ttl_trading: int = Field(default=30)
    forex_ttl: int = Field(default=3600)
    gold_ttl: int = Field(default=86400)
    gpr_ttl: int = Field(default=86400)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_CACHE_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class RedisSettings(BaseSettings):
    """Redis 缓存配置"""

    enabled: bool = Field(default=False, description="是否启用 Redis 缓存")
    host: str = Field(default="127.0.0.1", description="Redis 主机地址")
    port: int = Field(default=6379, description="Redis 端口")
    password: str = Field(default="", description="Redis 密码")
    db: int = Field(default=0, description="Redis 数据库编号")
    prefix: str = Field(default="fcli:", description="缓存 key 前缀")
    pool_size: int = Field(default=10, description="连接池大小")

    model_config = SettingsConfigDict(
        env_prefix="FCLI_REDIS_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class HttpSettings(BaseSettings):
    """HTTP 请求配置"""

    total_timeout: int = Field(default=30, description="请求总超时时间(秒)")
    connect_timeout: int = Field(default=10, description="连接超时时间(秒)")
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: float = Field(default=1.0, description="重试延迟(秒)")
    max_concurrent: int = Field(default=10, description="最大并发请求数")

    model_config = SettingsConfigDict(
        env_prefix="FCLI_HTTP_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class DisplaySettings(BaseSettings):
    """展示层配置"""

    market_map: dict = Field(
        default={
            "CN": "沪深",
            "HK": "港股",
            "US": "美股",
            "FUND": "基金",
            "GLOBAL": "全球",
            "FOREX": "外汇",
            "BOND": "债券",
        }
    )
    type_map: dict = Field(
        default={
            "STOCK": "股票",
            "FUND": "基金",
            "INDEX": "指数",
            "FOREX": "外汇",
            "BOND": "债券",
        }
    )
    type_color: dict = Field(
        default={
            "STOCK": "yellow",
            "FUND": "magenta",
            "INDEX": "blue",
            "FOREX": "cyan",
            "BOND": "white",
        }
    )

    model_config = SettingsConfigDict(
        env_prefix="FCLI_DISPLAY_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class ProxySettings(BaseSettings):
    """代理配置"""

    http: str = Field(default="")
    https: str = Field(default="")
    enabled: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_PROXY_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class ApiKeySettings(BaseSettings):
    """API Key 配置"""

    fred: str = Field(default="")
    imf_primary: str = Field(default="")
    imf_secondary: str = Field(default="")

    model_config = SettingsConfigDict(
        env_prefix="FCLI_API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class GoldSettings(BaseSettings):
    """黄金相关配置"""

    price_usd_per_ounce: float = Field(default=2300.0, description="黄金价格(USD/盎司)")
    wan_oz_to_tonne: float = Field(default=0.311035, description="万盎司转换为吨的系数")

    model_config = SettingsConfigDict(
        env_prefix="FCLI_GOLD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class SourceSettings(BaseSettings):
    quote_priority: List[str] = Field(default=["eastmoney", "sina", "yahoo"])
    forex_priority: List[str] = Field(default=["frankfurter", "exchangerate"])
    gold_priority: List[str] = Field(default=["fred", "imf"])
    fallback_enabled: bool = True

    model_config = SettingsConfigDict(
        env_prefix="FCLI_SOURCE_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


# Package root directory
PACKAGE_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    data_dir: Path = Field(default=PACKAGE_ROOT / "data")
    timeout: int = 10
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    trading_hours: TradingHoursSettings = Field(default_factory=TradingHoursSettings)
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    api: ApiKeySettings = Field(default_factory=ApiKeySettings)
    gold: GoldSettings = Field(default_factory=GoldSettings)
    source: SourceSettings = Field(default_factory=SourceSettings)
    http: HttpSettings = Field(default_factory=HttpSettings)
    display: DisplaySettings = Field(default_factory=DisplaySettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    model_config = SettingsConfigDict(
        env_prefix="FCLI_", env_file=".env", env_file_encoding="utf-8", extra="ignore", env_nested_delimiter="__"
    )


config = Settings()
settings = config

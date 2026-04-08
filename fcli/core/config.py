"""FCLI 配置模块

配置来源: .env 文件 + 环境变量
所有默认值硬编码在 Field(default=...) 中。

环境变量命名规则:
  FCLI__{SECTION}__{FIELD}  (使用双下划线分隔)
  例如: FCLI__DB__HOST=127.0.0.1
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ============================================================
# 项目目录和配置文件路径（固定使用项目目录）
# ============================================================

# 项目根目录 (fcli/core 的 parent.parent = 项目根目录)
PACKAGE_ROOT = Path(__file__).parent.parent.parent

# 配置文件路径（始终使用项目目录）
PROJECT_ENV_PATH = str(PACKAGE_ROOT / ".env")


# ============================================================
# 各模块配置类
# ============================================================


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration."""

    host: str = "127.0.0.1"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    database: str = "fcli"
    pool_min: int = 2
    pool_max: int = 10

    model_config = SettingsConfigDict(env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore")


class TradingHoursSettings(BaseSettings):
    """交易时间配置"""

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
    us_regular_start: str = Field(default="21:30")
    us_regular_end: str = Field(default="04:00")

    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class CacheSettings(BaseSettings):
    """缓存配置"""

    default_ttl: int = Field(default=300)
    search_ttl: int = Field(default=86400)
    stock_trading_ttl: int = Field(default=30)
    stock_non_trading_ttl: int = Field(default=300)
    fund_trading_ttl: int = Field(default=60)
    fund_non_trading_ttl: int = Field(default=300)
    index_trading_ttl: int = Field(default=30)
    index_non_trading_ttl: int = Field(default=300)
    forex_ttl: int = Field(default=3600)
    bond_ttl: int = Field(default=7200)
    gold_ttl: int = Field(default=86400)
    gpr_ttl: int = Field(default=86400)
    quote_short_ttl: int = Field(default=300)
    quote_medium_ttl: int = Field(default=600)
    quote_long_ttl: int = Field(default=3600)
    quote_history_days: int = Field(default=30)
    key_prefix: str = Field(default="fcli:")
    pg_cleanup_interval: int = Field(default=300)
    pg_health_check_interval: int = Field(default=60)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class HttpSettings(BaseSettings):
    """HTTP 请求配置"""

    total_timeout: int = Field(default=30)
    connect_timeout: int = Field(default=10)
    max_retries: int = Field(default=3)
    retry_delay: float = Field(default=1.0)
    max_concurrent: int = Field(default=10)
    max_connections: int = Field(default=100)
    max_per_host: int = Field(default=10)
    user_agent: str = Field(
        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
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
        default={"STOCK": "股票", "FUND": "基金", "INDEX": "指数", "FOREX": "外汇", "BOND": "债券", "GOLD": "黄金"}
    )
    type_color: dict = Field(
        default={
            "STOCK": "yellow",
            "FUND": "magenta",
            "INDEX": "blue",
            "FOREX": "cyan",
            "BOND": "white",
            "GOLD": "gold3",
        }
    )

    model_config = SettingsConfigDict(env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore")


class ProxySettings(BaseSettings):
    """代理配置"""

    http: str | None = Field(default=None)
    https: str | None = Field(default=None)
    enabled: bool | None = Field(default=None)

    model_config = SettingsConfigDict(env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore")


class ApiKeySettings(BaseSettings):
    """API密钥配置"""

    fred: str | None = Field(default=None)
    imf_primary: str | None = Field(default=None)
    imf_secondary: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class GoldSettings(BaseSettings):
    """黄金相关配置"""

    price_usd_per_ounce: float = Field(default=2300.0)
    wan_oz_to_tonne: float = Field(default=0.311035)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


# ============================================================
# 数据源详细配置类
# ============================================================


class SinaDataSource(BaseSettings):
    """新浪数据源配置"""

    # 行情API
    cn_quote_url: str = Field(default="https://hq.sinajs.cn/list={code}", description="A股行情URL模板")
    hk_quote_url: str = Field(default="https://hq.sinajs.cn/list={code}", description="港股行情URL模板")
    us_quote_url: str = Field(default="https://hq.sinajs.cn/list={code}", description="美股行情URL模板")
    global_quote_url: str = Field(default="https://hq.sinajs.cn/list={code}", description="全球指数URL模板")

    # 代码前缀
    cn_sh_prefix: str = Field(default="sh", description="上海交易所前缀")
    cn_sz_prefix: str = Field(default="sz", description="深圳交易所前缀")
    hk_prefix: str = Field(default="rt_hk", description="港股前缀")
    us_prefix: str = Field(default="gb_", description="美股前缀")

    referer: str = Field(default="https://finance.sina.com.cn", description="Sina Referer header")

    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class EastmoneyDataSource(BaseSettings):
    """东方财富数据源配置"""

    # 行情API
    quote_api_url: str = Field(default="https://push2.eastmoney.com/api/qt/stock/get", description="单只股票行情API")
    batch_quote_url: str = Field(default="https://push2.eastmoney.com/api/qt/ulist.np/get", description="批量行情API")
    global_batch_url: str = Field(
        default="https://push2.eastmoney.com/api/qt/ulist.np/get", description="全球指数批量API"
    )

    # 市场代码映射
    cn_sh_market_code: int = Field(default=1, description="上海市场代码")
    cn_sz_market_code: int = Field(default=0, description="深圳市场代码")
    hk_market_code: int = Field(default=116, description="港股市场代码")
    us_market_code: int = Field(default=105, description="美股市场代码")
    global_market_code: int = Field(default=100, description="全球市场代码")

    SINGLE_FIELDS: ClassVar[str] = "f43,f44,f45,f46,f47,f48,f57,f58,f60,f107"
    BATCH_FIELDS: ClassVar[str] = "f1,f2,f3,f4,f12,f14,f15,f16,f17,f18,f43,f47,f48"
    PRICE_DIVISOR: ClassVar[int] = 100

    F_SINGLE_PRICE: ClassVar[str] = "f43"
    F_SINGLE_PREV_CLOSE: ClassVar[str] = "f60"
    F_SINGLE_HIGH: ClassVar[str] = "f44"
    F_SINGLE_LOW: ClassVar[str] = "f45"
    F_SINGLE_VOLUME: ClassVar[str] = "f47"

    F_BATCH_CODE: ClassVar[str] = "f12"
    F_BATCH_NAME: ClassVar[str] = "f14"
    F_BATCH_PRICE: ClassVar[str] = "f2"
    F_BATCH_CHANGE: ClassVar[str] = "f3"
    F_BATCH_HIGH: ClassVar[str] = "f17"
    F_BATCH_LOW: ClassVar[str] = "f18"
    F_BATCH_VOLUME: ClassVar[str] = "f47"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class FundDataSource(BaseSettings):
    """基金数据源配置"""

    # 天天基金
    gz_api_url: str = Field(default="https://fundgz.1234567.com.cn/js/{code}.js", description="基金估值API")
    detail_api_url: str = Field(default="https://fund.eastmoney.com/pingzxinfo_{code}.html", description="基金详情页")

    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class ForexDataSource(BaseSettings):
    """汇率数据源配置"""

    # Frankfurter API
    frankfurter_base_url: str = Field(default="https://api.frankfurter.app", description="Frankfurter API 基础URL")
    frankfurter_latest_url: str = Field(default="https://api.frankfurter.app/latest", description="最新汇率API")
    frankfurter_historical_url: str = Field(default="https://api.frankfurter.app/{date}", description="历史汇率API模板")

    # ExchangeRate API
    exchangerate_base_url: str = Field(default="https://api.exchangerate.host", description="ExchangeRate API 基础URL")

    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_latest_url(self, base: str, symbols: list[str] | None = None) -> str:
        """获取最新汇率URL"""
        url = f"{self.frankfurter_base_url}/latest?from={base}"
        if symbols:
            url += f"&to={','.join(symbols)}"
        return url

    def get_historical_url(self, date: str, base: str, symbols: list[str] | None = None) -> str:
        """获取历史汇率URL"""
        url = f"{self.frankfurter_base_url}/{date}?from={base}"
        if symbols:
            url += f"&to={','.join(symbols)}"
        return url


class GoldDataSource(BaseSettings):
    """黄金数据源配置"""

    # FRED API
    fred_base_url: str = Field(default="https://api.stlouisfed.org/fred", description="FRED API 基础URL")
    fred_series_url: str = Field(
        default="https://api.stlouisfed.org/fred/series/observations", description="FRED 序列数据API"
    )

    # IMF API
    imf_base_url: str = Field(default="https://dataservices.imf.org/REST/SDMX_JSON.svc", description="IMF API 基础URL")
    imf_timeout_total: int = Field(default=60, description="IMF 请求总超时(秒)")
    imf_timeout_connect: int = Field(default=30, description="IMF 连接超时(秒)")
    imf_batch_concurrency: int = Field(default=5, description="IMF 批量请求并发数")

    # 世界黄金协会
    wgc_base_url: str = Field(default="https://www.gold.org", description="世界黄金协会网站")
    wgc_lookback_years: int = Field(default=3, description="WGC 报告回溯年数")

    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class GPRDataSource(BaseSettings):
    """地缘政治风险指数数据源配置"""

    # GPR Index 网站
    gpr_base_url: str = Field(default="https://www.matteoiacoviello.com", description="GPR Index 网站基础URL")
    gpr_data_url: str = Field(
        default="https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls", description="GPR 数据文件URL"
    )
    stale_days: int = Field(default=7, description="GPR 数据过期天数")
    risk_moderate_threshold: float = Field(default=100.0, description="中等风险阈值")
    risk_high_threshold: float = Field(default=150.0, description="高风险阈值")
    risk_extreme_threshold: float = Field(default=250.0, description="极高风险阈值")

    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DataSourceConfig(BaseSettings):
    """统一数据源配置"""

    sina: SinaDataSource = Field(default_factory=SinaDataSource)
    eastmoney: EastmoneyDataSource = Field(default_factory=EastmoneyDataSource)
    fund: FundDataSource = Field(default_factory=FundDataSource)
    forex: ForexDataSource = Field(default_factory=ForexDataSource)
    gold: GoldDataSource = Field(default_factory=GoldDataSource)
    gpr: GPRDataSource = Field(default_factory=GPRDataSource)

    # 数据源优先级
    quote_priority: list[str] = Field(default=["eastmoney", "sina", "yahoo"], description="行情数据源优先级")
    forex_priority: list[str] = Field(default=["frankfurter", "exchangerate"], description="汇率数据源优先级")
    gold_priority: list[str] = Field(default=["fred", "imf"], description="黄金数据源优先级")

    # 降级策略
    fallback_enabled: bool = Field(default=True, description="是否启用数据源降级")

    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


# ============================================================
# 主配置类
# ============================================================


class Settings(BaseSettings):
    log_level: str = Field(default="INFO", description="Logging level: DEBUG/INFO/WARNING/ERROR")
    data_dir: Path = Field(default=PACKAGE_ROOT / "data")
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    trading_hours: TradingHoursSettings = Field(default_factory=TradingHoursSettings)
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    api: ApiKeySettings = Field(default_factory=ApiKeySettings)
    gold: GoldSettings = Field(default_factory=GoldSettings)
    datasource: DataSourceConfig = Field(default_factory=DataSourceConfig)
    http: HttpSettings = Field(default_factory=HttpSettings)
    display: DisplaySettings = Field(default_factory=DisplaySettings)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_",
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )


# ============================================================
# 初始化配置
# ============================================================

config = Settings()


__all__ = [
    "config",
    "Settings",
    "PACKAGE_ROOT",
    "PROJECT_ENV_PATH",
    "DataSourceConfig",
    "SinaDataSource",
    "EastmoneyDataSource",
    "FundDataSource",
    "ForexDataSource",
    "GoldDataSource",
    "GPRDataSource",
]

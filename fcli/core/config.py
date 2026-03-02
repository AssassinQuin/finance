"""FCLI 配置模块

所有配置文件（.env, config.toml）固定使用项目目录，
无论命令从哪个目录执行。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path
from typing import List, Dict, Any
import os

# ============================================================
# 项目目录和配置文件路径（固定使用项目目录）
# ============================================================

# 项目根目录 (fcli/core 的 parent.parent = 项目根目录)
PACKAGE_ROOT = Path(__file__).parent.parent.parent

# 配置文件路径（始终使用项目目录）
PROJECT_ENV_PATH = str(PACKAGE_ROOT / ".env")
PROJECT_CONFIG_PATH = PACKAGE_ROOT / "config.toml"

# 尝试导入 tomllib (Python 3.11+) 或 tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


# ============================================================
# 各模块配置类
# ============================================================


class DatabaseSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "fcli"
    pool_min: int = 2
    pool_max: int = 10

    model_config = SettingsConfigDict(
        env_prefix="FCLI_DB_", env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore"
    )


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
        env_prefix="FCLI_TRADING_HOURS_", env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore"
    )


class CacheSettings(BaseSettings):
    """缓存配置 - 支持基于资产类型的差异化TTL"""

    # 通用TTL
    default_ttl: int = Field(default=300, description="默认缓存TTL")
    search_ttl: int = Field(default=86400, description="搜索结果缓存TTL")

    # 股票TTL
    stock_trading_ttl: int = Field(default=30, description="股票交易时段TTL")
    stock_non_trading_ttl: int = Field(default=300, description="股票非交易时段TTL")

    # 基金TTL
    fund_trading_ttl: int = Field(default=60, description="基金交易时段TTL")
    fund_non_trading_ttl: int = Field(default=300, description="基金非交易时段TTL")

    # 指数TTL
    index_trading_ttl: int = Field(default=30, description="指数交易时段TTL")
    index_non_trading_ttl: int = Field(default=300, description="指数非交易时段TTL")

    # 其他资产TTL
    forex_ttl: int = Field(default=3600, description="外汇TTL (1小时)")
    bond_ttl: int = Field(default=7200, description="债券TTL (2小时)")
    gold_ttl: int = Field(default=86400, description="黄金TTL (1天)")
    gpr_ttl: int = Field(default=86400, description="地缘风险TTL (1天)")

    # 兼容旧配置
    quote_ttl: int = Field(default=300, description="[兼容] 非交易时段TTL")
    quote_ttl_trading: int = Field(default=30, description="[兼容] 交易时段TTL")
    quote_short_ttl: int = Field(default=300, description="[兼容] 短TTL")
    quote_long_ttl: int = Field(default=3600, description="[兼容] 长TTL")

    model_config = SettingsConfigDict(
        env_prefix="FCLI_CACHE_", env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore"
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
        env_prefix="FCLI_REDIS_", env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore"
    )


class HttpSettings(BaseSettings):
    """HTTP 请求配置"""

    total_timeout: int = Field(default=30, description="请求总超时时间(秒)")
    connect_timeout: int = Field(default=10, description="连接超时时间(秒)")
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: float = Field(default=1.0, description="重试延迟(秒)")
    max_concurrent: int = Field(default=10, description="最大并发请求数")

    model_config = SettingsConfigDict(
        env_prefix="FCLI_HTTP_", env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore"
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
        env_prefix="FCLI_DISPLAY_", env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore"
    )


class ProxySettings(BaseSettings):
    """代理配置"""

    http: str = Field(default="")
    https: str = Field(default="")
    enabled: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_PROXY_", env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore"
    )


class ApiKeySettings(BaseSettings):
    """API Key 配置"""

    fred: str = Field(default="")
    imf_primary: str = Field(default="")
    imf_secondary: str = Field(default="")

    model_config = SettingsConfigDict(
        env_prefix="FCLI_API_",
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class GoldSettings(BaseSettings):
    """黄金相关配置"""

    price_usd_per_ounce: float = Field(default=2300.0, description="黄金价格(USD/盎司)")
    wan_oz_to_tonne: float = Field(default=0.311035, description="万盎司转换为吨的系数")

    model_config = SettingsConfigDict(
        env_prefix="FCLI_GOLD_",
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class SourceSettings(BaseSettings):
    """数据源配置"""

    quote_priority: List[str] = Field(default=["eastmoney", "sina", "yahoo"])
    forex_priority: List[str] = Field(default=["frankfurter", "exchangerate"])
    gold_priority: List[str] = Field(default=["fred", "imf"])
    fallback_enabled: bool = True

    model_config = SettingsConfigDict(
        env_prefix="FCLI_SOURCE_", env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore"
    )


class DataSourceSettings(BaseSettings):
    """数据源URL配置 - 消除硬编码"""

    # 新浪
    sina_base_url: str = Field(default="https://hq.sinajs.cn")
    sina_cn_quote: str = Field(default="https://hq.sinajs.cn/list={code}")

    # 东方财富
    eastmoney_quote_api: str = Field(default="https://push2.eastmoney.com/api/qt/stock/get")
    eastmoney_batch_api: str = Field(default="https://push2.eastmoney.com/api/qt/ulist.np/get")

    # 天天基金
    fund_gz_api: str = Field(default="https://fundgz.1234567.com.cn/js/{code}.js")

    # 汇率
    frankfurter_base: str = Field(default="https://api.frankfurter.app")
    exchangerate_base: str = Field(default="https://api.exchangerate.host")

    # 黄金
    fred_base_url: str = Field(default="https://api.stlouisfed.org/fred")
    imf_base_url: str = Field(default="https://dataservices.imf.org/REST/SDMX_JSON.svc")

    # GPR
    gpr_data_url: str = Field(default="https://www.matteoiacoviello.com/gpr_files/data_gpr_final.xls")

    model_config = SettingsConfigDict(
        env_prefix="FCLI_DATASOURCE_", env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore"
    )


# ============================================================
# TOML 配置加载（固定使用项目目录）
# ============================================================


def _load_toml_config() -> Dict[str, Any]:
    """加载项目目录下的 config.toml

    Returns:
        配置字典，如果加载失败返回空字典
    """
    if tomllib is None:
        return {}

    if not PROJECT_CONFIG_PATH.exists():
        return {}

    try:
        with open(PROJECT_CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        import warnings

        warnings.warn(f"Failed to load config from {PROJECT_CONFIG_PATH}: {e}")
        return {}


def _merge_toml_to_settings(toml_config: Dict[str, Any], settings: "Settings") -> None:
    """将 TOML 配置合并到 Settings 实例

    优先级: 环境变量 > TOML 配置 > 默认值
    """
    if not toml_config:
        return

    # 映射 TOML section 到 Settings 属性
    section_mapping = {
        "cache": "cache",
        "datasource": "datasource",
        "source": "source",
        "http": "http",
        "redis": "redis",
        "trading_hours": "trading_hours",
        "gold": "gold",
        "display": "display",
        "proxy": "proxy",
        "db": "db",
    }

    for section, attr_name in section_mapping.items():
        if section in toml_config:
            section_config = toml_config[section]
            if hasattr(settings, attr_name):
                sub_settings = getattr(settings, attr_name)
                for key, value in section_config.items():
                    if hasattr(sub_settings, key):
                        # 只有当环境变量没有设置时才使用 TOML 值
                        env_key = f"FCLI_{section.upper()}_{key.upper()}"
                        if env_key not in os.environ:
                            setattr(sub_settings, key, value)


# ============================================================
# 主配置类
# ============================================================


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
    datasource: DataSourceSettings = Field(default_factory=DataSourceSettings)
    http: HttpSettings = Field(default_factory=HttpSettings)
    display: DisplaySettings = Field(default_factory=DisplaySettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)

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

# 创建配置实例
config = Settings()

# 加载并合并 TOML 配置
_toml_config = _load_toml_config()
_merge_toml_to_settings(_toml_config, config)

# 别名
settings = config


# 导出公共接口
__all__ = [
    "config",
    "settings",
    "Settings",
    "PACKAGE_ROOT",
    "PROJECT_ENV_PATH",
    "PROJECT_CONFIG_PATH",
]

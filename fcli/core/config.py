"""FCLI 配置模块

所有配置文件（.env, config.toml）固定使用项目目录，
无论命令从哪个目录执行。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path
from typing import List, Dict, Any, Optional
from typing import TYPE_CHECKING
import os

if TYPE_CHECKING:
    from .models.base import Market

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
    """PostgreSQL database configuration."""

    host: str = "127.0.0.1"
    port: int = 5432  # PostgreSQL default port
    user: str = "postgres"
    password: str = ""
    database: str = "fcli"
    pool_min: int = 2
    pool_max: int = 10

    model_config = SettingsConfigDict(
        env_prefix="FCLI_DB_", env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore"
    )


class TradingHoursSettings(BaseSettings):
    """交易时间配置 - 所有默认值来自 config.toml"""

    cn_morning_start: Optional[str] = Field(default=None)
    cn_morning_end: Optional[str] = Field(default=None)
    cn_afternoon_start: Optional[str] = Field(default=None)
    cn_afternoon_end: Optional[str] = Field(default=None)
    hk_morning_start: Optional[str] = Field(default=None)
    hk_morning_end: Optional[str] = Field(default=None)
    hk_afternoon_start: Optional[str] = Field(default=None)
    hk_afternoon_end: Optional[str] = Field(default=None)
    us_pre_market_start: Optional[str] = Field(default=None)
    us_pre_market_end: Optional[str] = Field(default=None)
    us_regular_start: Optional[str] = Field(default=None)
    us_regular_end: Optional[str] = Field(default=None)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_TRADING_HOURS_",
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class CacheSettings(BaseSettings):
    """缓存配置 - 所有默认值来自 config.toml"""

    default_ttl: Optional[int] = Field(default=None)
    search_ttl: Optional[int] = Field(default=None)
    stock_trading_ttl: Optional[int] = Field(default=None)
    stock_non_trading_ttl: Optional[int] = Field(default=None)
    fund_trading_ttl: Optional[int] = Field(default=None)
    fund_non_trading_ttl: Optional[int] = Field(default=None)
    forex_ttl: Optional[int] = Field(default=None)
    gold_ttl: Optional[int] = Field(default=None)
    quote_short_ttl: Optional[int] = Field(default=None)
    quote_medium_ttl: Optional[int] = Field(default=None)
    quote_long_ttl: Optional[int] = Field(default=None)
    quote_history_days: Optional[int] = Field(default=None)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_CACHE_",
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class HttpSettings(BaseSettings):
    """HTTP 配置 - 所有默认值来自 config.toml"""

    total_timeout: Optional[int] = Field(default=None)
    connect_timeout: Optional[int] = Field(default=None)
    max_retries: Optional[int] = Field(default=None)
    retry_delay: Optional[float] = Field(default=None)
    max_concurrent: Optional[int] = Field(default=None)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_HTTP_",
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DisplaySettings(BaseSettings):
    """展示层配置 - 所有默认值来自 config.toml"""

    market_map: Optional[dict] = Field(default=None)
    type_map: Optional[dict] = Field(default=None)
    type_color: Optional[dict] = Field(default=None)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_DISPLAY_", env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore"
    )


class ProxySettings(BaseSettings):
    """代理配置 - 所有默认值来自 config.toml"""

    http: Optional[str] = Field(default=None)
    https: Optional[str] = Field(default=None)
    enabled: Optional[bool] = Field(default=None)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_PROXY_", env_file=PROJECT_ENV_PATH, env_file_encoding="utf-8", extra="ignore"
    )


class ApiKeySettings(BaseSettings):
    """API密钥配置 - 所有默认值来自 config.toml"""

    fred: Optional[str] = Field(default=None)
    imf_primary: Optional[str] = Field(default=None)
    imf_secondary: Optional[str] = Field(default=None)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_API_",
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class GoldSettings(BaseSettings):
    """黄金相关配置 - 所有默认值来自 config.toml"""

    price_usd_per_ounce: Optional[float] = Field(default=None)
    wan_oz_to_tonne: Optional[float] = Field(default=None)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_GOLD_",
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


# ============================================================
# 数据源详细配置类（从 datasource_config.py 合并）
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

    model_config = SettingsConfigDict(
        env_prefix="FCLI_SINA_",
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_cn_code(self, code: str) -> str:
        """获取A股API代码"""
        if code.startswith(("6", "9")):
            return f"{self.cn_sh_prefix}{code}"
        return f"{self.cn_sz_prefix}{code}"

    def get_hk_code(self, code: str) -> str:
        """获取港股API代码"""
        return f"{self.hk_prefix}{code}"

    def get_us_code(self, code: str) -> str:
        """获取美股API代码"""
        return f"{self.us_prefix}{code.lower()}"


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

    model_config = SettingsConfigDict(
        env_prefix="FCLI_EASTMONEY_",
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_cn_secid(self, code: str) -> str:
        """获取A股 secid"""
        if code.startswith(("sh", "SH")):
            return f"{self.cn_sh_market_code}.{code[2:]}"
        elif code.startswith(("sz", "SZ")):
            return f"{self.cn_sz_market_code}.{code[2:]}"
        elif code.startswith("6"):
            return f"{self.cn_sh_market_code}.{code}"
        return f"{self.cn_sz_market_code}.{code}"

    def get_hk_secid(self, code: str) -> str:
        """获取港股 secid"""
        clean_code = code.replace("rt_hk", "")
        return f"{self.hk_market_code}.{clean_code}"

    def get_us_secid(self, code: str) -> str:
        """获取美股 secid"""
        return f"{self.us_market_code}.{code}"

    def get_global_secid(self, code: str) -> str:
        """获取全球指数 secid"""
        if "." in code:
            return f"{self.global_market_code}.{code.split('.')[1]}"
        return f"{self.global_market_code}.{code}"


class FundDataSource(BaseSettings):
    """基金数据源配置"""

    # 天天基金
    gz_api_url: str = Field(default="https://fundgz.1234567.com.cn/js/{code}.js", description="基金估值API")
    detail_api_url: str = Field(default="https://fund.eastmoney.com/pingzxinfo_{code}.html", description="基金详情页")

    model_config = SettingsConfigDict(
        env_prefix="FCLI_FUND_",
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
        env_prefix="FCLI_FOREX_",
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_latest_url(self, base: str, symbols: Optional[List[str]] = None) -> str:
        """获取最新汇率URL"""
        url = f"{self.frankfurter_base_url}/latest?from={base}"
        if symbols:
            url += f"&to={','.join(symbols)}"
        return url

    def get_historical_url(self, date: str, base: str, symbols: Optional[List[str]] = None) -> str:
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

    # 世界黄金协会
    wgc_base_url: str = Field(default="https://www.gold.org", description="世界黄金协会网站")

    model_config = SettingsConfigDict(
        env_prefix="FCLI_GOLD_",
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

    model_config = SettingsConfigDict(
        env_prefix="FCLI_GPR_",
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
    quote_priority: List[str] = Field(default=["eastmoney", "sina", "yahoo"], description="行情数据源优先级")
    forex_priority: List[str] = Field(default=["frankfurter", "exchangerate"], description="汇率数据源优先级")
    gold_priority: List[str] = Field(default=["fred", "imf"], description="黄金数据源优先级")

    # 降级策略
    fallback_enabled: bool = Field(default=True, description="是否启用数据源降级")

    # 兼容字段 - 直接访问 URL (TOML [datasource] section)
    sina_base_url: Optional[str] = Field(default=None)
    sina_cn_quote: Optional[str] = Field(default=None)
    eastmoney_quote_api: Optional[str] = Field(default=None)
    eastmoney_batch_api: Optional[str] = Field(default=None)
    fund_gz_api: Optional[str] = Field(default=None)
    frankfurter_base: Optional[str] = Field(default=None)
    exchangerate_base: Optional[str] = Field(default=None)
    fred_base_url: Optional[str] = Field(default=None)
    imf_base_url: Optional[str] = Field(default=None)
    gpr_data_url: Optional[str] = Field(default=None)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_DATASOURCE_",
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
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
# 符号解析服务（从 datasource_config.py 合并）
# ============================================================


class SymbolRegistry:
    """统一符号解析服务 - 将用户代码转换为 API 代码"""

    def __init__(self, datasource: DataSourceConfig):
        self.datasource = datasource

    def resolve_api_code(self, code: str, market: "Market") -> str:
        """根据市场和代码解析 API 代码

        Args:
            code: 用户输入的代码 (e.g., "600519", "AAPL")
            market: 市场类型 (CN/HK/US)

        Returns:
            API 代码 (e.g., "sh600519", "gb_aapl")

        Raises:
            ValueError: 不支持的市场类型
        """
        # 导入 Market 枚举（避免循环导入）
        from .models.base import Market

        if market == Market.CN:
            return self.datasource.sina.get_cn_code(code)
        elif market == Market.HK:
            return self.datasource.sina.get_hk_code(code)
        elif market == Market.US:
            return self.datasource.sina.get_us_code(code)
        else:
            raise ValueError(f"Unsupported market: {market}")

    def infer_market(self, code: str) -> "Market":
        """从代码推断市场类型

        Args:
            code: 股票代码

        Returns:
            推断的市场类型
        """
        from .models.base import Market

        # A股: 6位数字，以 0/3/6 开头
        if code.isdigit() and len(code) == 6:
            return Market.CN
        # 港股: 5位数字
        if code.isdigit() and len(code) == 5:
            return Market.HK
        # 美股: 字母
        if code.isalpha():
            return Market.US
        # 默认美股
        return Market.US


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

# 全局符号注册表实例
symbol_registry = SymbolRegistry(config.datasource)


# 导出公共接口
__all__ = [
    "config",
    "settings",
    "Settings",
    "PACKAGE_ROOT",
    "PROJECT_ENV_PATH",
    "PROJECT_CONFIG_PATH",
    "symbol_registry",
    "SymbolRegistry",
    # 数据源配置类
    "DataSourceConfig",
    "SinaDataSource",
    "EastmoneyDataSource",
    "FundDataSource",
    "ForexDataSource",
    "GoldDataSource",
    "GPRDataSource",
]

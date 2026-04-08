"""FCLI 配置模块

配置来源: .env 文件 + 环境变量
所有默认值硬编码在 Field(default=...) 中。

环境变量命名规则:
  FCLI__{SECTION}__{FIELD}  (使用双下划线分隔)
  例如: FCLI__DB__HOST=127.0.0.1
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from .models import Asset
    from .models.base import AssetType, Market

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

    model_config = SettingsConfigDict(
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

    # 世界黄金协会
    wgc_base_url: str = Field(default="https://www.gold.org", description="世界黄金协会网站")

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
# 符号解析服务
# ============================================================


class SymbolRegistry:
    """统一符号解析服务 - 将用户代码转换为 API 代码"""

    def __init__(self, datasource: DataSourceConfig):
        self.datasource = datasource

    def resolve_api_code(self, code: str, market: Market) -> str:
        """根据市场和代码解析 API 代码

        Args:
            code: 用户输入的代码 (e.g., "600519", "AAPL")
            market: 市场类型 (CN/HK/US)

        Returns:
            API 代码 (e.g., "sh600519", "gb_aapl")

        Raises:
            ValueError: 不支持的市场类型
        """
        from .models.base import Market

        if market == Market.CN:
            return self.datasource.sina.get_cn_code(code)
        elif market == Market.HK:
            return self.datasource.sina.get_hk_code(code)
        elif market == Market.US:
            return self.datasource.sina.get_us_code(code)
        else:
            raise ValueError(f"Unsupported market: {market}")

    def infer_market(self, code: str) -> Market:
        """从代码推断市场类型

        Args:
            code: 股票代码（支持 SH/SZ/HK 前缀或纯代码）

        Returns:
            推断的市场类型
        """
        from .models.base import Market

        code_upper = code.upper().strip()

        # 港股：HK前缀 或 5位数字
        if code_upper.startswith("HK") or (code.isdigit() and len(code) == 5):
            return Market.HK

        # A股：SH/SZ前缀 或 6位数字
        if code_upper.startswith(("SH", "SZ")) or (code.isdigit() and len(code) == 6):
            return Market.CN

        # 美股：字母
        if code.isalpha():
            return Market.US

        # 默认美股
        return Market.US

    def infer_type(self, code: str) -> AssetType:
        from .models.base import AssetType

        gold_codes = {"GC", "XAU", "GOLD"}
        if code.upper().strip() in gold_codes:
            return AssetType.GOLD

        if code.isdigit() and len(code) == 6:
            prefix2 = code[:2]
            prefix3 = code[:3]

            fund_prefixes_2 = {"11", "15", "16", "50", "51", "52"}
            fund_prefixes_3 = {"159"}

            if prefix2 in fund_prefixes_2 or prefix3 in fund_prefixes_3:
                return AssetType.FUND

        return AssetType.STOCK

    def create_asset(self, code: str) -> Asset:
        from .models import Asset

        code = code.strip()
        code_upper = code.upper()
        market = self.infer_market(code)
        asset_type = self.infer_type(code)
        api_code = self._to_api_code(code, market)
        return Asset(
            code=code_upper,
            api_code=api_code,
            name=code_upper,
            market=market,
            type=asset_type,
        )

    def _to_api_code(self, code: str, market: Market) -> str:
        code_lower = code.lower()
        if market == Market.CN:
            if code_lower.startswith(("sh", "sz")):
                return code_lower
            prefix = code[:2]
            return f"sh{code}" if prefix in ("60", "68") else f"sz{code}"
        elif market == Market.HK:
            code_num = code[-5:] if code.upper().startswith("HK") else code
            return f"rt_hk{code_num}"
        else:
            return code_lower


# ============================================================
# 初始化配置
# ============================================================

# 创建配置实例
config = Settings()

symbol_registry = SymbolRegistry(config.datasource)


# 导出公共接口
__all__ = [
    "config",
    "Settings",
    "PACKAGE_ROOT",
    "PROJECT_ENV_PATH",
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

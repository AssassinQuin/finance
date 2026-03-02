"""数据源配置模块

集中管理所有数据源URL和API配置，消除硬编码。
"""

from typing import Dict, List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        env_file=".env",
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
        env_file=".env",
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
        env_file=".env",
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
        env_file=".env",
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
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class GPRDataSource(BaseSettings):
    """地缘政治风险指数数据源配置"""

    # GPR Index 网站
    gpr_base_url: str = Field(default="https://www.matteoiacoviello.com", description="GPR Index 网站基础URL")
    gpr_data_url: str = Field(
        default="https://www.matteoiacoviello.com/gpr_files/data_gpr_final.xls", description="GPR 数据文件URL"
    )

    model_config = SettingsConfigDict(
        env_prefix="FCLI_GPR_",
        env_file=".env",
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

    model_config = SettingsConfigDict(
        env_prefix="FCLI_DATASOURCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# 全局数据源配置实例
datasource_config = DataSourceConfig()

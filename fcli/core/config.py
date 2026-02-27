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

    model_config = SettingsConfigDict(
        env_prefix="FCLI_DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class CacheSettings(BaseSettings):
    search_ttl: int = Field(default=86400)
    quote_ttl: int = Field(default=300)
    forex_ttl: int = Field(default=3600)
    gold_ttl: int = Field(default=86400)
    gpr_ttl: int = Field(default=86400)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_CACHE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class ProxySettings(BaseSettings):
    """代理配置"""
    http: str = Field(default="")
    https: str = Field(default="")
    enabled: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_PROXY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
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
        env_prefix="FCLI_SOURCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
# Package root directory
PACKAGE_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    data_dir: Path = Field(default=PACKAGE_ROOT / "data")
    timeout: int = 10
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    api: ApiKeySettings = Field(default_factory=ApiKeySettings)
    gold: GoldSettings = Field(default_factory=GoldSettings)
    source: SourceSettings = Field(default_factory=SourceSettings)

    model_config = SettingsConfigDict(
        env_prefix="FCLI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__"
    )


config = Settings()
settings = config

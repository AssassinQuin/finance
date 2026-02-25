from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path
from typing import List


class DatabaseSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = "123456zx"
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


class SourceSettings(BaseSettings):
    quote_priority: List[str] = Field(default=["eastmoney", "sina", "yahoo"])
    forex_priority: List[str] = Field(default=["frankfurter", "exchangerate"])
    gold_priority: List[str] = Field(default=["wgc", "imf", "tradingeconomics"])
    fallback_enabled: bool = True

    model_config = SettingsConfigDict(
        env_prefix="FCLI_SOURCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class Settings(BaseSettings):
    data_dir: Path = Path("./data")
    timeout: int = 10
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
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

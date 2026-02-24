from pydantic_settings import BaseSettings
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

    class Config:
        env_prefix = "FCLI_DB_"


class CacheSettings(BaseSettings):
    search_ttl: int = Field(default=86400, description="搜索缓存 TTL (秒)")
    quote_ttl: int = Field(default=300, description="行情缓存 TTL (秒)")
    forex_ttl: int = Field(default=3600, description="汇率缓存 TTL (秒)")
    gold_ttl: int = Field(default=86400, description="黄金数据缓存 TTL (秒)")
    gpr_ttl: int = Field(default=86400, description="GPR 数据缓存 TTL (秒)")

    class Config:
        env_prefix = "FCLI_CACHE_"


class SourceSettings(BaseSettings):
    quote_priority: List[str] = Field(default=["eastmoney", "sina", "yahoo"])
    forex_priority: List[str] = Field(default=["frankfurter", "exchangerate"])
    gold_priority: List[str] = Field(default=["imf"])
    fallback_enabled: bool = True

    class Config:
        env_prefix = "FCLI_SOURCE_"


class Settings(BaseSettings):
    data_dir: Path = Path("./data")
    timeout: int = 10
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    source: SourceSettings = Field(default_factory=SourceSettings)

    class Config:
        env_prefix = "FCLI_"


config = Settings()
settings = config  # Alias for backward compatibility if needed

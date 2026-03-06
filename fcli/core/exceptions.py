from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """FCLI 错误码枚举 - 分类标识不同类型的错误

    错误码格式: Exxxx
    - E1xxx: 数据源错误 (Source errors)
    - E2xxx: 数据库错误 (Database errors)
    - E3xxx: 缓存错误 (Cache errors)
    - E4xxx: 业务逻辑错误 (Business logic errors)
    """

    # E1xxx: 数据源错误
    SOURCE_UNAVAILABLE = "E1001"
    ALL_SOURCES_FAILED = "E1002"
    QUOTE_PARSE_ERROR = "E1003"
    NETWORK_ERROR = "E1004"
    TIMEOUT_ERROR = "E1005"
    RATE_LIMIT_ERROR = "E1006"
    DATA_VALIDATION_ERROR = "E1007"

    # E2xxx: 数据库错误
    DATABASE_CONNECTION_ERROR = "E2001"
    DATABASE_QUERY_ERROR = "E2002"
    DATABASE_INSERT_ERROR = "E2003"
    DATABASE_UPDATE_ERROR = "E2004"
    DATABASE_DELETE_ERROR = "E2005"

    # E3xxx: 缓存错误
    CACHE_READ_ERROR = "E3001"
    CACHE_WRITE_ERROR = "E3002"
    CACHE_DELETE_ERROR = "E3003"
    CACHE_CONNECTION_ERROR = "E3004"

    # E4xxx: 业务逻辑错误
    VALIDATION_ERROR = "E4001"
    ASSET_NOT_FOUND = "E4002"
    SEARCH_ERROR = "E4003"
    INVALID_INPUT = "E4004"
    OPERATION_FAILED = "E4005"


class FcliError(Exception):
    """Base exception for FCLI with structured error information"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}

    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code.value}] {self.message}"
        return self.message


class SourceError(FcliError):
    """Data source error"""

    pass


class SourceUnavailableError(SourceError):
    """Source unavailable"""

    pass


class AllSourcesFailedError(SourceError):
    """All sources failed"""

    pass


class QuoteParseError(SourceError):
    """行情数据解析错误"""

    def __init__(self, message: str, raw_data: str | None = None):
        self.raw_data = raw_data
        super().__init__(message)


class NetworkError(SourceError):
    """网络请求错误"""

    def __init__(self, message: str, url: str | None = None):
        self.url = url
        super().__init__(message)


class TimeoutError(SourceError):
    """请求超时错误"""

    def __init__(self, message: str, timeout_seconds: float | None = None):
        self.timeout_seconds = timeout_seconds
        super().__init__(message)


class RateLimitError(SourceError):
    """API 限流错误"""

    def __init__(self, message: str, retry_after: int | None = None):
        self.retry_after = retry_after
        super().__init__(message)


class DataValidationError(SourceError):
    """数据验证错误"""

    def __init__(self, message: str, field: str | None = None, value: Any | None = None):
        self.field = field
        self.value = value
        super().__init__(message)


class DatabaseError(FcliError):
    """Database error"""

    pass


class CacheError(FcliError):
    """缓存操作错误"""

    def __init__(self, message: str, key: str | None = None):
        self.key = key
        super().__init__(message)


class ValidationError(FcliError):
    """Validation error"""

    pass


class AssetNotFoundError(FcliError):
    """Asset not found"""

    pass


class SearchError(FcliError):
    """Search error"""

    pass

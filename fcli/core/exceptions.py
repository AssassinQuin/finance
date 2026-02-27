from typing import Any, Optional


class FcliError(Exception):
    """Base exception for FCLI"""
    pass
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
    def __init__(self, message: str, raw_data: Optional[str] = None):
        self.raw_data = raw_data
        super().__init__(message)


class NetworkError(SourceError):
    """网络请求错误"""
    def __init__(self, message: str, url: Optional[str] = None):
        self.url = url
        super().__init__(message)


class TimeoutError(SourceError):
    """请求超时错误"""
    def __init__(self, message: str, timeout_seconds: Optional[float] = None):
        self.timeout_seconds = timeout_seconds
        super().__init__(message)


class RateLimitError(SourceError):
    """API 限流错误"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(message)


class DataValidationError(SourceError):
    """数据验证错误"""
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        self.field = field
        self.value = value
        super().__init__(message)


class DatabaseError(FcliError):
    """Database error"""

    pass


class CacheError(FcliError):
    """缓存操作错误"""
    def __init__(self, message: str, key: Optional[str] = None):
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

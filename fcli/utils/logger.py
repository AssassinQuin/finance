"""结构化日志工具

支持 JSON 格式输出，记录关键操作信息。
"""

import json
import logging
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional

# 默认日志格式
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class LogContext:
    """日志上下文"""

    operation: str
    market: Optional[str] = None
    code: Optional[str] = None
    source: Optional[str] = None
    cache_hit: Optional[bool] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    extra: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        result = {"operation": self.operation, "timestamp": datetime.now().isoformat()}
        if self.market:
            result["market"] = self.market
        if self.code:
            result["code"] = self.code
        if self.source:
            result["source"] = self.source
        if self.cache_hit is not None:
            result["cache_hit"] = self.cache_hit
        if self.duration_ms is not None:
            result["duration_ms"] = round(self.duration_ms, 2)
        if self.error:
            result["error"] = self.error
        if self.extra:
            result.update(self.extra)
        return result


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        # 如果有 context 属性，使用 JSON 格式
        if hasattr(record, "context") and isinstance(record.context, LogContext):
            data = record.context.to_dict()
            data["level"] = record.levelname
            data["logger"] = record.name
            data["message"] = record.getMessage()
            return json.dumps(data, ensure_ascii=False)

        # 否则使用默认格式
        return super().format(record)


class StructuredLogger:
    """结构化日志器"""

    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # 避免重复添加 handler
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(StructuredFormatter(DEFAULT_FORMAT))
            self.logger.addHandler(handler)

    def _log(self, level: int, message: str, context: Optional[LogContext] = None, **kwargs):
        """内部日志方法"""
        extra = {"context": context} if context else {}
        self.logger.log(level, message, extra=extra, **kwargs)

    def info(self, message: str, context: Optional[LogContext] = None):
        self._log(logging.INFO, message, context)

    def warning(self, message: str, context: Optional[LogContext] = None):
        self._log(logging.WARNING, message, context)

    def error(self, message: str, context: Optional[LogContext] = None):
        self._log(logging.ERROR, message, context)

    def debug(self, message: str, context: Optional[LogContext] = None):
        self._log(logging.DEBUG, message, context)

    @contextmanager
    def timed(self, operation: str, **context_kwargs):
        """计时上下文管理器"""
        start_time = time.time()
        context = LogContext(operation=operation, **context_kwargs)

        try:
            yield context
        except Exception as e:
            context.error = str(e)
            self.error(f"{operation} failed", context)
            raise
        finally:
            context.duration_ms = (time.time() - start_time) * 1000
            self.info(f"{operation} completed", context)


# 预定义的日志器
quote_logger = StructuredLogger("fcli.quote")
cache_logger = StructuredLogger("fcli.cache")
http_logger = StructuredLogger("fcli.http")


def get_logger(name: str) -> StructuredLogger:
    """获取结构化日志器"""
    return StructuredLogger(name)

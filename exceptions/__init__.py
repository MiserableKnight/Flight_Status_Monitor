"""
Flight Status Monitor - 异常类体系

提供结构化的异常处理，包含上下文信息以便调试和监控。
"""

from .auth import (
    LoginFailedError,
    SessionExpiredError,
)
from .base import (
    AuthenticationException,
    ConfigurationException,
    ConnectionException,
    DataException,
    FlightMonitorException,
    NotificationException,
)
from .connection import (
    BrowserConnectionError,
    NetworkTimeoutError,
    PageLoadError,
    ReconnectionFailedError,
)
from .data import (
    DataExtractionError,
    DataFileError,
    DataParseError,
    DataValidationError,
)
from .notification import (
    AlertTriggerError,
    EmailSendError,
)

__all__ = [
    # 基础异常
    "FlightMonitorException",
    "ConnectionException",
    "AuthenticationException",
    "DataException",
    "NotificationException",
    "ConfigurationException",
    # 连接异常
    "BrowserConnectionError",
    "NetworkTimeoutError",
    "PageLoadError",
    "ReconnectionFailedError",
    # 数据异常
    "DataExtractionError",
    "DataValidationError",
    "DataParseError",
    "DataFileError",
    # 通知异常
    "EmailSendError",
    "AlertTriggerError",
    # 认证异常
    "LoginFailedError",
    "SessionExpiredError",
]

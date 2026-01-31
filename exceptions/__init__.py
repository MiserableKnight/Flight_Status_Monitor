"""
Flight Status Monitor - Custom Exception Hierarchy

This module provides a structured exception hierarchy for the flight monitoring system.
All exceptions include rich context information for debugging and monitoring.

## Exception Categories

### Authentication Errors（认证异常）

#### auth.py
- **LoginFailedError**: Login credentials are invalid or login process failed
- **SessionExpiredError**: User session has expired, requires re-authentication

### Connection Errors（连接异常）

#### connection.py
- **BrowserConnectionError**: Failed to connect to browser debug port
- **NetworkTimeoutError**: Network operation timed out
- **PageLoadError**: Page failed to load within timeout
- **ReconnectionFailedError**: Automatic reconnection attempts exhausted

### Data Errors（数据异常）

#### data.py
- **DataExtractionError**: Failed to extract data from web page
- **DataValidationError**: Data validation checks failed
- **DataParseError**: Failed to parse data format (CSV, JSON, etc.)
- **DataFileError**: File operation failed (read/write/delete)
- **DataFreshnessError**: Data is too stale for monitoring operations

### Notification Errors（通知异常）

#### notification.py
- **EmailSendError**: Failed to send email notification
- **AlertTriggerError**: Failed to trigger or process alert

### Base Exception（基础异常）

#### base.py
- **FlightMonitorException**: Base exception for all custom exceptions
- **ConnectionException**: Base for connection-related errors
- **AuthenticationException**: Base for authentication errors
- **DataException**: Base for data processing errors
- **NotificationException**: Base for notification errors
- **ConfigurationException**: Base for configuration errors

## Exception Context（异常上下文）

All exceptions include relevant context information for debugging:

```python
# Connection errors include port and retry info
except BrowserConnectionError as e:
    logger.error(f"Connection failed on port {e.port}")
    logger.error(f"Retry attempts: {e.retry_count}")

# Data errors include aircraft and flight info
except DataExtractionError as e:
    logger.error(f"Failed to extract for {e.aircraft}")
    logger.error(f"Flight: {e.flight}")
```

## Usage Example（使用示例）

```python
from exceptions import (
    BrowserConnectionError,
    LoginFailedError,
    DataExtractionError
)

# Raise with context
raise DataExtractionError(
    aircraft="B-1234",
    flight="VJ105",
    element_selector="#out-time",
    reason="Element not found on page"
)

# Catch with specific handling
try:
    data = fetcher.extract_data()
except DataExtractionError as e:
    logger.error(f"Data extraction failed: {e}")
except BrowserConnectionError as e:
    logger.error(f"Browser connection failed: {e}")
except LoginFailedError as e:
    logger.error(f"Authentication failed: {e}")
```

## Best Practices（最佳实践）

1. **Use specific exceptions** - Catch most specific exception first
2. **Include context** - Always pass relevant context when raising
3. **Log with context** - Access exception attributes for detailed logging
4. **Let critical errors propagate** - Don't catch and hide system failures

## Related Documentation

- docs/architecture/error-handling.md - Error handling architecture guide
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
    DataFreshnessError,
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
    "DataFreshnessError",
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

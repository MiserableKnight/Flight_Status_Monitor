"""
Data Fetchers Module - 数据抓取器模块

This module provides data extraction capabilities from web interfaces,
with shared browser connection management and automatic reconnection.

## Base Infrastructure（基础设施）

### BaseFetcher
Abstract base class for all fetchers.
Provides:
- Browser connection management (cached by debug port)
- Smart login with session management
- Date navigation and page state detection
- Automatic reconnection on connection loss
- CSV data saving with automatic directory creation

### LoginManager
Centralized login logic with credential management.
Handles login failures, session expiry, and reauthentication.

## Data Fetchers（数据抓取器）

### LegFetcher
Extracts flight leg data (OUT/OFF/ON/IN times) for multiple aircraft.
Features:
- Multi-aircraft batch processing
- Automatic aircraft selection on page
- Intelligent retry on element access failures
- Data validation and deduplication

Usage:
```python
from fetchers import LegFetcher
fetcher = LegFetcher()
fetcher.connect_browser()
fetcher.smart_login(page)
data = fetcher.fetch_data("2026-01-30", ["B-1234", "B-5678"])
fetcher.save_to_csv(data, "data/daily_raw/leg_data_2026-01-30.csv")
```

### FaultFetcher
Extracts aircraft fault data with filtering support.
Features:
- Historical fault data retrieval
- Date-based navigation
- Raw fault data extraction
- Integration with FaultParser for structured output

Usage:
```python
from fetchers import FaultFetcher
fetcher = FaultFetcher()
fetcher.connect_browser()
fetcher.smart_login(page)
faults = fetcher.fetch_data("2026-01-30", "B-1234")
```

## Data Processing（数据处理）

### FaultParser
Parses raw fault data into structured format.
Extracts fault codes, descriptions, timestamps, and aircraft info.

### FaultDataSaver
Saves fault data to CSV files with proper formatting.
Handles duplicate detection and data validation.

### DataProcessor
General data processing utilities.
Provides common data transformation and validation functions.

## Architecture（架构设计）

### Browser Connection Management
All fetchers share browser connections via BaseFetcher._browsers (class-level dict):
- Key: Debug port number
- Value: ChromiumPage instance
- Automatic cache invalidation on connection loss

### Reconnection Strategy
1. Detect connection failure (page operation timeout)
2. Clear cached connection for that port
3. Reconnect to debug port
4. Re-login if needed
5. Resume operation

### Error Handling
All fetchers use structured exceptions from exceptions module:
- BrowserConnectionError: Connection to debug port failed
- LoginFailedError: Authentication failed
- DataExtractionError: Data extraction failed
- PageLoadError: Page navigation failed

## Usage Example（完整示例）

```python
from fetchers import LegFetcher, FaultFetcher

# Leg data fetching
leg_fetcher = LegFetcher()
leg_fetcher.connect_browser()
leg_data = leg_fetcher.fetch_data("2026-01-30", ["B-1234"])
leg_fetcher.save_to_csv(leg_data, "leg_data.csv")

# Fault data fetching
fault_fetcher = FaultFetcher()
fault_fetcher.connect_browser()
fault_data = fault_fetcher.fetch_data("2026-01-30", "B-1234")
```

## Dependencies

- DrissionPage: Browser automation framework
- pandas: CSV data handling
- exceptions: Structured exception classes
"""

__all__ = [
    "BaseFetcher",
    "LoginManager",
    "LegFetcher",
    "FaultFetcher",
    "FaultParser",
    "FaultDataSaver",
    "DataProcessor",
]


def __getattr__(name):
    """延迟导入，避免相对导入问题"""
    if name == "BaseFetcher":
        from .base_fetcher import BaseFetcher

        return BaseFetcher
    elif name == "LoginManager":
        from .login_manager import LoginManager

        return LoginManager
    elif name == "LegFetcher":
        from .leg_fetcher import LegFetcher

        return LegFetcher
    elif name == "FaultFetcher":
        from .fault_fetcher import FaultFetcher

        return FaultFetcher
    elif name == "FaultParser":
        from .fault_parser import FaultParser

        return FaultParser
    elif name == "FaultDataSaver":
        from .fault_data_saver import FaultDataSaver

        return FaultDataSaver
    elif name == "DataProcessor":
        from .data_processor import DataProcessor

        return DataProcessor
    raise AttributeError(f"module {__name__} has no attribute {name}")

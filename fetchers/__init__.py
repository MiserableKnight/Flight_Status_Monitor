"""
Data Fetchers Module - 数据抓取器模块

This module provides data extraction capabilities from web interfaces,
with shared browser connection management and automatic reconnection.

## Components（组件列表）

### Base Infrastructure（基础设施）

#### base_fetcher.py - BaseFetcher
Abstract base class for all fetchers.
Provides:
- Browser connection management (cached by debug port)
- Smart login with session management
- Date navigation and page state detection
- Automatic reconnection on connection loss
- CSV data saving with automatic directory creation

#### data_processor.py - DataProcessor
General data processing utilities.
Provides common data transformation and validation functions.

#### fault_data_saver.py - FaultDataSaver
Saves fault data to CSV files with proper formatting.
Handles duplicate detection and data validation.

#### fault_parser.py - FaultParser
Parses raw fault data into structured format.
Extracts fault codes, descriptions, timestamps, and aircraft info.

### Data Fetchers（数据抓取器）

#### leg_fetcher.py - LegFetcher
Extracts flight leg data (OUT/OFF/ON/IN times) for multiple aircraft.

Usage:
```python
from fetchers import LegFetcher
fetcher = LegFetcher()
fetcher.connect_browser()
fetcher.smart_login(page)
data = fetcher.fetch_data("2026-01-30", ["B-1234", "B-5678"])
fetcher.save_to_csv(data, "data/daily_raw/leg_data_2026-01-30.csv")
```

#### fault_fetcher.py - FaultFetcher
Extracts aircraft fault data with filtering support.

Usage:
```python
from fetchers import FaultFetcher
fetcher = FaultFetcher()
fetcher.connect_browser()
fetcher.smart_login(page)
faults = fetcher.fetch_data("2026-01-30", "B-1234")
```

## Architecture（架构设计）

### Browser Connection Management
All fetchers share browser connections via BaseFetcher._browsers (class-level dict):
- Key: Debug port number
- Value: ChromiumPage instance
- Automatic cache invalidation on connection loss

### Error Handling
All fetchers use structured exceptions from exceptions module:
- BrowserConnectionError: Connection to debug port failed
- LoginFailedError: Authentication failed
- DataExtractionError: Data extraction failed
- PageLoadError: Page navigation failed

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

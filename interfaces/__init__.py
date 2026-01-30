"""
Interfaces Module - 接口层定义

This module provides clear interface contracts for the flight monitoring system.
Enables dependency injection, loose coupling, and testability.

## Design Philosophy（设计理念）

### Interface-Based Design
- Defines contracts without implementation details
- Enables dependency injection for testing
- Supports multiple implementations
- Facilitates mocking in unit tests

### Benefits
- **Testability**: Inject mock objects for unit testing
- **Flexibility**: Swap implementations without changing client code
- **Maintainability**: Clear contracts between components
- **Extensibility**: Add new implementations without modifying existing code

## Core Interfaces（核心接口）

### IFetcher
Data fetching interface for all data extractors.

Methods:
- connect_browser(): Establish browser connection
- smart_login(page): Perform login with session management
- get_today_date(): Get current date string
- navigate_to_target_page(page, target_date, aircraft_list): Navigate to data page
- save_to_csv(data, filename): Save data to CSV file

Implementations:
- LegFetcher (fetchers/leg_fetcher.py)
- FaultFetcher (fetchers/fault_fetcher.py)

Usage:
```python
from interfaces import IFetcher
from fetchers import LegFetcher

def process_data(fetcher: IFetcher):
    fetcher.connect_browser()
    data = fetcher.fetch_data("2026-01-30", ["B-1234"])

# Production
fetcher = LegFetcher()
process_data(fetcher)

# Testing
mock_fetcher = MockFetcher()  # Implements IFetcher
process_data(mock_fetcher)
```

### ILogger
Logging interface for system-wide logging.

Methods:
- Callable with level parameter: logger(message, level)

Levels:
- "DEBUG": Detailed debugging information
- "INFO": General informational messages
- "WARNING": Warning messages for unexpected events
- "ERROR": Error messages for failures
- "CRITICAL": Critical errors requiring immediate attention

Usage:
```python
from interfaces import ILogger

class MyComponent:
    def __init__(self, logger: ILogger):
        self.logger = logger

    def run(self):
        self.logger("Starting component", "INFO")
        self.logger("Component started successfully", "INFO")
```

### IConfigLoader
Configuration loading interface for unified configuration access.

Methods:
- get_all_config(): Get all configuration sections as dictionary
- get_config(section): Get specific configuration section

Returns:
- Dictionary with configuration key-value pairs

Usage:
```python
from interfaces import IConfigLoader

class MyScheduler:
    def __init__(self, config_loader: IConfigLoader):
        self.config = config_loader

    def get_interval(self):
        scheduler_config = self.config.get_config("scheduler")
        return scheduler_config.get("check_interval", 60)
```

### IScheduler
Scheduler interface for automated data fetching and monitoring.

Methods:
- connect_browser(): Establish browser connection
- login(): Perform authentication
- fetch_data(): Fetch data from source
- get_check_interval(): Get polling interval in seconds
- run(): Start main scheduler loop

Implementations:
- LegScheduler (schedulers/leg_scheduler.py)
- FaultScheduler (schedulers/fault_scheduler.py)

Usage:
```python
from interfaces import IScheduler

def start_monitoring(scheduler: IScheduler):
    scheduler.connect_browser()
    scheduler.login()
    scheduler.run()  # Blocks until operating hours end
```

## Usage Patterns（使用模式）

### 1. Constructor Injection（构造函数注入）
Pass dependencies through constructor:

```python
from interfaces import IFetcher, ILogger, IConfigLoader

class LegScheduler:
    def __init__(
        self,
        fetcher: IFetcher | None = None,
        config_loader: IConfigLoader | None = None,
        logger: ILogger | None = None
    ):
        # Create dependencies if not provided
        self.fetcher = fetcher or LegFetcher()
        self.config_loader = config_loader or load_config()
        self.logger = logger or get_logger()
```

### 2. Method Injection（方法注入）
Pass dependencies to specific methods:

```python
def process_with_fetcher(data: dict, fetcher: IFetcher):
    # Use injected fetcher for this operation only
    return fetcher.save_to_csv(data, "output.csv")
```

### 3. Mocking for Testing（测试模拟）
Create mock implementations for testing:

```python
from interfaces import IFetcher, ILogger
import unittest

class MockFetcher(IFetcher):
    def connect_browser(self):
        return True

    def smart_login(self, page):
        return True

    # ... implement other methods

class TestLegScheduler(unittest.TestCase):
    def test_scheduler(self):
        mock_fetcher = MockFetcher()
        mock_logger = MockLogger()
        scheduler = LegScheduler(
            fetcher=mock_fetcher,
            logger=mock_logger
        )
        # Test without real browser or config files
```

## Interface Contracts（接口契约）

### Type Hints
All interfaces use Python type hints for clarity:

```python
def connect_browser(self) -> bool: ...
def get_config(self, section: str) -> dict: ...
def __call__(self, message: str, level: str) -> None: ...
```

### Return Values
- Methods return specific types (bool, dict, str, etc.)
- Callables (ILogger) return None
- Fetchers return data or file paths

### Exceptions
Interfaces don't specify exception types:
- Implementations can raise appropriate exceptions
- Common: ConnectionError, ValueError, IOError
- Custom: BrowserConnectionError, LoginFailedError, etc.

## Implementation Guidelines（实现指南）

### When to Create Interfaces
✅ Create interfaces for:
- Core system components (fetchers, schedulers, notifiers)
- External dependencies (browser, email, file system)
- Components that need testing (everything, ideally)

❌ Don't create interfaces for:
- Simple data classes (DTOs)
- Utility functions with no side effects
- Internal implementation details

### Interface Segregation
Keep interfaces focused and cohesive:
- IFetcher: Data fetching only
- ILogger: Logging only
- IScheduler: Scheduling only

Don't create god interfaces like ISystemComponent.

## Dependency Injection Best Practices（依赖注入最佳实践）

### 1. Optional Dependencies
Make dependencies optional with default values:

```python
def __init__(self, fetcher: IFetcher | None = None):
    self.fetcher = fetcher or DefaultFetcher()
```

### 2. Factory Functions
Provide factory functions for common cases:

```python
def create_leg_scheduler() -> LegScheduler:
    # Create LegScheduler with production dependencies
    return LegScheduler(
        fetcher=LegFetcher(),
        config_loader=load_config(),
        logger=get_logger()
    )
```

### 3. Test Helpers
Provide test helper functions:

```python
def create_test_scheduler(mock_data: dict) -> LegScheduler:
    # Create LegScheduler with mock dependencies for testing
    return LegScheduler(
        fetcher=MockFetcher(data=mock_data),
        config_loader=MockConfigLoader(),
        logger=MockLogger()
    )
```

## Related Documentation

- docs/guides/dependency-injection.md - Detailed dependency injection guide
- docs/architecture/project-structure.md - Architecture overview
- interfaces/interfaces.py - Full interface definitions

## Example: Full Workflow（完整示例）

```python
from interfaces import IFetcher, ILogger, IConfigLoader, IScheduler
from fetchers import LegFetcher
from schedulers import LegScheduler
from config import load_config
from core import get_logger

# Production: Use real implementations
class ProductionSetup:
    @staticmethod
    def create_scheduler() -> IScheduler:
        return LegScheduler(
            fetcher=LegFetcher(),
            config_loader=load_config(),
            logger=get_logger()
        )

# Testing: Use mock implementations
class TestSetup:
    @staticmethod
    def create_scheduler() -> IScheduler:
        return LegScheduler(
            fetcher=MockFetcher(),
            config_loader=MockConfigLoader(),
            logger=MockLogger()
        )

# Usage
scheduler = ProductionSetup.create_scheduler()
scheduler.run()
```

## Dependencies

- typing: Type hints and protocols
- abc: Abstract base classes (optional, not currently used)
"""

from .interfaces import IConfigLoader, IFetcher, ILogger, IScheduler

__all__ = ["IFetcher", "IScheduler", "ILogger", "IConfigLoader"]

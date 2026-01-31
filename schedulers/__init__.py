"""
Schedulers Module - 调度器模块

This module provides orchestration for automated data fetching and monitoring.
Implements dual-scheduler architecture for independent monitoring of leg and fault data.

## Components（组件列表）

### Base Infrastructure（基础设施）

#### base_scheduler.py - BaseScheduler
Abstract base class for all schedulers.
Provides:
- Dependency injection support (config_loader, logger, fetcher)
- Browser connection management
- Smart login with reconnection logic
- Main loop template with time-based scheduling
- Graceful shutdown on keyboard interrupt

### Production Schedulers（生产调度器）

#### leg_scheduler.py - LegScheduler (port 9222)
Monitors flight leg status (OUT/OFF/ON/IN times).

Features:
- Runs on Chrome debug port 9222
- Fetches leg data for all configured aircraft
- Triggers LegStatusMonitor for status change notifications
- Triggers LegAlertMonitor for duration/freshness alerts
- Updates cumulative leg data CSV

Usage:
```python
from schedulers import LegScheduler
scheduler = LegScheduler()
scheduler.run()
```

#### fault_scheduler.py - FaultScheduler (port 9333)
Monitors aircraft fault data.

Features:
- Runs on Chrome debug port 9333
- Fetches fault data for all configured aircraft
- Applies fault filtering rules
- Triggers FaultStatusMonitor for notifications

Usage:
```python
from schedulers import FaultScheduler
scheduler = FaultScheduler()
scheduler.run()
```

## Dual-Scheduler Architecture（双调度器架构）

### Design Rationale
Two independent schedulers run on separate Chrome instances:
- **Isolation**: Failure in one scheduler doesn't affect the other
- **Prioritization**: FlightTracker intelligently decides which page to monitor first
- **Parallelism**: Both can run simultaneously without interference

### Browser Connection Management
- Each scheduler uses a dedicated Chrome debug port
- BaseFetcher caches connections by port (class-level dict)
- Automatic reconnection on connection loss

### Intelligent Page Prioritization
FlightTracker (core/flight_tracker.py) coordinates between schedulers:
- Prioritizes Leg page if aircraft is airborne past scheduled arrival
- Prioritizes Leg page if ground aircraft is past scheduled departure

## Configuration（配置）

### Operating Hours
- Configured in config.ini: `[scheduler] start_time` and `end_time`
- Default: 06:00 - 23:59

### Check Interval
- Configured in config.ini: `[scheduler] check_interval`
- Default: 60 seconds

## Dependency Injection（依赖注入）

All schedulers support optional dependency injection for testing:

```python
# Production (auto-creates dependencies)
scheduler = LegScheduler()

# Testing (inject mocks)
from unittest.mock import Mock
scheduler = LegScheduler(
    fetcher=MockFetcher(),
    config_loader=MockConfigLoader(),
    logger=MockLogger()
)
```

## Dependencies

- DrissionPage: Browser automation
- fetchers: Data fetching classes
- processors: Data processing classes
- notifiers: Email notification classes
- core: Base classes (BaseScheduler)
- config: Configuration loading
"""

__all__ = [
    "BaseScheduler",
    "LegScheduler",
    "FaultScheduler",
]


def __getattr__(name):
    """延迟导入，避免相对导入问题"""
    if name == "BaseScheduler":
        from .base_scheduler import BaseScheduler

        return BaseScheduler
    elif name == "LegScheduler":
        from .leg_scheduler import LegScheduler

        return LegScheduler
    elif name == "FaultScheduler":
        from .fault_scheduler import FaultScheduler

        return FaultScheduler
    raise AttributeError(f"module {__name__} has no attribute {name}")

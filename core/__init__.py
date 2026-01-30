"""
Core System Module - 核心系统模块

This module provides foundational components for the flight monitoring system,
including browser management, data processing, and monitoring infrastructure.

## Browser Management（浏览器管理）

### BrowserHandler
Low-level ChromiumPage connection to Chrome debug ports.
Handles browser lifecycle, connection pooling, and automatic reconnection.

### Navigator
Intelligent page navigation with state detection.
Automatically detects login state and navigates to target pages.

### LoginManager
Centralized login logic with credential management and session handling.

## Data Processing（数据处理）

### FlightTracker
Real-time flight phase tracking for multiple aircraft.
Tracks flight phases: SCHEDULED → PUSHBACK → AIRBORNE → LANDED → IN_GATE.
Provides intelligent page prioritization (Leg vs Fault) based on flight status.

### AbnormalDetector
Diversion detection based on route chain analysis.
Identifies abnormal flight patterns like diversions.

### FaultFilter
CSV-based fault filtering with multi-column AND rules.
Supports group filtering for simultaneous faults.

### DataSaver
Generic CSV data saving with automatic directory creation.

## Monitoring Framework（监控框架）

### BaseMonitor
Template method pattern for status monitoring.
Implements hash-based change detection and notification workflow.

### BaseNotifier
Email notification base class with hash-based deduplication.
Prevents duplicate notifications for the same content.

## Logging（日志系统）

### get_logger()
Unified logging interface with automatic file rotation.
Log retention: 24 hours. Log directory: logs/

## Usage Example

```python
from core import BrowserHandler, get_logger, FlightTracker

# Browser connection
handler = BrowserHandler(port=9222)
page = handler.connect()

# Logging
logger = get_logger()
logger.info("System started")

# Flight tracking
tracker = FlightTracker()
tracker.update_flight_status("B-1234", "VJ105", "AIRBORNE")
```

## Architecture Notes

- BrowserHandler caches connections by debug port (class-level cache)
- FlightTracker maintains state for all aircraft across both schedulers
- BaseMonitor uses MD5 hash for content change detection
- All log files automatically rotate and are cleaned up after 24h
"""

# 延迟导入，避免依赖问题
__all__ = [
    "BrowserHandler",
    "Navigator",
    "LoginManager",
    "FlightTracker",
    "AbnormalDetector",
    "FaultFilter",
    "DataSaver",
    "BaseMonitor",
    "BaseNotifier",
    "get_logger",
]


def __getattr__(name):
    """延迟导入，只在需要时加载模块"""
    if name == "BrowserHandler":
        from .browser_handler import BrowserHandler

        return BrowserHandler
    elif name == "Navigator":
        from .navigator import Navigator

        return Navigator
    elif name == "LoginManager":
        from .login_manager import LoginManager

        return LoginManager
    elif name == "FlightTracker":
        from .flight_tracker import FlightTracker

        return FlightTracker
    elif name == "AbnormalDetector":
        from .abnormal_detector import AbnormalDetector

        return AbnormalDetector
    elif name == "FaultFilter":
        from .fault_filter import FaultFilter

        return FaultFilter
    elif name == "DataSaver":
        from .data_saver import DataSaver

        return DataSaver
    elif name == "BaseMonitor":
        from .base_monitor import BaseMonitor

        return BaseMonitor
    elif name == "BaseNotifier":
        from .base_notifier import BaseNotifier

        return BaseNotifier
    elif name == "get_logger":
        from .logger import get_logger

        return get_logger
    raise AttributeError(f"module {__name__} has no attribute {name}")

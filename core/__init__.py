"""
Core System Module - 核心系统模块

This module provides foundational components for the flight monitoring system,
including browser management, data processing, and monitoring infrastructure.

## Components（组件列表）

### Browser Management（浏览器管理）

#### browser_handler.py - BrowserHandler
Low-level ChromiumPage connection to Chrome debug ports.
Handles browser lifecycle, connection pooling, and automatic reconnection.

#### login_manager.py - LoginManager
Centralized login logic with credential management and session handling.
Provides intelligent page navigation with state detection.

### Data Processing（数据处理）

#### flight_tracker.py - FlightTracker
Real-time flight phase tracking for multiple aircraft.
Tracks flight phases: SCHEDULED → PUSHBACK → AIRBORNE → LANDED → IN_GATE.
Provides intelligent page prioritization (Leg vs Fault) based on flight status.

#### abnormal_detector.py - AbnormalDetector
Diversion detection based on route chain analysis.
Identifies abnormal flight patterns like diversions.

#### fault_filter.py - FaultFilter
CSV-based fault filtering with multi-column AND rules.
Supports group filtering for simultaneous faults.

#### data_saver.py - DataSaver
Generic CSV data saving with automatic directory creation.

### Monitoring Framework（监控框架）

#### base_monitor.py - BaseMonitor
Template method pattern for status monitoring.
Implements hash-based change detection and notification workflow.

#### base_notifier.py - BaseNotifier
Email notification base class with hash-based deduplication.
Prevents duplicate notifications for the same content.

### Logging（日志系统）

#### logger.py - get_logger()
Unified logging interface with automatic file rotation.
Log retention: 24 hours. Log directory: logs/

## Usage Example

```python
from core import BrowserHandler, get_logger, FlightTracker

# Browser connection
handler = BrowserHandler(user_data_path="path", local_port=9222)
handler.connect()
page = handler.get_page()

# Logging
logger = get_logger()
logger("System started", "INFO")

# Flight tracking
tracker = FlightTracker()
tracker.update_flight_status("B-1234", "VJ105", "AIRBORNE")
```

## Architecture Notes

- BrowserHandler manages Chrome debug port connections
- LoginManager handles page state detection and navigation
- FlightTracker coordinates monitoring priority between schedulers
- BaseMonitor uses MD5 hash for content change detection
- BaseNotifier prevents duplicate email notifications
- All log files automatically rotate and are cleaned up after 24h
"""

# 延迟导入，避免依赖问题
__all__ = [
    "BrowserHandler",
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

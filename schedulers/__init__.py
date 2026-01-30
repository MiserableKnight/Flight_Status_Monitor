"""
Schedulers Module - 调度器模块

This module provides orchestration for automated data fetching and monitoring.
Implements dual-scheduler architecture for independent monitoring of leg and fault data.

## Base Infrastructure（基础设施）

### BaseScheduler
Abstract base class for all schedulers.
Provides:
- Dependency injection support (config_loader, logger, fetcher)
- Browser connection management
- Smart login with reconnection logic
- Main loop template with time-based scheduling
- Graceful shutdown on keyboard interrupt

Template method pattern:
```
run()
  ↓
connect_browser() → login()
  ↓
while in_operating_hours:
    fetch_data()
    process_data()
    send_notifications()
    sleep(check_interval)
  ↓
cleanup()
```

## Production Schedulers（生产调度器）

### LegScheduler (port 9222)
Monitors flight leg status (OUT/OFF/ON/IN times).
Features:
- Runs on Chrome debug port 9222
- Fetches leg data for all configured aircraft
- Triggers LegStatusMonitor for status change notifications
- Triggers LegAlertMonitor for duration/freshness alerts
- Updates cumulative leg data CSV
- Operating hours: 06:00 - 23:59 (configurable)

Data flow:
```
LegScheduler
  ↓
LegFetcher (fetch data)
  ↓
LegDataUpdate (merge to cumulative)
  ↓
LegStatusMonitor (detect changes)
  ↓
LegStatusNotifier (send emails)
```

Usage:
```python
from schedulers import LegScheduler
scheduler = LegScheduler()
scheduler.run()  # Blocks until operating hours end
```

### FaultScheduler (port 9333)
Monitors aircraft fault data.
Features:
- Runs on Chrome debug port 9333
- Fetches fault data for all configured aircraft
- Applies fault filtering rules
- Triggers FaultStatusMonitor for notifications
- Operating hours: 06:00 - 23:59 (configurable)

Data flow:
```
FaultScheduler
  ↓
FaultFetcher (fetch data)
  ↓
FaultStatusMonitor (detect changes)
  ↓
FaultStatusNotifier (send emails)
```

Usage:
```python
from schedulers import FaultScheduler
scheduler = FaultScheduler()
scheduler.run()  # Blocks until operating hours end
```

## Dual-Scheduler Architecture（双调度器架构）

### Design Rationale
Two independent schedulers run on separate Chrome instances:
- **Isolation**: Failure in one scheduler doesn't affect the other
- **Prioritization**: FlightTracker intelligently decides which page to monitor first
- **Parallelism**: Both can run simultaneously without interference
- **Flexibility**: Can restart one scheduler without affecting the other

### Browser Connection Management
- Each scheduler uses a dedicated Chrome debug port (9222 for Leg, 9333 for Fault)
- BaseFetcher caches connections by port (class-level dict)
- Automatic reconnection on connection loss
- Shared connection across multiple fetch operations

### Intelligent Page Prioritization
FlightTracker (core/flight_tracker.py) coordinates between schedulers:
- Prioritizes Leg page if aircraft is airborne past scheduled arrival
- Prioritizes Leg page if ground aircraft is past scheduled departure
- Defaults to Leg page monitoring if no aircraft airborne

```python
# FlightTracker decision logic
should_monitor_leg = flight_tracker.should_monitor_leg_first(current_time)
if should_monitor_leg:
    # Prioritize LegScheduler (port 9222)
else:
    # Prioritize FaultScheduler (port 9333)
```

## Scheduler Lifecycle（调度器生命周期）

### 1. Initialization
```python
scheduler = LegScheduler(
    config_loader=custom_config,  # Optional
    logger=custom_logger,          # Optional
    fetcher=custom_fetcher         # Optional
)
```

### 2. Startup
- Wait until start_time (operating hours begin)
- Connect to Chrome debug port
- Perform smart login
- Load initial state

### 3. Main Loop
```python
while in_operating_hours():
    # Fetch data
    data = fetcher.fetch_data(date, aircraft_list)

    # Process data
    processor.process(data)

    # Send notifications
    notifier.send(alert)

    # Sleep for check_interval
    time.sleep(check_interval)
```

### 4. Shutdown
- Triggered by keyboard interrupt (Ctrl+C)
- Graceful cleanup (close browser connections)
- Save final state

## Configuration（配置）

### Operating Hours
- Configured in config.ini: `[scheduler] start_time` and `end_time`
- Default: 06:00 - 23:59
- Outside operating hours: scheduler waits

### Check Interval
- Configured in config.ini: `[scheduler] check_interval`
- Default: 60 seconds
- Controls how often to fetch data

### Aircraft List
- Configured in config.ini: `[aircraft] aircraft_list`
- Comma-separated tail numbers
- All schedulers monitor same aircraft list

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

## Usage Example（完整示例）

```python
from schedulers import LegScheduler, FaultScheduler

# Production environment
leg_scheduler = LegScheduler()
fault_scheduler = FaultScheduler()

# Run both (typically in separate terminals/processes)
# Terminal 1:
leg_scheduler.run()

# Terminal 2:
fault_scheduler.run()
```

Or use the provided batch files:
- `bin/leg_monitor.bat` - Starts LegScheduler
- `bin/faults_monitor.bat` - Starts FaultScheduler

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

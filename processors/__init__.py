"""
Data Processors Module - 数据处理器模块

This module provides data processing, monitoring, and alerting capabilities.
All processors follow the template method pattern defined in BaseMonitor.

## Leg Data Processing（航段数据处理）

### LegDataUpdate
Updates cumulative leg data CSV from daily raw data.
Features:
- Merges today's data with historical data
- Removes duplicates based on (date, aircraft, flight)
- Automatic CSV sorting and formatting
- Preserves data integrity

Usage:
```python
from processors import LegDataUpdate
updater = LegDataUpdate(daily_file="data/daily_raw/leg_data_2026-01-30.csv")
updater.update()
```

### LegStatusMonitor
Monitors leg status changes and sends email notifications.
Features:
- Hash-based change detection (MD5 of content)
- Detects OUT/OFF/ON/IN time updates
- Sends Vietnam time formatted emails
- Tracks last state to detect changes

Triggers notification when:
- OUT time appears (pushback started)
- OFF time appears (airborne)
- ON time appears (landed)
- IN time appears (at gate)

Usage:
```python
from processors import LegStatusMonitor
monitor = LegStatusMonitor()
monitor.run()  # Reads data, detects changes, sends notifications
```

### LegAlertMonitor
Monitors flight duration and triggers alerts for abnormal flights.
Features:
- Checks flight duration thresholds
- Monitors data freshness (alerts if data too old)
- Tracks alert state to avoid duplicate notifications
- Separated from LegStatusMonitor for independent alerting

Alert conditions:
- Flight duration exceeds threshold (e.g., > 150 minutes for 110min scheduled)
- Data freshness check fails (no update for configured minutes)

Usage:
```python
from processors import LegAlertMonitor
monitor = LegAlertMonitor()
monitor.run()  # Checks duration and freshness, sends alerts
```

## Fault Data Processing（故障数据处理）

### FaultStatusMonitor
Monitors fault data changes and sends email notifications.
Features:
- Hash-based change detection
- Applies fault filtering rules before notification
- Tracks historical fault count
- Lists new/removed faults

Usage:
```python
from processors import FaultStatusMonitor
monitor = FaultStatusMonitor()
monitor.run()  # Reads data, detects changes, sends notifications
```

## Architecture（架构设计）

### Template Method Pattern
All processors inherit from BaseMonitor (core/base_monitor.py):

```
run()
  ↓
read_data_file()           # Read current data from CSV
  ↓
load_last_status()         # Load previous state (hash)
  ↓
generate_content()         # Generate notification content
  ↓ (if changed)
send_notification()        # Send email via notifier
  ↓
save_current_status()      # Save current state (hash)
```

### Hash-Based Change Detection
- MD5 hash of data content (or JSON representation)
- Stored in status files (e.g., data/leg_status.json)
- Only send notification if hash changes
- Prevents duplicate notifications

### Data Flow（数据流）

```
Daily Raw Data (from fetchers)
    ↓
LegDataUpdate (merge to cumulative)
    ↓
Cumulative CSV (data/leg_data.csv)
    ↓
LegStatusMonitor / LegAlertMonitor
    ↓
Notifiers (send emails)
```

## Configuration（配置）

### File Paths
- Daily raw data: `data/daily_raw/leg_data_YYYY-MM-DD.csv`
- Cumulative data: `data/leg_data.csv`
- Status files: `data/leg_status.json`, `data/leg_alert_state.json`, `data/fault_status.json`

### Thresholds
- Flight duration alert: configured in LegAlertMonitor
- Data freshness alert: configured in LegAlertMonitor
- Check interval: configured in schedulers

## Usage Example（完整示例）

```python
from processors import LegDataUpdate, LegStatusMonitor, LegAlertMonitor

# Update cumulative data
updater = LegDataUpdate(daily_file="data/daily_raw/leg_data_2026-01-30.csv")
updater.update()

# Monitor status changes
status_monitor = LegStatusMonitor()
status_monitor.run()

# Monitor for alerts (separate from status)
alert_monitor = LegAlertMonitor()
alert_monitor.run()
```

## Dependencies

- pandas: CSV data handling
- json: Status file management
- core.BaseMonitor: Template method pattern
- notifiers: Email notification classes
"""

__all__ = [
    "LegDataUpdate",
    "LegStatusMonitor",
    "LegAlertMonitor",
    "FaultStatusMonitor",
]


def __getattr__(name):
    """延迟导入，避免相对导入问题"""
    if name == "LegDataUpdate":
        from .leg_data_update import LegDataUpdate

        return LegDataUpdate
    elif name == "LegStatusMonitor":
        from .leg_status_monitor import LegStatusMonitor

        return LegStatusMonitor
    elif name == "LegAlertMonitor":
        from .leg_alert_monitor import LegAlertMonitor

        return LegAlertMonitor
    elif name == "FaultStatusMonitor":
        from .fault_status_monitor import FaultStatusMonitor

        return FaultStatusMonitor
    raise AttributeError(f"module {__name__} has no attribute {name}")

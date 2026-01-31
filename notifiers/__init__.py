"""
Notifiers Module - 通知器模块

This module provides email notification capabilities for flight monitoring system.
All notifiers inherit from BaseNotifier and use hash-based deduplication.

## Components（组件列表）

### task_notifier.py - TaskNotifier
Task notification for data fetching operations.
Notifies when scheduled tasks complete or fail.

### leg_status_notifier.py - LegStatusNotifier
Sends notifications for flight leg status changes (OUT/OFF/ON/IN).

Features:
- Converts Beijing time to Vietnam time for display
- Shows previous and current times for comparison
- Multi-aircraft batch notification

### fault_status_notifier.py - FaultStatusNotifier
Sends notifications for aircraft fault data changes.

Features:
- Lists new faults (appeared since last check)
- Lists removed faults (disappeared since last check)
- Shows current active fault count
- Applies fault filtering rules

### leg_alert_notifier.py - LegAlertNotifier
Sends alert notifications for abnormal flight conditions.

Alert types:
1. Duration Alert: Flight exceeds threshold duration
2. Freshness Alert: Data hasn't been updated recently

## Architecture（架构设计）

### BaseNotifier
Abstract base class (core/base_notifier.py) providing:
- Hash-based content deduplication (prevents duplicate emails)
- Gmail SMTP integration
- HTML email formatting
- Multi-recipient support
- State tracking (saves last sent hash)

Template method pattern:
- generate_content(data) - Abstract, implemented by subclasses
- check_if_new_content() - Hash comparison
- send_email() - Send via Gmail SMTP
- save_current_hash() - Update state

## Configuration（配置）

### Gmail Settings
Configured in config.ini or .env:
```ini
[gmail]
sender_email = your_email@gmail.com
app_password = your_app_password
recipients = recipient1@domain.com,recipient2@domain.com
sender_name = Flight Status Monitor
```

### State Files（状态文件）
Each notifier maintains a state file:
- data/task_notifier_hash.json
- data/leg_status_hash.json
- data/fault_status_hash.json
- data/leg_alert_hash.json

## Dependencies

- smtplib: Gmail SMTP integration
- email.mime: Email message construction
- hashlib: MD5 hash generation
- core.BaseNotifier: Base class
- config.ConfigLoader: Gmail configuration
"""

__all__ = ["TaskNotifier", "LegStatusNotifier", "FaultStatusNotifier", "LegAlertNotifier"]


def __getattr__(name):
    """延迟导入，避免相对导入问题"""
    if name == "TaskNotifier":
        from .task_notifier import TaskNotifier

        return TaskNotifier
    elif name == "LegStatusNotifier":
        from .leg_status_notifier import LegStatusNotifier

        return LegStatusNotifier
    elif name == "FaultStatusNotifier":
        from .fault_status_notifier import FaultStatusNotifier

        return FaultStatusNotifier
    elif name == "LegAlertNotifier":
        from .leg_alert_notifier import LegAlertNotifier

        return LegAlertNotifier
    raise AttributeError(f"module {__name__} has no attribute {name}")

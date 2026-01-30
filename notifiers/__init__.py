"""
Notifiers Module - 通知器模块

This module provides email notification capabilities for flight monitoring system.
All notifiers inherit from BaseNotifier and use hash-based deduplication to prevent
duplicate notifications for the same content.

## Architecture（架构设计）

### BaseNotifier
Abstract base class for all notifiers (core/base_notifier.py).
Provides:
- Hash-based content deduplication (prevents duplicate emails)
- Gmail SMTP integration
- HTML email formatting
- Multi-recipient support
- State tracking (saves last sent hash)

All notifiers follow template method pattern:
```
run(data)
  ↓
generate_content(data)  # Abstract - implemented by subclasses
  ↓
check_if_new_content()  # Hash comparison
  ↓ (if changed)
send_email()           # Send via Gmail SMTP
  ↓
save_current_hash()    # Update state
```

## Notifiers（通知器列表）

### TaskNotifier
Task notification for data fetching operations.
Notifies when scheduled tasks complete or fail.

Use cases:
- Daily data fetch completed
- Scheduled maintenance started/completed
- Background task status updates

Usage:
```python
from notifiers import TaskNotifier
notifier = TaskNotifier()
notifier.run({
    "task": "Leg Data Fetch",
    "status": "completed",
    "records": 150,
    "timestamp": "2026-01-30 08:00"
})
```

### LegStatusNotifier
Sends notifications for flight leg status changes (OUT/OFF/ON/IN).

Triggers when:
- OUT time appears (pushback started)
- OFF time appears (airborne)
- ON time appears (landed)
- IN time appears (at gate)

Features:
- Converts Beijing time to Vietnam time for display
- Shows previous and current times for comparison
- Highlights changed fields
- Multi-aircraft batch notification

Email format:
```
Subject: [航段状态更新] VJ105 - 机号1
Body:
  航班号: VJ105
  飞机号: 机号1
  日期: 2026-01-30

  ✅ 状态更新:
    OUT: 06:45 (Vietnam time)
    OFF: 06:52
    ON: 08:30
    IN: 08:45
```

Usage:
```python
from notifiers import LegStatusNotifier
notifier = LegStatusNotifier()
notifier.run(leg_data_df)
```

### FaultStatusNotifier
Sends notifications for aircraft fault data changes.

Features:
- Lists new faults (appeared since last check)
- Lists removed faults (disappeared since last check)
- Shows current active fault count
- Applies fault filtering rules before notification

Email format:
```
Subject: [故障状态更新] 机号1 - 2026-01-30
Body:
  飞机号: 机号1
  日期: 2026-01-30
  当前故障数: 3

  新增故障 (2):
  - 27-10: LGCIU FAULT
  - 27-11: LGCIU FAULT

  消失故障 (1):
  - 24-10: HYD SYS FAULT
```

Usage:
```python
from notifiers import FaultStatusNotifier
notifier = FaultStatusNotifier()
notifier.run(fault_data_df)
```

### LegAlertNotifier
Sends alert notifications for abnormal flight conditions.

Alert types:
1. **Duration Alert**: Flight exceeds threshold duration
   - Example: 110min scheduled flight takes >150min

2. **Freshness Alert**: Data hasn't been updated recently
   - Example: No data update for 30 minutes during operation

Email format:
```
Subject: [⚠️ 告警] VJ105 - 飞行时间异常
Body:
  航班号: VJ105
  飞机号: 机号1
  计划起飞: 07:45
  计划飞行时长: 110分钟

  ⚠️ 告警详情:
    当前飞行时长: 155分钟
    超出阈值: +45分钟
    最后更新: 08:30
```

Usage:
```python
from notifiers import LegAlertNotifier
notifier = LegAlertNotifier()
notifier.run(alert_data)
```

## Configuration（配置）

### Gmail Settings
Configured in config.ini or .env:

```ini
[gmail]
sender_email = your_email@gmail.com
app_password = your_app_password  # Gmail app-specific password
recipients = recipient1@domain.com,recipient2@domain.com
sender_name = Flight Status Monitor
```

⚠️ **Important**: Use Gmail app-specific password, NOT account password.
Generate at: https://myaccount.google.com/apppasswords

### State Files（状态文件）
Each notifier maintains a state file to track last sent hash:

```
data/
├── task_notifier_hash.json      # TaskNotifier state
├── leg_status_hash.json         # LegStatusNotifier state
├── fault_status_hash.json       # FaultStatusNotifier state
└── leg_alert_hash.json          # LegAlertNotifier state
```

## Hash-Based Deduplication（哈希去重）

### How It Works
1. Generate MD5 hash of content (or JSON representation)
2. Compare with last saved hash
3. Only send email if hash differs
4. Save new hash after sending

### Benefits
- Prevents duplicate notifications for same data
- Reduces email spam
- Tracks content changes efficiently
- State persists across scheduler restarts

### Implementation
```python
# In BaseNotifier
def check_if_new_content(self, content: str) -> bool:
    current_hash = hashlib.md5(content.encode()).hexdigest()
    last_hash = self.load_last_hash()
    return current_hash != last_hash
```

## Usage Examples（使用示例）

### Basic Notification
```python
from notifiers import LegStatusNotifier

notifier = LegStatusNotifier()
notifier.run(leg_data_df)
```

### With Custom Data
```python
from notifiers import TaskNotifier

notifier = TaskNotifier()
notifier.run({
    "task": "Data Export",
    "status": "completed",
    "records": 1500,
    "file": "export_2026-01-30.csv"
})
```

### Testing (Mock Mode)
```python
from notifiers import LegStatusNotifier
from unittest.mock import patch

notifier = LegStatusNotifier()

# Mock send_email to prevent actual email sending
with patch.object(notifier, 'send_email'):
    notifier.run(leg_data_df)
    # Verify email content without sending
```

## Error Handling（错误处理）

### EmailSendError
Raised when email sending fails.

Common causes:
- Network connectivity issues
- Gmail authentication failure
- Invalid recipient addresses
- SMTP server issues

All notifiers catch EmailSendError and log errors:
```python
try:
    self.send_email(content)
except EmailSendError as e:
    self.logger(f"Failed to send email: {e}", "ERROR")
```

## Dependencies（依赖项）

- smtplib: Gmail SMTP integration
- email.mime: Email message construction
- hashlib: MD5 hash generation
- core.BaseNotifier: Base class with template methods
- config.ConfigLoader: Gmail configuration
- exceptions.EmailSendError: Email error handling

## Related Documentation（相关文档）

- core/base_notifier.py - BaseNotifier implementation
- docs/architecture/project-structure.md - Architecture overview
- docs/guides/security-setup.md - Gmail app password setup

## Best Practices（最佳实践）

1. **Always use hash-based deduplication** - Prevents spam
2. **Clear state files when needed** - Delete hash JSON files to force notification
3. **Test email format** - Use test recipients before production
4. **Monitor email quota** - Gmail has daily sending limits
5. **Handle errors gracefully** - Log and continue, don't crash scheduler
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

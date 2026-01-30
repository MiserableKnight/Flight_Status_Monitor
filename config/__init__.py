"""
Configuration Module - 配置管理模块

This module provides unified configuration loading and management for the entire system.
Supports environment variable overrides for sensitive credentials.

## Configuration Loading（配置加载）

### load_config()
Main entry point for loading configuration.
Returns ConfigLoader instance with all configuration sections.

Features:
- Environment variable priority (.env file overrides config.ini)
- Secure credential handling
- Type conversion (int, str, list)
- Default value support
- Validation

Usage:
```python
from config import load_config

config = load_config()
credentials = config.get_credentials()
gmail_config = config.get_gmail_config()
aircraft_list = config.get_aircraft_list()
```

### get_aircraft_mapping()
Utility function to get aircraft tail number mapping.
Maps internal aircraft codes to display names.

Usage:
```python
from config import get_aircraft_mapping

mapping = get_aircraft_mapping()
# Returns: {"B-1234": "机号1", "B-5678": "机号2", ...}
```

## Configuration Files（配置文件）

### config.ini
Main configuration file (not committed to git).
Sections:
- [credentials]: System username/password (deprecated, use .env)
- [paths]: Chrome user data path
- [aircraft]: Aircraft list (comma-separated)
- [scheduler]: Operating hours and check interval
- [gmail]: Email notification settings (deprecated, use .env)

### .env
Environment variables for sensitive data (not committed to git).
Overrides config.ini values.

Variables:
```bash
SYSTEM_USERNAME=411613
SYSTEM_PASSWORD=your_password
GMAIL_SENDER_EMAIL=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
GMAIL_RECIPIENTS=recipient@domain.com
GMAIL_SENDER_NAME=Flight Monitor
```

### .env.template
Template file (committed to git) for reference.

## Configuration Sections（配置节）

### Credentials（登录凭证）
- system_username: System login username
- system_password: System login password

Priority: .env > config.ini

### Paths（路径配置）
- user_data_path: Chrome user data directory

### Aircraft（飞机配置）
- aircraft_list: Comma-separated tail numbers
  Example: B-1234,B-5678,B-9010

### Scheduler（调度器配置）
- start_time: Operating hours start (HH:MM format)
- end_time: Operating hours end (HH:MM format)
- check_interval: Data fetch interval (seconds)
  Default: 60 seconds

### Gmail（邮件配置）
- sender_email: Gmail sender address
- app_password: Gmail app-specific password (NOT account password)
- recipients: Comma-separated recipient list
- sender_name: Email sender display name

Priority: .env > config.ini

## Flight Schedule Configuration（航班计划）

### flight_schedule.py
Defines flight schedules (Beijing time).

Structure:
```python
FLIGHT_SCHEDULES = {
    "VJ105": {
        "scheduled_departure": "07:45",  # Beijing time
        "duration_minutes": 110,
        "route": "HAN-VCS"
    }
}
```

Functions:
- FlightSchedule.to_vietnam_time(): Convert Beijing time to Vietnam time
- FlightSchedule.format_vietnam_time(): Format datetime for display

### aircraft_cfg.py
Aircraft tail number mapping.

Maps internal codes to display names:
```python
AIRCRAFT_MAPPING = {
    "B-1234": "机号1",
    "B-5678": "机号2"
}
```

## Fault Filter Configuration（故障过滤规则）

### fault_filter_rules.csv
Multi-column AND rules for filtering faults.

Format:
```csv
fault_code,description,ata_chapter
27-10,LGCIU FAULT,24
```

- Each row: AND condition (all columns must match)
- Multiple rows: OR relationship (any row can match)

### fault_group_filter_rules.csv
Filters faults that appear simultaneously.

Format:
```csv
fault_code1,fault_code2
27-10,27-11
```

## Security（安全机制）

### Environment Variable Priority
Sensitive credentials prioritize .env over config.ini:

```
.env (highest) → config.ini → default value (lowest)
```

### Deployment
- Development: Use .env file (git-ignored)
- Production: Use system environment variables or .env file
- Team: Each member maintains their own .env

### File Permissions
- .env: chmod 600 (owner read/write only)
- config.ini: Can contain non-sensitive config only

## Usage Example（完整示例）

```python
from config import load_config, get_aircraft_mapping
from config.flight_schedule import FlightSchedule

# Load configuration
config = load_config()

# Get credentials (from .env or config.ini)
username, password = config.get_credentials()

# Get Gmail config
gmail = config.get_gmail_config()
print(f"Sending from: {gmail['sender_email']}")

# Get aircraft list
aircraft_list = config.get_aircraft_list()
print(f"Monitoring: {aircraft_list}")

# Get flight schedule
schedule = FlightSchedule.get_schedule("VJ105")
print(f"Departure: {schedule['scheduled_departure']}")

# Convert to Vietnam time for email display
from datetime import datetime
bj_time = datetime(2026, 1, 30, 7, 45)
vn_time = FlightSchedule.to_vietnam_time(bj_time)
print(f"Vietnam time: {vn_time}")  # 06:45
```

## Related Documentation

- docs/guides/security-setup.md - Detailed security setup guide
- docs/guides/timezone.md - Timezone strategy and conversion
- .env.template - Configuration template

## Dependencies

- python-dotenv: Environment variable loading
- configparser: INI file parsing
- typing: Type hints
"""

from .config_loader import get_aircraft_mapping, load_config

__all__ = ["load_config", "get_aircraft_mapping"]

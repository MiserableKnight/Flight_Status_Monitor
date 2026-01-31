"""
Configuration Module - 配置管理模块

This module provides unified configuration loading and management for the entire system.
Supports environment variable overrides for sensitive credentials.

## Components（组件列表）

### config_loader.py
ConfigLoader class providing unified configuration loading.
Features:
- Environment variable priority (.env overrides config.ini)
- Secure credential handling
- Type conversion and validation
- Default value support

### constants.py
Project-wide constants and enumerated values.
Defines:
- Status codes and mappings
- Configuration thresholds
- Common constants used across modules

### flight_schedule.py
Flight schedule configuration (Beijing time).
Defines:
- FLIGHT_SCHEDULES: Flight timing and route information
- ROUTE_CHAINS: Sequential flight route definitions
- Time conversion utilities (Beijing ↔ Vietnam)
- Flight phase calculations

### flight_phase_mapping.py
Flight phase status mappings and transitions.
Defines:
- Flight phase enumerations (SCHEDULED, PUSHBACK, AIRBORNE, etc.)
- Status transition rules
- Phase detection logic

### aircraft_cfg.py
Aircraft tail number mapping.
Maps internal codes to display names.

## Configuration Loading（配置加载）

### load_config()
Main entry point for loading configuration.
Returns ConfigLoader instance with all configuration sections.

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

Usage:
```python
from config import get_aircraft_mapping

mapping = get_aircraft_mapping()
# Returns: {"B-1234": "机号1", "B-5678": "机号2", ...}
```

## Configuration Files（配置文件）

### config.ini
Main configuration file (not committed to git).
Sections: credentials, paths, aircraft, scheduler, gmail

### .env
Environment variables for sensitive data (not committed to git).
Overrides config.ini values.

### fault_filter_rules.csv & fault_group_filter_rules.csv
Fault filtering rules for monitoring system.

## Security（安全机制）

### Environment Variable Priority
```
.env (highest) → config.ini → default value (lowest)
```

### Deployment
- Development: Use .env file (git-ignored)
- Production: Use system environment variables
- Team: Each member maintains their own .env

## Usage Example（完整示例）

```python
from config import load_config, get_aircraft_mapping
from config.flight_schedule import FlightSchedule

# Load configuration
config = load_config()
credentials = config.get_credentials()
gmail = config.get_gmail_config()
aircraft_list = config.get_aircraft_list()

# Get flight schedule and convert time
schedule = FlightSchedule.get_flight_info("VJ105")
bj_time = FlightSchedule.get_scheduled_departure_datetime("VJ105")
vn_time = FlightSchedule.to_vietnam_time(bj_time)
```

## Related Documentation

- docs/guides/security-setup.md - Security setup guide
- docs/guides/timezone.md - Timezone strategy
- .env.template - Configuration template
"""

from .config_loader import get_aircraft_mapping, load_config

__all__ = ["load_config", "get_aircraft_mapping"]

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ CRITICAL: Always Use Virtual Environment

**Python Virtual Environment Location:** `venv/`

** ALWAYS use the virtual environment Python for ALL commands:**

```bash
# Windows - Use these commands:
venv\Scripts\python.exe
venv\Scripts\pytest.exe
venv\Scripts\ruff.exe

# Example:
venv\Scripts\python.exe -m pytest tests/test_data_freshness.py
venv\Scripts\python.exe bin/run_leg_scheduler.py
```

**DO NOT use:** `python`, `pytest`, `ruff` directly (they use system Python, not venv)

**Reason:** Project dependencies are installed in the virtual environment. Using system Python will cause ModuleNotFoundError.

## Project Overview

Flight status monitoring system for VietJet C909 aircraft operations. Uses DrissionPage (browser automation framework) to monitor leg data (OUT/OFF/ON/IN times) and fault data from a web interface, with email notifications via Gmail.

## Development Commands

```bash
# Linting and formatting (uses Ruff)
venv\Scripts\ruff.exe check .                    # Run linter
venv\Scripts\ruff.exe check . --fix              # Auto-fix linting issues
venv\Scripts\ruff.exe format .                   # Format code
venv\Scripts\python.exe -m pre_commit run --all-files  # Run pre-commit hooks

# Run schedulers
venv\Scripts\python.exe bin/run_leg_scheduler.py      # Leg data monitoring (port 9222)
venv\Scripts\python.exe bin/run_fault_scheduler.py    # Fault monitoring (port 9333)

# Module execution (alternative)
venv\Scripts\python.exe -m schedulers.leg_scheduler
venv\Scripts\python.exe -m schedulers.fault_scheduler

# Run tests
venv\Scripts\pytest.exe tests/
venv\Scripts\python.exe -m pytest tests/test_fault_filter.py -v
```

## Architecture

### Dual Scheduler Design

The system uses **two independent schedulers** running on different Chrome debugging ports:

- **LegScheduler** (port 9222): Monitors flight leg status (OUT/OFF/ON/IN)
- **FaultScheduler** (port 9333): Monitors aircraft fault data

Each scheduler has its own Chrome instance, browser connection, and monitoring cycle.

### Layered Architecture

```
Schedulers (orchestration)
    ↓
Fetchers (data extraction) → Processors (data processing) → Notifiers (alerts)
    ↓                           ↓                              ↓
BaseFetcher (shared browser   BaseStatusMonitor            BaseNotifier
 connection management)      (hash-based change detection)
```

### Key Base Classes

- **BaseScheduler** ([schedulers/base_scheduler.py](schedulers/base_scheduler.py)): Abstract base for schedulers with dependency injection support, reconnection logic, and main loop template
- **BaseFetcher** ([fetchers/base_fetcher.py](fetchers/base_fetcher.py)): Manages Chrome debug port connections, login via LoginManager, and browser state
- **BaseStatusMonitor** ([core/base_monitor.py](core/base_monitor.py)): Template method pattern for status monitoring - reads data, generates content, compares hash, sends notification
- **BaseNotifier** ([core/base_notifier.py](core/base_notifier.py)): Email notification with hash-based deduplication

### Dependency Injection Pattern

Most classes support optional dependency injection:

```python
# With DI (for testing)
scheduler = LegScheduler(config_loader=mock_config, logger=mock_logger)

# Without DI (production - auto-creates instances)
scheduler = LegScheduler()
```

### Browser Connection Management

- **BrowserHandler** ([core/browser_handler.py](core/browser_handler.py)): Low-level ChromiumPage connection to debug ports
- **BaseFetcher._browsers**: Class-level dict caching browser connections by port
- Auto-reconnect: If page connection fails, clears cache and reconnects (handles computer sleep/wake)

## Smart Navigation System

**Navigator** ([core/navigator.py](core/navigator.py)) detects page state and intelligently navigates:

```
PageState detection: NEED_LOGIN | ALREADY_TARGET | IN_SYSTEM | OUT_SYSTEM | UNKNOWN
    ↓
smart_navigate() with optional login callback
```

Login keywords are configurable in `config.ini` under `[urls][login_keywords]`.

## Flight Tracking Logic

**FlightTracker** ([core/flight_tracker.py](core/flight_tracker.py)) tracks each aircraft's flight phase:

```
FlightPhase: SCHEDULED → PUSHBACK → AIRBORNE → LANDED → IN_GATE
```

Key method: `should_monitor_leg_first(current_time)` - decides whether to prioritize Leg page or Fault page monitoring based on:
1. Aircraft needing arrival monitoring (airborne + past scheduled arrival)
2. Ground aircraft past scheduled departure time
3. Defaults to Leg page if no aircraft airborne

## Timezone Strategy

**Critical**: All internal time uses **Beijing Time (UTC+8)**

- Data storage: Beijing time
- Scheduling logic: Beijing time
- Email display: Converted to Vietnam Time (Beijing - 1 hour)

See [docs/TIMEZONE.md](docs/TIMEZONE.md) for details.

## Configuration

### config.ini Structure

```ini
[credentials]
username / password           # Login credentials

[paths]
user_data_path                # Chrome user data directory

[aircraft]
aircraft_list                 # Comma-separated aircraft tail numbers

[scheduler]
start_time / end_time         # Operating hours (HH:MM format)

[gmail]
sender_email / app_password   # Gmail app-specific password (NOT account password)
recipients / sender_name
```

### Flight Schedule Configuration

**config/flight_schedule.py**: Defines flight schedules (Beijing time)

```python
FLIGHT_SCHEDULES = {
    "VJ105": {
        "scheduled_departure": "07:45",  # Beijing time
        "duration_minutes": 110,
        "route": "HAN-VCS"
    }
}
```

### Fault Filter Rules

- **config/fault_filter_rules.csv**: Multi-column AND rules (rows = OR relationship)
- **config/fault_group_filter_rules.csv**: Filters faults that appear simultaneously

## Running the System

### Prerequisites

1. Chrome in debug mode (required for DrissionPage):
   ```bash
   chrome.exe --remote-debugging-port=9222 --user-data-dir="path/to/chrome_debug"
   ```

2. Gmail app-specific password (not account password)

### Startup Process

1. Start Chrome on port 9222 (for leg monitoring)
2. Start Chrome on port 9333 (for fault monitoring)
3. Run both schedulers (order doesn't matter - they wait until `start_time`)

### Batch Files

- **bin/leg_monitor.bat**: Starts leg scheduler with port 9222
- **bin/faults_monitor.bat**: Starts fault scheduler with port 9333

## Testing

Test files in [tests/](tests/):

- **test_fault_filter.py**: Fault filtering logic tests
- **test_abnormal.py**: Diversion detection tests
- **test_dependency_injection.py**: DI pattern validation
- **test_route_chain.py**: Flight route chain tests
- **send_test_fault_email.py**: Manual fault email testing

## Important Implementation Notes

1. **Browser connection reuse**: BaseFetcher caches connections by port in class variable `_browsers`
2. **Hash-based deduplication**: Both monitors use MD5 hash of content to detect changes
3. **Chinese column names**: Leg data CSV uses Chinese column names (日期, 执飞飞机, 航班号, OUT/OFF/ON/IN)
4. **Sys.path manipulation**: Project uses `sys.path.insert(0, project_root)` in many files
5. **Ruff exceptions**: E402 (imports not at top) and B008 (function calls as defaults) are ignored due to project patterns
6. **Log rotation**: Logs in `logs/` directory retained for 24 hours only
7. **Data files**: Daily raw data in `data/daily_raw/`, cumulative data in `data/leg_data.csv`

## Interface Contracts

Core interfaces defined in [interfaces/interfaces.py](interfaces/interfaces.py):

- **IFetcher**: connect_browser(), smart_login(), get_today_date(), navigate_to_target_page(), save_to_csv()
- **ILogger**: Callable logger with level parameter
- **IConfigLoader**: get_all_config(), get_config(section)
- **IScheduler**: connect_browser(), login(), fetch_data(), get_check_interval(), run()

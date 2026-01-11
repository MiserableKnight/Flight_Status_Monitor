# 航段数据监控系统

## 项目简介

自动化航段数据监控和状态跟踪系统，支持实时监控航段状态变化（起飞、降落、备降等异常），并通过Gmail发送通知。

## ⚠️ 技术架构说明（重要）

**核心技术栈：**
- **浏览器自动化框架**: DrissionPage（不是 Playwright！）
  - 所有数据抓取模块使用 DrissionPage 的 ChromiumPage
  - 使用 ChromiumOptions 连接到已启动的 Chrome 调试端口（9222）
- **代码风格**: 函数式脚本（非类风格）
  - `leg_fetcher.py` 是独立可运行脚本
  - 通过 `main()` 函数执行，支持命令行参数传递日期
- **调度方式**: 使用 subprocess 调用独立脚本
  - `main_scheduler.py` 不直接操作浏览器
  - 通过 subprocess.run() 执行 fetcher 脚本

**架构设计：**
- **fetchers/** - 数据抓取层，负责从网页获取原始数据
- **processors/** - 数据处理层，负责数据更新和状态监控
- **core/** - 核心系统层，提供通用功能模块

## 项目结构

```
Flight_Status_Monitor/
├── config/                      # 配置目录
│   ├── __init__.py
│   ├── config.ini               # 核心配置文件（使用 config.ini.example 作为模板）
│   ├── config_loader.py         # 配置加载器
│   ├── aircraft_cfg.py          # 飞机号映射配置
│   └── flight_schedule.py       # 航班计划配置
│
├── core/                        # 核心系统模块
│   ├── __init__.py
│   ├── browser_handler.py       # 浏览器管理（ChromiumPage）
│   ├── navigator.py             # 智能导航系统
│   ├── notifier.py              # Gmail通知模块
│   ├── logger.py                # 日志记录系统
│   ├── flight_tracker.py        # 航班状态跟踪器
│   ├── abnormal_detector.py     # 异常检测器（备降检测）
│   └── leg_status_notifier.py   # 航段状态通知器
│
├── fetchers/                    # 数据抓取器
│   ├── __init__.py
│   ├── base_fetcher.py          # 抓取器基类
│   ├── login_manager.py         # 登录管理
│   ├── leg_fetcher.py           # 航段数据抓取
│   └── data_processor.py        # 数据处理器
│
├── processors/                  # 数据处理器
│   ├── __init__.py
│   ├── leg_data_update.py       # 数据更新处理
│   └── leg_status_monitor.py    # 状态监控处理
│
├── data/                        # 数据存储目录
│   ├── daily_raw/               # 每日原始数据
│   ├── backup/                  # 历史备份
│   └── leg_data.csv             # 航段数据汇总
│
├── docs/                        # 文档目录
│   ├── SCHEDULER_GUIDE.md       # 调度模式使用指南
│   └── TIMEZONE.md              # 时区策略说明
│
├── logs/                        # 系统日志（保留24小时）
│
├── main_scheduler.py            # 系统主调度器（使用 subprocess 调用脚本）
├── run_system.bat               # 一键启动脚本
├── requirements.txt             # 项目依赖（DrissionPage >= 4.0.0）
└── README.md                    # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

或使用国内镜像加速：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 配置系统

编辑 `config/config.ini` 文件，配置以下内容：

- **登录凭证**: `username` 和 `password`
- **浏览器路径**: `user_data_path`
- **监控飞机**: `aircraft_list`
- **调度时间**: `start_time` 和 `end_time`
- **Gmail通知** (可选): `sender_email` 和 `app_password`

### 3. 启动Chrome浏览器（调试模式）

在运行系统前，需要先启动Chrome浏览器的调试模式：

```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="D:\Code\Flight_Status_Monitor\chrome_debug"
```

或使用快捷方式，目标设置为：

```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="D:\Code\Flight_Status_Monitor\chrome_debug"
```

### 4. 运行系统

双击运行 `run_system.bat`，系统会显示运行模式选择菜单：

```
============================================================
🛫 航段数据监控系统
============================================================

请选择运行模式:

[1] 调度模式 - 自动定时监控数据 (06:30-21:00)
[2] 交互模式 - 手动选择抓取任务
[3] 退出

============================================================

请输入选择 (1-3):
```

#### 模式 1：调度模式（推荐用于生产环境）

调度模式会根据 `config.ini` 中配置的时间自动执行数据监控任务。

**更多详情请参考:** [docs/SCHEDULER_GUIDE.md](docs/SCHEDULER_GUIDE.md)

#### 模式 2：交互模式（推荐用于测试和手动操作）

交互模式允许您手动选择要执行的任务，适合测试和临时数据监控：

**交互菜单示例：**
```
🎯 交互式模式
============================================================
1. 抓取并更新航段数据（Fetch & Update Leg Data）
   - 抓取最新数据
   - 检测状态变化并更新
   - 自动发送邮件通知
2. 退出
============================================================

请选择操作 (1-2):
```

## 功能特性

### ✅ 已实现功能

1. **智能导航系统**
   - 自动检测页面状态
   - 智能跳转到目标模块
   - 自动处理登录超时

2. **航段数据监控**
   - 实时监控航段数据
   - 自动检测状态变化（起飞、降落）
   - 检测异常情况（备降等）
   - 支持多飞机监控

3. **智能状态检测**
   - 自动检测航段状态变化
   - 检测起飞和降落事件
   - 检测备降异常事件

4. **Gmail通知** (可选)
   - 状态变化通知
   - 异常事件通知
   - 备降告警通知

5. **日志系统**
   - 24小时日志保留
   - 自动清理过期日志

## 配置说明

### 调度时间配置

在 `config.ini` 的 `[scheduler]` 部分配置：

```ini
[scheduler]
start_time = 06:30              # 系统启动时间
end_time = 21:00                # 系统停止时间
```

### Gmail通知配置

如需启用邮件通知，需要：

1. 在Gmail设置中生成应用专用密码
2. 在 `config.ini` 的 `[gmail]` 部分配置：

```ini
[gmail]
sender_email = your_email@gmail.com
app_password = your_app_password
recipients = recipient1@example.com, recipient2@example.com
```

### 时区配置

**项目时间统一使用北京时间**

- **内部时间**: 统一使用北京时间 (UTC+8)
- **邮件展示**: 转换为越南时间显示 (北京时间-1小时)

**更多详情请参考:** [docs/TIMEZONE.md](docs/TIMEZONE.md)

## 常见问题

### Q1: 浏览器连接失败？

**A**: 确保Chrome浏览器已以调试模式启动，并且端口为9222。

### Q2: 登录失败？

**A**: 检查 `config.ini` 中的用户名和密码是否正确。

### Q3: Gmail邮件发送失败？

**A**: 确保已启用两步验证并生成了应用专用密码，不要使用账号密码。

### Q4: 如何查看系统日志？

**A**: 日志文件存储在 `logs/` 目录下，按日期命名（YYYY-MM-DD.log）。

## 开发说明

### 架构分层设计

项目采用 fetchers/processors 分层架构：

- **fetchers/** - 数据抓取层
  - 负责与浏览器交互，从网页获取原始数据
  - 数据保存到 `data/daily_raw/` 目录
  - 每个脚本可独立运行，通过 `main()` 函数执行

- **processors/** - 数据处理层
  - 读取原始数据进行处理和分析
  - 检测状态变化
  - 触发邮件通知

- **core/** - 核心系统层
  - 提供浏览器管理、导航、日志等通用功能
  - 被上层模块复用

### 添加新的数据抓取模块

1. 在 `fetchers/` 目录下创建新的 fetcher 脚本
2. 实现为独立可运行脚本，提供 `main()` 函数
3. 在 `main_scheduler.py` 中通过 subprocess 调用

### 添加新的数据处理流程

1. 在 `processors/` 目录下创建新的处理脚本
2. 实现数据处理逻辑
3. 在 `main_scheduler.py` 中调用新处理器

### 扩展通知方式

在 `core/notifier.py` 中添加新的通知类（如微信、钉钉等）。

## 版本历史

- **v3.1.1** (2026-01-11)
  - 添加 `docs/` 目录，整理项目文档
  - 优化 README.md，添加文档链接

- **v3.1** (2026-01-11)
  - 重构项目架构，采用 `fetchers/` 和 `processors/` 分层设计
  - 数据抓取和数据处理职责分离
  - 提升代码可维护性和可扩展性
  - 优化航段数据抓取流程，减少重复操作

- **v3.0** (2026-01-11)
  - 重构为专门的航段数据监控系统
  - 移除flight data和faults data相关功能
  - 专注于航段状态变化监控
  - 优化系统架构和模块化

- **v2.0** (2026-01-08)
  - 重构为模块化架构
  - 添加智能导航系统
  - 支持Gmail通知
  - 完善日志和错误处理

- **v1.0** (初始版本)
  - 基础数据抓取功能

## 许可证

本项目仅供内部使用。

## 联系方式

如有问题，请联系系统管理员。

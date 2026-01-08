# 航班数据抓取系统

## 项目简介

自动化航班数据抓取和监控系统，支持定时抓取航段数据、飞行数据（运力统计）和故障数据，并通过Gmail发送通知。

## ⚠️ 技术架构说明（重要）

**核心技术栈：**
- **浏览器自动化框架**: DrissionPage（不是 Playwright！）
  - 所有数据抓取模块使用 DrissionPage 的 ChromiumPage
  - 使用 ChromiumOptions 连接到已启动的 Chrome 调试端口（9222）
- **代码风格**: 函数式脚本（非类风格）
  - `leg_fetcher.py`, `flight_fetcher.py`, `faults_fetcher.py` 都是独立可运行脚本
  - 每个脚本通过 `main()` 函数执行，支持命令行参数传递日期
- **调度方式**: 使用 subprocess 调用独立脚本
  - `main_scheduler.py` 不直接操作浏览器
  - 通过 subprocess.run() 执行各个 fetcher 脚本

**数据抓取模块：**
1. **leg_fetcher.py** - 航段数据抓取
   - 目标页面: `lineLogController/index.html`
   - 数据内容: 航段详细信息（起飞/着陆机场、时间、油量等）
   - 保存文件: `data/daily_raw/leg_data_YYYY-MM-DD.csv`

2. **flight_fetcher.py** - 飞行数据/运力统计抓取
   - 目标页面: `lineLogNewController/indexSF.html`
   - 数据内容: 累计飞行时间、轮挡时间等统计数据
   - 保存文件: `data/daily_raw/flight_data_YYYY-MM-DD.csv`

3. **faults_fetcher.py** - 故障数据抓取
   - 目标页面: `integratedMonitor/index.html`
   - 数据内容: 飞机故障信息
   - 保存文件: `data/daily_raw/faults_data_YYYY-MM-DD.csv`

## 项目结构

```
flight_data_daily_get/
├── config/                      # 配置目录
│   ├── __init__.py
│   ├── config.ini               # 核心配置文件（使用 config.ini.example 作为模板）
│   ├── config_loader.py         # 配置加载器
│   └── aircraft_cfg.py          # 飞机号映射配置
│
├── core/                        # 核心系统模块（基于 DrissionPage）
│   ├── __init__.py
│   ├── browser_handler.py       # 浏览器管理（ChromiumPage）
│   ├── navigator.py             # 智能导航系统
│   ├── notifier.py              # Gmail通知模块
│   └── logger.py                # 日志记录系统
│
├── modules/                     # 业务逻辑模块（独立函数式脚本）
│   ├── __init__.py
│   ├── login_manager.py         # 登录管理
│   ├── leg_fetcher.py           # 航段数据抓取（新增）
│   ├── flight_fetcher.py        # 飞行数据/运力统计抓取
│   ├── faults_fetcher.py        # 故障数据抓取
│   └── data_processor.py        # 数据处理
│
├── data/                        # 数据存储目录
│   ├── daily_raw/               # 每日原始数据
│   ├── backup/                  # 历史备份
│   ├── flight_data.csv          # 飞行数据汇总
│   └── leg_data.csv             # 航段数据汇总
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
- **调度时间**: `flight_fetch_times` 和 `faults_fetch_times`
- **Gmail通知** (可选): `sender_email` 和 `app_password`

### 3. 启动Chrome浏览器（调试模式）

在运行系统前，需要先启动Chrome浏览器的调试模式：

```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="D:\Code\flight_data_daily_get\chrome_debug"
```

或使用快捷方式，目标设置为：

```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="D:\Code\flight_data_daily_get\chrome_debug"
```

### 4. 运行系统

双击运行 `run_system.bat`，系统会显示运行模式选择菜单：

```
============================================================
🛫 航班数据抓取系统
============================================================

请选择运行模式:

[1] 调度模式 - 自动定时抓取数据 (06:30-21:00)
[2] 交互模式 - 手动选择抓取任务
[3] 退出

============================================================

请输入选择 (1-3):
```

#### 模式 1：调度模式（推荐用于生产环境）

调度模式会根据 `config.ini` 中配置的时间自动执行数据抓取任务：

**工作流程：**
1. 系统启动后进入等待状态，等待到配置的 `start_time`
2. 在配置的时间点自动执行航班数据抓取（`flight_fetch_times`）
3. 在配置的时间点自动执行故障数据抓取（`faults_fetch_times`）
4. 到达 `end_time` 后自动停止
5. 发送每日汇总报告（如果配置了Gmail通知）

**适用场景：**
- 服务器环境长期运行
- 需要定时自动化抓取数据
- 无需人工干预的无人值守模式

**示例调度时间配置：**
```ini
[scheduler]
start_time = 06:30              # 早上6:30启动系统
end_time = 21:00                # 晚上9:00停止运行
flight_fetch_times = 07:00, 12:00, 18:00   # 7点、12点、18点抓取航班数据
faults_fetch_times = 08:00, 14:00, 20:00   # 8点、14点、20点抓取故障数据
```

#### 模式 2：交互模式（推荐用于测试和手动操作）

交互模式允许您手动选择要执行的任务，适合测试和临时数据抓取：

**工作流程：**
1. 系统进入交互式菜单
2. 显示可用的操作选项
3. 根据您的输入执行相应任务
4. 可以连续执行多个任务
5. 退出时发送汇总报告（如果配置了Gmail通知）

**交互菜单示例：**
```
🎯 交互式模式
============================================================
1. 抓取航段数据（Leg Data）
2. 抓取故障数据（Faults Data）
3. 抓取飞行数据（Flight Data - 运力统计）
4. 退出
============================================================

请选择操作 (1-4):
```

**操作说明：**

- **输入 1** - 立即执行航段数据抓取任务
  - 连接到已打开的Chrome浏览器（端口9222）
  - 自动导航到 `lineLogController/index.html`
  - 选择配置的飞机号（通过序列号筛选）
  - 设置日期为当天
  - 点击查询并获取航段数据（起飞/着陆机场、时间、油量等）
  - 保存至: `data/daily_raw/leg_data_YYYY-MM-DD.csv`
  - 发送通知（如果配置了Gmail）

- **输入 2** - 立即执行故障数据抓取任务
  - 连接到已打开的Chrome浏览器
  - 导航到综合监控页面 `integratedMonitor/index.html`
  - 选择配置的飞机号
  - 获取故障信息
  - 保存至: `data/daily_raw/faults_data_YYYY-MM-DD.csv`
  - 发送通知（如果配置了Gmail）

- **输入 3** - 立即执行飞行数据/运力统计抓取任务
  - 连接到已打开的Chrome浏览器
  - 导航到运力统计页面 `lineLogNewController/indexSF.html`
  - 选择配置的飞机号（使用飞机号下拉框）
  - 获取累计飞行时间、轮挡时间等统计数据
  - 保存至: `data/daily_raw/flight_data_YYYY-MM-DD.csv`
  - 发送通知（如果配置了Gmail）

- **输入 4** - 退出交互模式
  - 发送每日汇总报告（如果配置了Gmail）
  - 关闭系统

**适用场景：**
- 测试系统配置是否正确
- 临时需要手动抓取数据
- 调试和问题排查
- 不按固定时间运行的情况

**使用示例：**
```
请选择操作 (1-4): 1
============================================================
🚀 开始执行任务: 航段数据抓取
⏰ 时间: 2026-01-08 14:35:22
============================================================
🚀 开始抓取航段数据...
🎯 目标日期：2026-01-08
✅ 浏览器连接成功！

🎯 步骤1: 导航到航段数据页面
   ✅ 已在航段数据页面

🎯 步骤2: 选择飞机
   ✅ 找到'序列号:'标签
   ✅ 找到序列号下拉框
   🎯 开始选择目标飞机...
   ✅ 选择飞机: B-652G
   ✅ 选择飞机: B-656E
   ✅ 成功选择 2 架飞机

🎯 步骤3: 设置时间范围
   ✅ 开始时间设置为: 2026-01-08
   ✅ 结束时间设置为: 2026-01-08

🎯 步骤4: 点击【查询】
   ✅ 已点击查询按钮

⏳ 等待表格加载...
   ✅ 数据已加载 (2秒)

🎯 步骤6: 提取并保存数据
📊 开始提取表格数据...
   ✅ 找到数据容器
   ✅ 找到 4 行数据
   ✅ 成功提取 4 行数据

✅ 数据已保存到: data/daily_raw/leg_data_2026-01-08.csv
🎉 数据抓取完成！
📊 总行数: 5
✅ 任务 航段数据抓取 执行成功

请选择操作 (1-4): 4

👋 退出系统
📊 正在发送汇总报告...
```

## 功能特性

### ✅ 已实现功能

1. **智能导航系统**
   - 自动检测页面状态
   - 智能跳转到目标模块
   - 自动处理登录超时

2. **数据抓取**
   - 航班数据抓取（运力统计）
   - 故障数据抓取（综合监控）
   - 支持多飞机监控

3. **数据处理**
   - 自动保存每日原始数据
   - 累计值计算（飞行时间、轮挡时间）
   - 数据备份功能

4. **Gmail通知** (可选)
   - 任务成功通知
   - 任务失败通知
   - 每日汇总报告

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
flight_fetch_times = 07:00, 12:00, 18:00   # 航班数据抓取时间
faults_fetch_times = 08:00, 14:00, 20:00   # 故障数据抓取时间
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

### 添加新的数据抓取模块

1. 在 `modules/` 目录下创建新的fetcher类
2. 继承基类并实现 `fetch()` 方法
3. 在 `main_scheduler.py` 中集成新模块

### 扩展通知方式

在 `core/notifier.py` 中添加新的通知类（如微信、钉钉等）。

## 版本历史

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

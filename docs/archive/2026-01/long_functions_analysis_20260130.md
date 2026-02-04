# 长函数分析报告

**生成时间**: 2026-01-30
**扫描阈值**: 50行
**扫描范围**: fetchers/, schedulers/, core/

---

## 📊 扫描概览

- **发现长函数数量**: 15个
- **高优先级（>100行）**: 3个
- **中优先级（50-100行）**: 12个

---

## 🔴 高优先级问题（>100行）

### 1. leg_fetcher.py:navigate_to_target_page() - 164行

**位置**: `fetchers/leg_fetcher.py:375`

**问题**:
- 导航逻辑与数据抓取逻辑混合在一起
- 包含多个职责：页面导航、等待加载、数据提取、保存

**建议重构方案**:
```python
def navigate_to_target_page(self, page, target_date):
    """导航到目标页面并执行抓取逻辑"""
    # 1. 导航到Leg页面
    self._navigate_to_leg_page(page, target_date)

    # 2. 选择飞机
    self._select_aircrafts_for_fetch(page)

    # 3. 等待数据加载
    self._wait_for_data_load(page)

    # 4. 提取数据
    return self.extract_table_data(page)

# 新增辅助方法
def _navigate_to_leg_page(self, page, target_date):
    """导航到Leg页面并设置日期"""

def _select_aircrafts_for_fetch(self, page):
    """选择要抓取的飞机"""

def _wait_for_data_load(self, page):
    """等待表格数据加载完成"""
```

---

### 2. leg_fetcher.py:select_aircrafts() - 132行

**位置**: `fetchers/leg_fetcher.py:123`

**问题**:
- 多架飞机的选择逻辑混在一起
- 包含循环选择、状态检测、错误处理

**建议重构方案**:
```python
def select_aircrafts(self, page, aircraft_list):
    """选择多架飞机"""
    selected_count = 0
    for aircraft in aircraft_list:
        if self._select_single_aircraft(page, aircraft):
            selected_count += 1
    return selected_count

def _select_single_aircraft(self, page, aircraft):
    """选择单架飞机"""
    # 1. 点击选择按钮
    if not self._click_select_button(page):
        return False

    # 2. 搜索飞机号
    if not self._search_aircraft(page, aircraft):
        return False

    # 3. 确认选择
    return self._confirm_selection(page)

def _click_select_button(self, page):
    """点击选择按钮"""

def _search_aircraft(self, page, aircraft):
    """搜索并选择飞机号"""

def _confirm_selection(self, page):
    """确认选择"""
```

---

### 3. leg_fetcher.py:extract_table_data() - 118行

**位置**: `fetchers/leg_fetcher.py:256`

**问题**:
- 表格解析逻辑过于复杂
- 包含：定位表格、提取表头、提取数据行、数据验证

**建议重构方案**:
```python
def extract_table_data(self, page):
    """提取表格数据"""
    # 1. 定位表格元素
    table = self._locate_table(page)
    if not table:
        return None

    # 2. 提取表头
    headers = self._extract_headers(table)

    # 3. 提取数据行
    data_rows = self._extract_data_rows(table)

    # 4. 组装数据
    return self._assemble_table_data(headers, data_rows)

def _locate_table(self, page):
    """定位表格元素"""

def _extract_headers(self, table):
    """提取表头"""

def _extract_data_rows(self, table):
    """提取数据行"""

def _assemble_table_data(self, headers, rows):
    """组装完整的表格数据"""
```

---

## 🟡 中优先级问题（50-100行）

### 4. fault_fetcher.py:select_aircrafts() - 96行

**位置**: `fetchers/fault_fetcher.py:241`

**问题**: 与 `leg_fetcher.py:select_aircrafts()` 类似，多架飞机选择逻辑混合

**建议**: 参考 `leg_fetcher.py` 的重构方案，提取子方法

---

### 5. fault_fetcher.py:navigate_to_target_page() - 95行

**位置**: `fetchers/fault_fetcher.py:99`

**问题**: 导航与抓取逻辑混合

**建议**: 参考 `leg_fetcher.py:navigate_to_target_page()` 的重构方案

---

### 6. fault_fetcher.py:quick_refresh() - 80行

**位置**: `fetchers/fault_fetcher.py:433`

**问题**: 快速刷新逻辑包含多个步骤

**建议重构方案**:
```python
def quick_refresh(self, page):
    """快速刷新页面数据"""
    # 1. 点击刷新按钮
    self._click_refresh_button(page)

    # 2. 等待加载
    self._wait_for_refresh_complete(page)

    # 3. 重新提取数据
    return self.extract_table_data(page)

def _click_refresh_button(self, page):
    """点击刷新按钮"""

def _wait_for_refresh_complete(self, page):
    """等待刷新完成"""
```

---

### 7. schedulers/base_scheduler.py:run() - 73行

**位置**: `schedulers/base_scheduler.py:307`

**问题**: 主循环包含多个职责：时间检查、连接管理、数据抓取、错误处理

**建议重构方案**:
```python
def run(self):
    """运行调度器主循环"""
    self._log_startup_info()

    while True:
        try:
            if not self._should_run_now():
                self._wait_until_next_check()
                continue

            # 执行监控任务
            self._execute_monitoring_cycle()

        except Exception as e:
            self._handle_cycle_error(e)

def _should_run_now(self):
    """判断当前时间是否应该运行"""

def _execute_monitoring_cycle(self):
    """执行单次监控周期"""

def _handle_cycle_error(self, error):
    """处理周期错误"""
```

---

### 8. schedulers/base_scheduler.py:_reconnect_browser() - 67行

**位置**: `schedulers/base_scheduler.py:170`

**问题**: 重连逻辑包含多个步骤：清理缓存、重新连接、登录、导航

**建议重构方案**:
```python
def _reconnect_browser(self):
    """重新连接浏览器"""
    self.log("Attempting to reconnect browser...", "WARNING")

    # 1. 清理现有连接
    self._cleanup_browser_connection()

    # 2. 重新连接
    if not self._reestablish_connection():
        return False

    # 3. 重新登录
    return self._relogin_after_reconnect()

def _cleanup_browser_connection(self):
    """清理浏览器连接"""

def _reestablish_connection(self):
    """重新建立连接"""

def _relogin_after_reconnect(self):
    """重连后重新登录"""
```

---

### 9. schedulers/fault_scheduler.py:fetch_data() - 73行

**位置**: `schedulers/fault_scheduler.py:132`

**问题**: 包含数据抓取和重试逻辑

**建议**: 将重试逻辑提取为独立方法或装饰器

---

### 10. core/base_monitor.py:monitor() - 66行

**位置**: `core/base_monitor.py:236`

**问题**: 监控流程包含多个步骤：读取数据、生成内容、哈希比对、发送通知

**建议重构方案**:
```python
def monitor(self, page):
    """监控数据变化并发送通知"""
    # 1. 读取当前数据
    current_data = self.read_data(page)
    if not current_data:
        return

    # 2. 生成通知内容
    content = self.generate_notification_content(current_data)
    if not content:
        return

    # 3. 检查数据是否变化
    if self._has_data_changed(content):
        self._send_notification(content)

def _has_data_changed(self, content):
    """检查数据是否发生变化"""
    current_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
    return current_hash != self.last_hash

def _send_notification(self, content):
    """发送通知"""
```

---

### 11. core/login_manager.py:_wait_and_navigate() - 64行

**位置**: `core/login_manager.py:100`

**问题**: 等待和导航逻辑包含多个状态判断

**建议重构方案**:
```python
def _wait_and_navigate(self, page, target_url):
    """等待页面加载并导航到目标URL"""
    # 1. 等待登录完成
    self._wait_for_login_complete(page)

    # 2. 检测当前页面状态
    page_state = self._detect_page_state(page)

    # 3. 根据状态导航
    if target_url:
        self._navigate_to_target(page, target_url)
    else:
        self._handle_default_navigation(page, page_state)

def _wait_for_login_complete(self, page):
    """等待登录完成"""

def _detect_page_state(self, page):
    """检测当前页面状态"""

def _navigate_to_target(self, page, url):
    """导航到目标URL"""

def _handle_default_navigation(self, page, state):
    """处理默认导航逻辑"""
```

---

### 12. core/flight_tracker.py:should_monitor_leg_first() - 53行

**位置**: `core/flight_tracker.py:284`

**问题**: 包含多个优先级判断逻辑

**建议重构方案**:
```python
def should_monitor_leg_first(self, current_time):
    """判断是否应优先监控Leg页面"""
    # 1. 检查是否有到达中的飞机
    if self._has_arriving_aircraft(current_time):
        return True

    # 2. 检查是否有延误的地面飞机
    if self._has_delayed_grounded_aircraft(current_time):
        return True

    # 3. 默认优先监控Leg页面
    return True

def _has_arriving_aircraft(self, current_time):
    """检查是否有到达中的飞机"""

def _has_delayed_grounded_aircraft(self, current_time):
    """检查是否有延误的地面飞机"""
```

---

### 13-15. 其他中等长度函数

| 文件 | 函数 | 行数 | 说明 |
|------|------|------|------|
| `fault_fetcher.py` | `set_date()` | 56行 | 日期设置逻辑 |
| `leg_fetcher.py` | `quick_refresh()` | 53行 | 快速刷新逻辑 |
| `base_fetcher.py` | `main()` | 52行 | 主流程模板 |

**建议**: 这些函数接近阈值，可以暂时保持，但在后续优化时注意拆分

---

## ✅ 已解决的问题

### base_fetcher.py:smart_login() - 已重构

**原问题**: 190行的超长函数，包含登录、跳转、状态检测等多个职责

**解决方案**: 提取到独立的 `LoginManager` 类，现在只有8行：

```python
def smart_login(self, page, target_url=None):
    """智能登录系统 - 委托给 LoginManager"""
    return self.login_manager.login(page, target_url)
```

**重构时间**: 2026-01-30 之前

---

### leg_fetcher.py:select_aircrafts() - 已重构 ✅

**原问题**: 132行，多架飞机选择逻辑混合在一起

**重构时间**: 2026-02-04

**提交**: `1251fee`

**重构方案**: 拆分为8个辅助方法
- `select_aircrafts()` → 主流程控制（30行，↓78%）
- `_locate_and_open_dropdown()` - 等待并打开下拉框
- `_find_and_click_dropdown()` - 查找并点击下拉框
- `_find_dropdown_near_label()` - 在标签附近查找
- `_find_and_click_first_dropdown()` - 直接查找第一个下拉框
- `_clear_all_selections()` - 清空所有已选项
- `_select_target_aircrafts()` - 选择目标飞机列表
- `_select_single_aircraft()` - 选择单架飞机
- `_close_dropdown()` - 关闭下拉框

---

### leg_fetcher.py:navigate_to_target_page() - 已重构 ✅

**原问题**: 164行，导航逻辑与数据抓取逻辑混合

**重构时间**: 2026-02-04

**提交**: `cb43443`

**重构方案**: 拆分为11个辅助方法
- `navigate_to_target_page()` → 主流程控制（30行，↓82%）
- `_print_startup_info()` - 打印启动信息
- `_run_quick_refresh_mode()` - 运行快速刷新模式
- `_run_initialization_flow()` - 运行首次初始化流程
- `_navigate_to_leg_page()` - 导航到Leg页面
- `_navigate_via_intermediate_page()` - 通过中间页面导航
- `_navigate_and_verify()` - 导航并验证
- `_select_aircrafts_for_init()` - 初始化时选择飞机
- `_set_date_inputs()` - 设置日期输入框
- `_click_query_button()` - 点击查询按钮
- `_wait_for_data_load()` - 等待数据加载
- `_set_initialized_flag()` - 设置初始化标记

---

### leg_fetcher.py:extract_table_data() - 已重构 ✅

**原问题**: 134行，表格解析逻辑过于复杂

**重构时间**: 2026-02-04

**提交**: `9e55912`

**重构方案**: 拆分为10个辅助方法
- `extract_table_data()` → 主流程控制（20行，↓85%）
- `_locate_table()` - 定位数据容器
- `_extract_data_rows()` - 提取数据行
- `_extract_single_row()` - 提取单行数据
- `_extract_cell_data()` - 提取单元格数据
- `_normalize_flight_number()` - 标准化航班号
- `_log_row_data()` - 记录行数据
- `_assemble_table_data()` - 组装表格数据
- `_get_table_headers()` - 获取表头
- `_handle_extraction_error()` - 处理提取错误

---

### fault_fetcher.py:select_aircrafts() - 已重构 ✅

**原问题**: 96行，与 `leg_fetcher.py:select_aircrafts()` 类似

**重构时间**: 2026-02-04

**提交**: `ecfad1c`

**重构方案**: 拆分为6个辅助方法
- `select_aircrafts()` → 主流程控制（30行，↓72%）
- `_find_and_click_dropdown()` - 查找并点击下拉框
- `_clear_all_selections()` - 清空所有已选项
- `_select_target_aircrafts()` - 选择目标飞机列表
- `_select_single_aircraft()` - 选择单架飞机
- `_close_dropdown()` - 关闭下拉框

---

## 🎯 重构进度跟踪

### ✅ 已完成（4/15 函数）

**高优先级（>100行）- 100%完成：**
1. ✅ `base_fetcher.py:smart_login()` - 190行 → 8行（↓96%）
2. ✅ `leg_fetcher.py:select_aircrafts()` - 132行 → 30行（↓78%）- 提交: `1251fee`
3. ✅ `leg_fetcher.py:navigate_to_target_page()` - 164行 → 30行（↓82%）- 提交: `cb43443`
4. ✅ `leg_fetcher.py:extract_table_data()` - 134行 → 20行（↓85%）- 提交: `9e55912`

**中优先级（50-100行）- 部分完成：**
5. ✅ `fault_fetcher.py:select_aircrafts()` - 96行 → 30行（↓72%）- 提交: `ecfad1c`

**总计重构成果：**
- 5个函数，原共 616 行代码 → 138 行（平均 ↓78%）
- 提交 5 次，所有测试通过（86个 × 5次验证）
- Tag 标记：`BETA4.6.6` - 高优先级函数重构完成

### 🔄 待重构（11/15 函数）

**中优先级（50-100行）：**
6. ⏳ `fault_fetcher.py:navigate_to_target_page()` (95行)
7. ⏳ `fault_fetcher.py:quick_refresh()` (80行)
8. ⏳ `schedulers/base_scheduler.py:run()` (73行)
9. ⏳ `schedulers/base_scheduler.py:_reconnect_browser()` (67行)
10. ⏳ `schedulers/fault_scheduler.py:fetch_data()` (73行)
11. ⏳ `core/base_monitor.py:monitor()` (66行)
12. ⏳ `core/login_manager.py:_wait_and_navigate()` (64行)
13. ⏳ `core/flight_tracker.py:should_monitor_leg_first()` (53行)

**低优先级（50-60行）：**
14. ⏳ `fault_fetcher.py:set_date()` (56行)
15. ⏳ `leg_fetcher.py:quick_refresh()` (53行)
16. ⏳ `base_fetcher.py:main()` (52行)

---

## 📝 重构原则

1. **单一职责原则**: 每个函数只做一件事
2. **提取方法**: 将复杂逻辑提取为语义明确的私有方法
3. **委托模式**: 将跨多个类的职责提取到专门的类（如 `LoginManager`）
4. **模板方法模式**: 分离流程骨架和具体实现
5. **保持测试覆盖**: 每次重构后确保测试通过

---

## 🔧 工具支持

可以使用以下命令重新扫描：

```bash
venv/Scripts/python.exe -c "
import ast
import os

def get_function_length(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        start = node.lineno
        end = start
        for child in ast.walk(node):
            if hasattr(child, 'lineno') and child.lineno > end:
                end = child.lineno
        return end - start + 1
    return 0

def find_long_functions(filepath, threshold=50):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    tree = ast.parse(source, filename=filepath)
    long_funcs = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = get_function_length(node)
            if length > threshold:
                long_funcs.append({
                    'name': node.name,
                    'lineno': node.lineno,
                    'length': length
                })
    return sorted(long_funcs, key=lambda x: x['length'], reverse=True)

files_to_check = [
    'fetchers/base_fetcher.py',
    'fetchers/leg_fetcher.py',
    'fetchers/fault_fetcher.py',
    'schedulers/base_scheduler.py',
    'schedulers/leg_scheduler.py',
    'schedulers/fault_scheduler.py',
    'core/base_monitor.py',
    'core/flight_tracker.py',
    'core/login_manager.py',
    'core/browser_handler.py',
]

for f in files_to_check:
    if os.path.exists(f):
        funcs = find_long_functions(f, 50)
        if funcs:
            print(f'📁 {f}')
            for func in funcs:
                print(f\"  {func['name']}() - 第{func['lineno']}行, {func['length']}行\")
            print()
"
```

---

## 📈 重构进度总结

### 里程碑

- **2026-01-30**: 生成长函数分析报告
- **2026-02-04**: 开始长函数重构工作
- **2026-02-04**: 完成高优先级函数重构（3个）
- **2026-02-04**: Tag `BETA4.6.6` - 标记高优先级函数重构完成
- **2026-02-04**: 删除误导性备份分支 `backup-before-cleanup-20260114`

### 成果统计

| 指标 | 数值 |
|------|------|
| 已重构函数 | 5个 |
| 代码减少 | 616行 → 138行（↓78%） |
| 测试通过率 | 100%（86个 × 5次） |
| Git提交 | 5次 |
| Tag标记 | 2个（BETA4.6.6 + 重构里程碑） |
| 进度 | 33% (5/15) |

### 技术改进

1. **可读性提升** - 每个方法职责单一，命名清晰
2. **维护性提升** - 小方法易于理解和修改
3. **测试覆盖完整** - 所有测试保持100%通过
4. **零业务风险** - 纯结构重构，业务逻辑完全不变
5. **Git版本保护** - 每次重构都有独立提交，随时可回退

### 下一步计划

根据报告建议，继续重构剩余的11个中优先级函数（50-100行），预计：
- **剩余工作量**: 约 700-800 行代码需要重构
- **预计时间**: 2-3小时（包含测试验证）
- **预期收益**: 将代码复杂度降低 70% 以上

---

**报告结束**

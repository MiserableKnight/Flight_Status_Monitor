"""
航段数据抓取模块（优化版）

功能:
- 首次运行：导航到页面 → 设置机号 → 设置日期 → 点击查询
- 后续运行：只点击查询按钮（无需重复设置）
- 智能检测：自动判断是否已在目标页面且设置完成

优化策略:
- 减少页面跳转：停留在 lineLogController/index.html
- 减少表单操作：机号和日期只需设置一次
- 快速刷新：每分钟只点击查询按钮
"""

import os
import sys
import time

from config.constants import (
    DATA_REFRESH_WAIT_SECONDS,
    FRAMEWORK_LOAD_WAIT_SECONDS,
    PAGE_LOAD_WAIT_SECONDS,
)

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from fetchers.base_fetcher import BaseFetcher


class LegFetcher(BaseFetcher):
    """航段数据抓取器（优化版）"""

    def get_data_prefix(self):
        """返回数据文件前缀"""
        return "leg_data"

    def check_initialized(self, _target_date=None):
        """
        检查是否已初始化（使用状态标记，不检查页面）

        核心逻辑:
        1. 使用内部状态标记，避免检查页面的开销
        2. 首次运行时需要初始化
        3. 一旦初始化完成，后续直接使用快速刷新模式

        Args:
            _target_date: 目标日期（未使用，保留接口兼容性）

        Returns:
            bool: True 表示已初始化，False 表示需要初始化
        """
        print("\n" + "=" * 60)
        print("🔍 检查初始化状态")
        print("=" * 60)

        needs_init, minutes_left = self.should_force_refresh()

        if not needs_init:
            print("   ✅ 已初始化")
            print(f"   ⏳ 下次整页刷新: {minutes_left}分钟后")
            print("   ⚡ 使用快速刷新模式")
            print("=" * 60)
            return True

        if needs_init:
            print("   ❌ 未初始化")
            print("   → 需要执行初始化（导航+选机号+设日期+查询）")
            print("=" * 60)
            return False

    def quick_refresh(self, page):
        """
        快速刷新：只点击查询按钮

        核心逻辑:
        - 确保在分配的标签页上操作
        - 系统已在目标页面，机号和日期已设置
        - 只需要点击查询按钮刷新数据
        - 不需要任何页面跳转或表单填写

        Args:
            page: ChromiumPage 对象

        Returns:
            bool: 是否成功
        """
        print("\n" + "=" * 60)
        print("⚡ 快速刷新模式")
        print("=" * 60)
        print("💡 核心策略: 停留在当前页面，只点击查询按钮")

        # 点击查询按钮
        print("🔍 查找查询按钮...")
        query_btn = page.ele("tag:input@@value=查询 @@class=button_partial2")
        if query_btn:
            print("   ✅ 找到查询按钮")
            query_btn.click(by_js=True)
            print("   ✅ 已点击查询按钮")
        else:
            print("   ❌ 未找到查询按钮")
            return False

        # 等待数据刷新（快速模式）
        print("   ⏳ 等待数据刷新...")
        time.sleep(2)  # 快速刷新只需2秒

        # 等待数据容器更新
        print("🔍 检查数据更新...")
        for i in range(8):
            data_con = page.ele("tag:div@@id=dataCon1")
            if data_con:
                rows = data_con.eles("tag:div@@class=tr_title")
                if rows:
                    print(f"   ✅ 数据已刷新 (耗时: {i + 2}秒)")
                    print(f"   📊 当前数据行数: {len(rows)}")
                    print("=" * 60)
                    return True
            print(f"   ⏳ 等待中... ({i + 2}/8秒)")
            time.sleep(1)

        print("   ⚠️ 数据刷新超时，页面可能已卡住")
        print("=" * 60)
        return False

    def select_aircrafts(self, page, aircraft_list):
        """
        选择指定的飞机(通过序列号筛选)

        采用老代码的简单方式:
        1. 通过"序列号:"标签定位下拉框
        2. 点击 filter-option 下拉框
        3. 清空所有已选项
        4. 选择目标飞机
        """
        print("\n📋 开始选择飞机...")

        # 1. 等待并定位下拉框
        if not self._locate_and_open_dropdown(page):
            return False

        # 2. 等待下拉选项出现
        time.sleep(2)

        # 3. 清空所有已选项
        self._clear_all_selections(page)

        # 4. 选择目标飞机
        selected_count = self._select_target_aircrafts(page, aircraft_list)

        # 5. 关闭下拉框
        self._close_dropdown(page)

        # 6. 返回结果
        if selected_count > 0:
            print(f"   ✅ 成功选择 {selected_count} 架飞机")
            return True
        else:
            print("   ❌ 未能选择任何飞机")
            return False

    def _locate_and_open_dropdown(self, page):
        """等待并打开序列号下拉框"""
        print("   ⏳ 等待页面元素加载...")
        time.sleep(PAGE_LOAD_WAIT_SECONDS)

        # 通过标签定位或直接查找
        return self._find_and_click_dropdown(page)

    def _find_and_click_dropdown(self, page):
        """查找并点击序列号下拉框（通过标签或直接查找）"""
        # 方法1: 通过标签定位
        label_ele = page.ele("tag:p@text()=序列号:")
        if label_ele:
            print("   ✅ 找到标签: 序列号")
            dropdown = self._find_dropdown_near_label(label_ele)
            if dropdown:
                dropdown.click(by_js=True)
                time.sleep(1)
                print("   ✅ 已点击序列号下拉框")
                return True
            else:
                print("   ❌ 未找到序列号下拉框")
                return False
        else:
            # 方法2: 直接查找第一个下拉框
            return self._find_and_click_first_dropdown(page)

    def _find_dropdown_near_label(self, label_ele):
        """在标签附近查找下拉框"""
        aircraft_dropdown = None

        # 查找标签的父元素,然后找同级的下拉框
        parent = label_ele.parent()
        if parent:
            # 在父元素的同级或兄弟元素中查找 filter-option
            dropdown = parent.ele("tag:div@@class=filter-option")
            if dropdown:
                aircraft_dropdown = dropdown
                print("   ✅ 通过父元素找到下拉框")
            else:
                # 尝试查找父元素的下一个兄弟元素
                next_sibling = parent.next()
                if next_sibling:
                    dropdown = next_sibling.ele("tag:div@@class=filter-option")
                    if dropdown:
                        aircraft_dropdown = dropdown
                        print("   ✅ 通过兄弟元素找到下拉框")

        # 如果上面都失败,直接查找所有 filter-option
        if not aircraft_dropdown:
            all_dropdowns = label_ele.page.eles("tag:div@@class=filter-option")
            if len(all_dropdowns) > 0:
                aircraft_dropdown = all_dropdowns[0]
                print(f"   ✅ 找到 {len(all_dropdowns)} 个下拉框,使用第一个")

        return aircraft_dropdown

    def _find_and_click_first_dropdown(self, page):
        """直接查找并点击第一个下拉框"""
        print("   ❌ 未找到'序列号'标签")
        print("   🔍 尝试直接定位下拉框...")
        all_dropdowns = page.eles("tag:div@@class=filter-option")
        if len(all_dropdowns) > 0:
            print(f"   ✅ 找到 {len(all_dropdowns)} 个下拉框")
            all_dropdowns[0].click(by_js=True)
            time.sleep(1)
            print("   ✅ 已点击第一个下拉框")
            return True
        else:
            print("   ❌ 未找到任何下拉框")
            return False

    def _clear_all_selections(self, page):
        """清空所有已选择的飞机选项"""
        print("   🔍 清空所有已选项...")
        text_elements = page.eles("tag:span@@class=text")
        for ele in text_elements:
            parent = ele.parent()
            if parent:
                parent_attr = parent.attr("class") or ""
                if "selected" in parent_attr or "active" in parent_attr:
                    text = ele.text.strip()
                    print(f"   🔄 取消选择: {text}")
                    parent.click(by_js=True)
                    time.sleep(0.3)

        time.sleep(1)

    def _select_target_aircrafts(self, page, aircraft_list):
        """选择目标飞机列表"""
        print("   🎯 开始选择目标飞机...")
        selected_count = 0

        for aircraft in aircraft_list:
            if self._select_single_aircraft(page, aircraft):
                selected_count += 1

        return selected_count

    def _select_single_aircraft(self, page, aircraft):
        """选择单架飞机"""
        # 重新获取元素列表
        text_elements = page.eles("tag:span@@class=text")
        for ele in text_elements:
            text = ele.text.strip()
            # 使用包含匹配
            if aircraft in text:
                print(f"   ✅ 选择飞机: {text}")
                try:
                    parent = ele.parent()
                    if parent:
                        parent.click(by_js=True)
                    else:
                        ele.click(by_js=True)
                except (AttributeError, RuntimeError) as e:
                    # 元素点击相关的特定异常
                    print(f"   ⚠️ 点击元素失败: {type(e).__name__}")
                    self.log(f"点击飞机选择失败: {aircraft} - {e}", "WARNING")
                except Exception as e:
                    # 其他未预期的异常
                    print(f"   ⚠️ 点击失败: {type(e).__name__}: {e}")
                    self.log(f"点击飞机选择异常: {aircraft} - {e}", "WARNING")
                time.sleep(0.5)
                return True

        print(f"   ⚠️ 未找到飞机: {aircraft}")
        return False

    def _close_dropdown(self, page):
        """关闭下拉框"""
        try:
            page.ele("tag:body").click()
        except (AttributeError, RuntimeError):
            # 元素不存在或点击失败是可接受的，静默忽略
            pass

        time.sleep(1)

    def extract_table_data(self, page):
        """从表格中提取航段数据"""
        print("\n📊 开始提取表格数据...")

        try:
            # 1. 定位表格元素
            data_con = self._locate_table(page)
            if not data_con:
                return None

            # 2. 提取数据行
            data_rows = self._extract_data_rows(data_con)
            if not data_rows:
                return None

            # 3. 组装表格数据
            return self._assemble_table_data(data_rows)

        except Exception as e:
            return self._handle_extraction_error(e)

    def _locate_table(self, page):
        """定位数据容器"""
        data_con = page.ele("tag:div@@id=dataCon")
        if not data_con:
            print("   ❌ 未找到数据容器 #dataCon")
            return None

        print("   ✅ 找到数据容器")
        return data_con

    def _extract_data_rows(self, data_con):
        """提取数据行"""
        rows = data_con.eles("tag:div@@class=tr_title")
        print(f"   ✅ 找到 {len(rows)} 行数据")

        if not rows:
            print("   ❌ 表格为空")
            return None

        data_rows = []
        for i, row in enumerate(rows):
            row_data = self._extract_single_row(row, i)
            if row_data:
                data_rows.append(row_data)

        if not data_rows:
            print("   ❌ 未能提取到有效数据")
            return None

        return data_rows

    def _extract_single_row(self, row, row_index):
        """提取单行数据"""
        try:
            cells = row.eles("tag:div")
            row_data = []

            for cell in cells:
                cell_data = self._extract_cell_data(cell, row_data)
                if cell_data is not None:
                    row_data.append(cell_data)

            # 确保始终有15列（防御性检查）
            if len(row_data) < 15:
                row_data.extend([""] * (15 - len(row_data)))

            # 只取前15列
            row_data = row_data[:15]
            self._log_row_data(row_index, row_data)
            return row_data

        except (AttributeError, IndexError) as e:
            print(f"   ⚠️ 提取第{row_index + 1}行数据结构异常: {type(e).__name__}")
            self.log(f"行数据提取异常 (行{row_index + 1}): {e}", "DEBUG")
            return None
        except Exception as e:
            print(f"   ⚠️ 提取第{row_index + 1}行失败: {type(e).__name__}: {e}")
            self.log(f"行数据提取失败 (行{row_index + 1}): {e}", "WARNING")
            return None

    def _extract_cell_data(self, cell, row_data):
        """提取单元格数据"""
        class_attr = cell.attr("class") or ""

        # 只保留有 longtext 或 showOptSpan 类的元素
        if "longtext" not in class_attr and "showOptSpan" not in class_attr:
            return None

        text = cell.text.strip()

        # 处理空值
        if text in ["&nbsp;", "\xa0", ""]:
            return ""

        # 去掉末尾的 &nbsp;
        if text.endswith("&nbsp;"):
            text = text[:-6].strip()

        # 特殊处理：标准化航班号（将EU/VJ统一为VJ）
        if len(row_data) == 2:  # 当前是第3列（航班号）
            text = self._normalize_flight_number(text)

        return text

    def _normalize_flight_number(self, text):
        """标准化航班号"""
        import re

        text = str(text).strip().upper()
        match = re.search(r"\d+", text)
        if match:
            return f"VJ{match.group()}"
        return text

    def _log_row_data(self, row_index, row_data):
        """记录行数据"""
        print(
            f"   📝 第{row_index + 1}行: {row_data[0]} - {row_data[1]} - {row_data[2]} "
            f"(OUT:{row_data[6]}, OFF:{row_data[7]}, ON:{row_data[8]}, IN:{row_data[9]})"
        )

    def _assemble_table_data(self, data_rows):
        """组装完整的表格数据"""
        headers = self._get_table_headers()
        csv_data = [headers] + data_rows
        print(f"\n   ✅ 成功提取 {len(data_rows)} 行数据")
        return csv_data

    def _get_table_headers(self):
        """获取表头"""
        return [
            "日期",
            "执飞飞机",
            "航班号",
            "起飞机场",
            "着陆机场",
            "MSN",
            "OUT",
            "OFF",
            "ON",
            "IN",
            "运行情况",
            "OUT油量(kg)",
            "OFF油量(kg)",
            "ON油量(kg)",
            "IN油量(kg)",
        ]

    def _handle_extraction_error(self, error):
        """处理提取错误"""
        if isinstance(error, AttributeError):
            print(f"   ❌ 页面元素访问错误: {error}")
            self.log(f"元素访问错误: {error}", "ERROR")
        elif isinstance(error, (TimeoutError, RuntimeError)):
            print(f"   ❌ 数据提取超时或运行时错误: {error}")
            self.log(f"数据提取失败: {error}", "ERROR")
        else:
            print(f"   ❌ 提取数据出错: {type(error).__name__}: {error}")
            self.log(f"数据提取失败: {type(error).__name__}: {error}", "ERROR")
            import traceback

            traceback.print_exc()
        return None

    def navigate_to_target_page(self, page, target_date, aircraft_list=None):
        """
        导航到目标页面并执行抓取逻辑（优化版）

        Args:
            page: ChromiumPage 对象
            target_date: 目标日期
            aircraft_list: 要监控的飞机列表（可选）

        核心逻辑:
        1. 确保在分配的标签页上操作（标签页隔离）
        2. 一旦进入 https://cis.comac.cc:8004/caphm/lineLogController/index.html 就停留
        3. 首次运行: 填写机号和日期，点击查询
        4. 后续运行: 直接点击查询按钮（机号和日期已设置）

        :param page: ChromiumPage 对象
        :param target_date: 目标日期
        :param aircraft_list: 要监控的飞机列表（可选）
        :return: 成功返回数据,失败返回 None
        """
        # 1. 打印启动信息
        self._print_startup_info(target_date, aircraft_list)

        # 2. 检查初始化状态
        print("\n🔍 步骤0: 检查初始化状态")

        if self.check_initialized(target_date):
            # 已初始化，使用快速刷新模式
            return self._run_quick_refresh_mode(page, aircraft_list)

        # 3. 执行首次初始化流程
        return self._run_initialization_flow(page, target_date, aircraft_list)

    def _print_startup_info(self, target_date, aircraft_list=None):
        """打印启动信息"""
        # 优先使用传入的 aircraft_list，否则使用实例变量
        display_list = aircraft_list if aircraft_list is not None else self.aircraft_list

        print("\n" + "=" * 60)
        print("🚀 航段数据抓取器启动")
        print(f"⏰ 启动时间: {time.strftime('%H:%M:%S')}")
        print(f"📅 目标日期: {target_date}")

        if display_list:
            print(f"✈️ 监控飞机: {', '.join(display_list)} ({len(display_list)} 架)")
        else:
            print("⚠️ 警告: 飞机列表为空，将显示所有机队数据！")

        print("=" * 60)

    def _run_quick_refresh_mode(self, page, aircraft_list=None):
        """运行快速刷新模式（已初始化）"""
        print("\n✨ 检测结果: 已初始化")
        print("⚡ 使用快速刷新模式: 只点击查询按钮")
        print("⏱️ 预计耗时: 2-3秒")
        print("💡 机号和日期已设置，无需重复填写")

        if not self.quick_refresh(page):
            return None

        # 提取数据
        print("\n🎯 步骤: 提取数据")
        return self.extract_table_data(page)

    def _run_initialization_flow(self, page, target_date, aircraft_list=None):
        """运行首次初始化流程（未初始化）"""
        print("\n🔧 检测结果: 页面未就绪")
        print("🔧 执行首次初始化流程")
        print("⏱️ 预计耗时: 15-20秒")
        print("💡 只需设置一次: 机号和日期")

        # 优先使用传入的 aircraft_list，否则使用实例变量
        effective_list = aircraft_list if aircraft_list is not None else self.aircraft_list

        # 步骤1: 导航到目标页面（整页刷新时强制重新加载）
        # 判断是否是整页刷新：如果 _last_full_refresh > 0 说明之前初始化过，现在是重新初始化
        is_full_refresh = self._last_full_refresh > 0
        if not self._navigate_to_leg_page(page, force_reload=is_full_refresh):
            return None

        # 步骤2: 选择飞机
        if not self._select_aircrafts_for_init(page, effective_list):
            return None

        # 步骤3: 设置日期
        self._set_date_inputs(page, target_date)

        # 步骤4: 点击查询按钮
        if not self._click_query_button(page):
            return None

        # 步骤5: 等待数据加载
        if not self._wait_for_data_load(page):
            return None

        # 步骤6: 设置初始化标记
        self._set_initialized_flag(target_date)

        # 步骤7: 提取数据
        print("\n🎯 步骤7: 提取数据")
        return self.extract_table_data(page)

    def _navigate_to_leg_page(self, page, force_reload=False):
        """导航到Leg页面

        Args:
            page: ChromiumPage 对象
            force_reload: 是否强制重新加载页面（整页刷新时使用）

        Returns:
            bool: 是否成功
        """
        print("\n🎯 步骤1: 导航到目标页面")
        target_url = "https://cis.comac.cc:8004/caphm/lineLogController/index.html"

        current_url = page.url
        if "lineLogController/index.html" in current_url and not force_reload:
            print("   ✅ 已在目标页面")
            return True

        # 整页刷新：强制重新加载页面，确保 DOM 状态干净
        if force_reload and "lineLogController/index.html" in current_url:
            print("   🔄 整页刷新: 强制重新加载页面...")
            self.log("[整页刷新] 强制重新加载 Leg 页面", "INFO")

        print(f"   📍 当前页面: {current_url}")
        print(f"   🎯 目标页面: {target_url}")

        # 如果从8010端口访问，先跳转到8004首页
        if "cis.comac.cc:8004" not in current_url and "cis.comac.cc:8010" in current_url:
            if not self._navigate_via_intermediate_page(page):
                return False

        # 跳转到目标页面
        return self._navigate_and_verify(page, target_url)

    def _navigate_via_intermediate_page(self, page):
        """通过中间页面导航（从8010到8004）"""
        print("   🔄 从8010端口访问，先跳转到8004首页初始化...")
        intermediate_url = "https://cis.comac.cc:8004/caphm/mainController/index.html"
        page.get(url=intermediate_url)

        # 等待页面加载
        print("   ⏳ 等待8004首页初始化...")
        for i in range(8):
            time.sleep(1)
            if "mainController/index.html" in page.url:
                print(f"   ✅ 8004首页已就绪 ({i + 1}秒)")
                break

        # 额外等待，确保JavaScript框架完全加载
        print("   ⏳ 等待页面框架完全加载...")
        time.sleep(FRAMEWORK_LOAD_WAIT_SECONDS)
        return True

    def _navigate_and_verify(self, page, target_url):
        """导航到目标页面并验证"""
        print("   🚀 导航到目标页面...")
        page.get(url=target_url)

        # 验证是否到达目标页面
        print("   🔍 验证页面...")
        time.sleep(2)

        max_wait = 10
        for i in range(max_wait):
            current_url = page.url
            print(f"   📍 第{i + 1}次检查: {current_url}")

            if "lineLogController/index.html" in current_url:
                print("   ✅ 成功到达目标页面!")
                print("   💡 此后将停留在此页面")
                return True
            time.sleep(1)

        print("   ❌ 导航失败！")
        return False

    def _select_aircrafts_for_init(self, page, aircraft_list):
        """初始化时选择飞机"""
        print("\n🎯 步骤2: 选择飞机（只需设置一次）")

        # 验证 aircraft_list
        if aircraft_list is None:
            aircraft_list = []
            print("   ⚠️ 警告: aircraft_list 为 None，将使用空列表")
        elif len(aircraft_list) == 0:
            print("   ⚠️ 警告: aircraft_list 为空列表，不会选择任何飞机")
            print("   ⚠️ 这可能导致显示所有机队的数据！")
        else:
            print(f"   📋 飞机列表: {', '.join(aircraft_list)} ({len(aircraft_list)} 架)")

        if aircraft_list:
            if not self.select_aircrafts(page, aircraft_list):
                return False
            print("   ✅ 机号选择完成")
        else:
            print("   ⏭️ 跳过机号选择（列表为空）")

        return True

    def _set_date_inputs(self, page, target_date):
        """设置开始和结束日期输入框"""
        print("\n🎯 步骤3: 设置日期（只需设置一次）")

        # 设置开始时间
        start_input = page.ele("tag:input@@id=startTime")
        if start_input:
            start_input.run_js("this.value = arguments[0]", target_date)
            start_input.run_js('this.dispatchEvent(new Event("change", {bubbles: true}))')
            print(f"   ✅ 开始时间: {target_date}")
            time.sleep(0.5)
        else:
            print("   ⚠️ 未找到开始时间输入框")

        # 设置结束时间
        end_input = page.ele("tag:input@@id=endTime")
        if end_input:
            end_input.run_js("this.value = arguments[0]", target_date)
            end_input.run_js('this.dispatchEvent(new Event("change", {bubbles: true}))')
            print(f"   ✅ 结束时间: {target_date}")
            time.sleep(0.5)
        else:
            print("   ⚠️ 未找到结束时间输入框")

    def _click_query_button(self, page):
        """点击查询按钮"""
        print("\n🎯 步骤4: 点击查询按钮")
        query_btn = page.ele("tag:input@@value=查询 @@class=button_partial2")
        if query_btn:
            query_btn.click(by_js=True)
            print("   ✅ 已点击查询按钮")
            return True
        else:
            print("   ❌ 未找到查询按钮")
            return False

    def _wait_for_data_load(self, page):
        """等待数据加载完成"""
        print("\n⏳ 等待数据加载...")
        time.sleep(DATA_REFRESH_WAIT_SECONDS)

        # 等待数据容器出现
        for i in range(10):
            data_con = page.ele("tag:div@@id=dataCon1")
            if data_con:
                print(f"   ✅ 数据已加载 ({i + 1}秒)")
                return True
            print(f"   ⏳ 等待数据... ({i + 1}/10)")
            time.sleep(1)

        print("   ❌ 数据加载超时")
        return False

    def _set_initialized_flag(self, target_date):
        """设置初始化标记"""
        print("\n🎯 步骤6: 设置初始化标记")
        self._initialized = True
        self._initialized_date = target_date
        self.mark_full_refresh()
        print("   ✅ 初始化完成！")
        print(f"   📅 初始化日期: {target_date}")
        print("   💡 下次运行将直接点击查询按钮，无需重复设置机号和日期")


def main(target_date=None):
    """
    主函数:抓取航段数据

    :param target_date: 可选,指定要抓取的目标日期(YYYY-MM-DD格式)
                       如果为None,则抓取今天的数据
    """
    print("🚀 开始抓取航段数据...")

    fetcher = LegFetcher()
    return fetcher.main(target_date)


if __name__ == "__main__":
    import sys

    # 支持命令行参数指定日期
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]

    main(target_date)

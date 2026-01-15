# -*- coding: utf-8 -*-
"""
故障数据监控模块（完整版）

功能:
- 选择机号（通过复选框）
- 点击"历史"按钮
- 设置时间为当天
- 点击"查询"按钮
- 获取并保存故障数据
- 支持与 leg_fetcher 并行运行，共享同一个浏览器实例
"""
import time
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from fetchers.base_fetcher import BaseFetcher
from fetchers.fault_parser import FaultParser
from fetchers.fault_data_saver import FaultDataSaver


class FaultFetcher(BaseFetcher):
    """故障数据监控器（完整版 - 独立端口 9333）"""

    def __init__(self, config_file=None):
        """
        初始化故障数据监控器

        Args:
            config_file: 配置文件路径
        """
        super().__init__(config_file)
        # 初始化解析器和保存器
        self.parser = FaultParser()
        self.saver = FaultDataSaver(project_root)

    def get_browser_port(self):
        """
        [重写] 返回故障监控专用端口

        Returns:
            int: 9333
        """
        return 9333

    def get_browser_user_data_path(self):
        """
        [重写] 返回故障监控专用用户数据路径

        Returns:
            str: 故障监控浏览器用户数据路径
        """
        return r"C:\Users\zhengqiao\AppData\Local\Google\Chrome\User Data_Fault"

    def get_data_prefix(self):
        """返回数据文件前缀"""
        return "fault_data"

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
        print("\n" + "="*60)
        print("🔍 检查初始化状态")
        print("="*60)

        if self._initialized:
            print(f"   ✅ 已初始化")
            print(f"   ⚡ 使用快速刷新模式")
            print("="*60)
            return True
        else:
            print(f"   ❌ 未初始化")
            print(f"   → 需要执行首次初始化（选择机号、点击历史、设置日期）")
            print("="*60)
            return False

    def navigate_to_target_page(self, page, target_date, aircraft_list=None):
        """
        导航到故障监控页面并执行数据抓取

        Args:
            page: ChromiumPage 对象
            target_date: 目标日期
            aircraft_list: 要监控的飞机列表

        Returns:
            成功返回数据列表，失败返回 None
        """
        print("\n" + "="*60)
        print("🚀 故障数据抓取启动")
        print(f"⏰ 启动时间: {time.strftime('%H:%M:%S')}")
        print(f"📅 目标日期: {target_date}")
        if aircraft_list:
            print(f"✈️  监控飞机: {', '.join(aircraft_list)}")
            # 保存目标机号列表，用于后续刷新验证
            self._target_aircrafts = aircraft_list
        else:
            self._target_aircrafts = []
        print("="*60)

        # 故障监控页面URL
        target_url = "https://cis.comac.cc:8004/caphm/integratedMonitorController/list.html?gzphFlag=1&faultType=1,2"

        # 检查当前是否已在目标页面
        current_url = page.url
        print(f"📍 当前URL: {current_url}")

        if "integratedMonitorController/list.html" not in current_url:
            # 需要导航到故障监控页面
            print(f"🎯 导航到故障监控页面...")
            try:
                page.get(target_url)
                print("   ✅ 已导航到故障监控页面")

                # 等待页面关键元素加载完成
                print("   ⏳ 等待页面加载...")
                for i in range(10):
                    # 先检查URL是否已经到达目标页面
                    current_url_after_nav = page.url
                    if "integratedMonitorController" in current_url_after_nav:
                        # 再检查机号下拉框是否已加载
                        dropdown = page.ele('tag:div@@class=filter-option')
                        if dropdown:
                            print(f"   ✅ 页面加载完成 (耗时: {i+1}秒)")
                            print(f"   📍 当前URL: {current_url_after_nav}")
                            break
                    print(f"   ⏳ 加载中... URL: {current_url_after_nav[:80]}... ({i+1}/10秒)")
                    time.sleep(1)
                else:
                    # 10秒后仍未到达目标页面
                    final_url = page.url
                    print(f"   ❌ 页面跳转超时")
                    print(f"   📍 目标URL: {target_url}")
                    print(f"   📍 实际URL: {final_url}")
                    if "integratedMonitorController" not in final_url:
                        print(f"   ❌ 未到达目标页面，跳转失败")
                        return None

            except Exception as e:
                print(f"   ❌ 打开出错: {e}")
                print("="*60)
                return None
        else:
            print("   ✅ 已在故障监控页面")
            # 即使已在页面，也等待一下确保元素可用
            time.sleep(1)

        # 检查是否需要初始化
        if not self.check_initialized():
            # 首次初始化：选择机号、点击历史、设置日期
            if not self.initialize_page(page, aircraft_list, target_date):
                print("❌ 页面初始化失败")
                return None
            # 标记为已初始化
            self._initialized = True

        # 快速刷新：只点击查询按钮
        if not self.quick_refresh(page):
            print("❌ 数据刷新失败")
            return None

        # 提取数据
        data = self.extract_fault_data(page)
        if data:
            print(f"✅ 成功提取 {len(data)} 条故障记录")
            print("="*60)
            return data
        else:
            print("❌ 未能提取到故障数据")
            print("="*60)
            return None

    def initialize_page(self, page, aircraft_list, target_date):
        """
        初始化页面：选择机号、点击历史、设置日期

        Args:
            page: ChromiumPage 对象
            aircraft_list: 飞机列表
            target_date: 目标日期

        Returns:
            bool: 是否成功
        """
        print("\n" + "="*60)
        print("🔧 初始化页面设置")
        print("="*60)

        # 等待页面完全加载
        print("   ⏳ 等待页面元素加载...")
        time.sleep(3)

        # 步骤1：选择机号
        if aircraft_list:
            print("\n📍 步骤1: 选择机号")
            if not self.select_aircrafts(page, aircraft_list):
                print("   ❌ 选择机号失败")
                return False
            print("   ✅ 机号选择完成")

        # 步骤2：点击"历史"按钮
        print("\n📍 步骤2: 点击'历史'按钮")
        if not self.click_history_button(page):
            print("   ❌ 点击历史按钮失败")
            return False
        print("   ✅ 已点击历史按钮")

        # 步骤3：设置日期
        print("\n📍 步骤3: 设置日期")
        if not self.set_date(page, target_date):
            print("   ❌ 设置日期失败")
            return False
        print(f"   ✅ 日期已设置为: {target_date}")

        print("\n✅ 页面初始化完成")
        print("="*60)
        return True

    def select_aircrafts(self, page, aircraft_list):
        """
        选择指定的飞机（通过复选框）

        Args:
            page: ChromiumPage 对象
            aircraft_list: 飞机列表

        Returns:
            bool: 是否成功
        """
        print(f"   📋 开始选择飞机...")

        # 查找机号下拉框
        # 结构：<div class="filter-option"><div class="filter-option-inner"><div class="filter-option-inner-inner"></div></div></div>
        print("   🔍 查找机号下拉框...")

        # 尝试找到第一个 filter-option
        all_dropdowns = page.eles('tag:div@@class=filter-option')
        if not all_dropdowns or len(all_dropdowns) == 0:
            print("   ❌ 未找到机号下拉框")
            return False

        aircraft_dropdown = all_dropdowns[0]
        print(f"   ✅ 找到 {len(all_dropdowns)} 个下拉框，使用第一个")

        # 点击下拉框
        try:
            aircraft_dropdown.click(by_js=True)
            time.sleep(1)
            print("   ✅ 已点击机号下拉框")
        except Exception as e:
            print(f"   ❌ 点击下拉框失败: {e}")
            return False

        # 等待下拉选项出现
        time.sleep(2)

        # 清空所有已选项
        print("   🔍 清空所有已选项...")
        text_elements = page.eles('tag:span@@class=text')
        for ele in text_elements:
            parent = ele.parent()
            if parent:
                parent_attr = parent.attr('class') or ''
                if 'selected' in parent_attr or 'active' in parent_attr:
                    text = ele.text.strip()
                    print(f"   🔄 取消选择: {text}")
                    parent.click(by_js=True)
                    time.sleep(0.3)

        time.sleep(1)

        # 选择指定的飞机
        print("   🎯 开始选择目标飞机...")
        selected_count = 0

        for aircraft in aircraft_list:
            # 重新获取元素列表
            text_elements = page.eles('tag:span@@class=text')
            found = False
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
                    except Exception as e:
                        print(f"   ⚠️ 点击失败: {e}")
                    time.sleep(0.5)
                    selected_count += 1
                    found = True
                    break

            if not found:
                print(f"   ⚠️ 未找到飞机: {aircraft}")

        # 点击其他地方关闭下拉框
        try:
            page.ele('tag:body').click()
        except:
            pass

        time.sleep(1)

        if selected_count > 0:
            print(f"   ✅ 成功选择 {selected_count} 架飞机")
            return True
        else:
            print("   ❌ 未能选择任何飞机")
            return False

    def click_history_button(self, page):
        """
        点击"历史"按钮（单选按钮）

        Args:
            page: ChromiumPage 对象

        Returns:
            bool: 是否成功
        """
        print("   🔍 查找'历史'按钮...")

        # 查找历史按钮
        # 结构：<input id="legType3" name="legType" type="radio" value="3" onclick="updateLegType()">
        history_radio = page.ele('tag:input@@id=legType3@@type=radio')

        if not history_radio:
            print("   ❌ 未找到'历史'按钮")
            return False

        print("   ✅ 找到'历史'按钮")

        # 检查是否已选中
        is_checked = history_radio.attr('checked')
        if is_checked:
            print("   ✅ '历史'按钮已选中")
            return True

        # 点击按钮
        try:
            history_radio.click(by_js=True)
            print("   ✅ 已点击'历史'按钮")
            time.sleep(1)
            return True
        except Exception as e:
            print(f"   ❌ 点击'历史'按钮失败: {e}")
            return False

    def set_date(self, page, target_date):
        """
        设置日期为当天

        Args:
            page: ChromiumPage 对象
            target_date: 目标日期 (YYYY-MM-DD)

        Returns:
            bool: 是否成功
        """
        print(f"   🔍 设置日期为: {target_date}")

        # 解析日期
        try:
            date_obj = datetime.strptime(target_date, '%Y-%m-%d')
        except ValueError:
            print(f"   ❌ 日期格式错误: {target_date}")
            return False

        # 查找开始日期输入框
        # 结构：<input disabled="disabled" type="text" id="from" name="from" class="condition_input" ...>
        from_input = page.ele('tag:input@@id=from')
        if not from_input:
            print("   ⚠️ 未找到开始日期输入框，尝试继续...")

        # 查找结束日期输入框
        to_input = page.ele('tag:input@@id=to')
        if not to_input:
            print("   ⚠️ 未找到结束日期输入框，尝试继续...")

        # 尝试使用 JavaScript 设置日期
        try:
            # 使用 JavaScript 设置日期值
            js_code = f'''
            // 设置开始日期
            var fromInput = document.getElementById('from');
            if (fromInput) {{
                fromInput.value = '{target_date}';
                fromInput.setAttribute('value', '{target_date}');
            }}

            // 设置结束日期
            var toInput = document.getElementById('to');
            if (toInput) {{
                toInput.value = '{target_date}';
                toInput.setAttribute('value', '{target_date}');
            }}
            '''
            page.run_js(js_code)
            print(f"   ✅ 日期已设置为: {target_date}")
            time.sleep(1)
            return True
        except Exception as e:
            print(f"   ❌ 设置日期失败: {e}")
            return False

    def quick_refresh(self, page):
        """
        快速刷新：只点击查询按钮

        Args:
            page: ChromiumPage 对象

        Returns:
            bool: 是否成功
        """
        print("\n" + "="*60)
        print("⚡ 快速刷新模式")
        print("="*60)

        # 点击查询按钮
        print("   🔍 查找查询按钮...")
        query_btn = page.ele('tag:input@@value=查询 @@class=button_partial2')
        if query_btn:
            print("   ✅ 找到查询按钮")
            query_btn.click(by_js=True)
            print("   ✅ 已点击查询按钮")
        else:
            print("   ❌ 未找到查询按钮")
            return False

        # 等待数据刷新
        print("   ⏳ 等待数据刷新...")
        time.sleep(3)

        # 获取目标机号列表（用于验证数据是否刷新完成）
        target_aircrafts = getattr(self, '_target_aircrafts', [])
        # 只在首次运行时验证机号（防止刷新不完整）
        need_aircraft_validation = not self._initialized

        # 等待数据容器更新
        print("   🔍 检查数据更新...")
        for i in range(10):
            data_con = page.ele('tag:div@@id=dataCon')
            if data_con:
                rows = data_con.eles('tag:div@@name=t_rtm_faultMainRowDiv')
                if rows:
                    # 首次运行时：验证数据是否只包含目标机号
                    if need_aircraft_validation and target_aircrafts:
                        # 检查前3行的机号，确保都是目标机号
                        sample_rows = rows[:min(3, len(rows))]
                        has_non_target = False

                        for row in sample_rows:
                            try:
                                # 提取机号（从第一列获取）
                                first_cell = row.ele('tag:div@@class=t_c')
                                if first_cell:
                                    aircraft_text = first_cell.text.strip()
                                    # 检查是否包含任何目标机号
                                    is_target = any(target in aircraft_text for target in target_aircrafts)
                                    if not is_target:
                                        has_non_target = True
                                        print(f"   ⚠️ 发现非目标机号数据: {aircraft_text}")
                                    else:
                                        print(f"   ✅ 发现目标机号数据: {aircraft_text}")
                            except:
                                pass

                        if has_non_target:
                            print(f"   🔄 数据未刷新完成（包含旧数据），继续等待2秒...")
                            time.sleep(2)
                            continue

                    print(f"   ✅ 数据已刷新 (耗时: {i+3}秒)")
                    print(f"   📊 当前数据行数: {len(rows)}")
                    print("="*60)
                    return True
            print(f"   ⏳ 等待中... ({i+3}/10秒)")
            time.sleep(1)

        print("   ⚠️ 数据刷新较慢，继续提取")
        print("="*60)
        return True

    def extract_fault_data(self, page):
        """
        从页面中提取故障数据（调用解析器）

        Args:
            page: ChromiumPage 对象

        Returns:
            list: 故障数据列表
        """
        return self.parser.extract_fault_data(page)

    def save_to_csv(self, data, filename=None):
        """
        保存故障数据到CSV文件（调用保存器）

        优化：
        1. 删除FlightlegId和ReportId列
        2. 清理时间字段（移除日期部分）
        3. 标准化航班号（EU改为VJ）

        Args:
            data: 故障数据列表
            filename: 文件名（可选）

        Returns:
            str: 保存的文件路径，失败返回 None
        """
        return self.saver.save_to_csv(data, filename)

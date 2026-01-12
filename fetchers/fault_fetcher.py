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
import csv
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from fetchers.base_fetcher import BaseFetcher


class FaultFetcher(BaseFetcher):
    """故障数据监控器（完整版 - 独立端口 9333）"""

    def connect_browser(self):
        """
        [重写] 连接到独立的故障监控浏览器 (端口 9333)
        """
        from DrissionPage import ChromiumPage, ChromiumOptions

        co = ChromiumOptions()
        # 1. 设置端口为 9333
        co.set_local_port(9333)
        # 2. 设置对应的 User Data 路径 (必须与你快捷方式里设置的一模一样)
        # 注意：这里使用 r"" 原始字符串防止转义问题
        co.set_user_data_path(r"C:\Users\zhengqiao\AppData\Local\Google\Chrome\User Data_Fault")

        try:
            print(f"\n{'='*60}")
            print(f"🌐 (Fault专用) 连接浏览器端口 9333...")
            page = ChromiumPage(co)
            print(f"✅ 连接成功!")

            # 这里的标签页管理很简单，直接获取当前激活的标签页即可
            # 因为这个浏览器只有你在用
            self.assigned_tab_object = page.get_tab(page.tab_ids[0])
            return self.assigned_tab_object

        except Exception as e:
            print(f"❌ 连接 9333 端口失败: {e}")
            print("💡 请确保已经通过快捷方式启动了故障监控专用浏览器！")
            return None

    def get_target_url_keyword(self):
        """
        返回用于标签页匹配的URL关键词

        Returns:
            str: 'integratedMonitorController'
        """
        return "integratedMonitorController"

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
        # 标签页隔离检查
        if not self.ensure_assigned_tab(page):
            print("⚠️  标签页检查失败")
            return None

        print("\n" + "="*60)
        print("🚀 故障数据抓取启动")
        print(f"⏰ 启动时间: {time.strftime('%H:%M:%S')}")
        print(f"🏷️  标签页索引: {self.assigned_tab_index}")
        print(f"📅 目标日期: {target_date}")
        if aircraft_list:
            print(f"✈️  监控飞机: {', '.join(aircraft_list)}")
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
                time.sleep(3)
            except Exception as e:
                print(f"   ❌ 打开出错: {e}")
                print("="*60)
                return None
        else:
            print("   ✅ 已在故障监控页面")

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

        # 等待数据容器更新
        print("   🔍 检查数据更新...")
        for i in range(10):
            data_con = page.ele('tag:div@@id=dataCon')
            if data_con:
                rows = data_con.eles('tag:div@@name=t_rtm_faultMainRowDiv')
                if rows:
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
        从页面中提取故障数据（快速模式）

        Args:
            page: ChromiumPage 对象

        Returns:
            list: 故障数据列表
        """
        print("\n📊 开始提取故障数据...")

        try:
            # 找到数据容器
            data_con = page.ele('tag:div@@id=dataCon')
            if not data_con:
                print("   ❌ 未找到数据容器 #dataCon")
                return None

            print("   ✅ 找到数据容器")

            # 使用DOM方式提取所有行（更可靠）
            rows = data_con.eles('tag:div@@name=t_rtm_faultMainRowDiv')

            # 如果没找到行，多等两秒再试一次，防止由于网络波动导致的抓取失败
            if not rows:
                print("   ⏳ 首次未找到数据行，等待2秒后重试...")
                time.sleep(2)
                rows = data_con.eles('tag:div@@name=t_rtm_faultMainRowDiv')

            print(f"   ✅ 找到 {len(rows)} 行数据")

            if not rows:
                print("   ❌ 没有故障数据")
                return None

            # 批量提取数据（使用DOM但只提取一次）
            data_list = []
            for i, row in enumerate(rows):
                try:
                    # 直接从元素获取HTML，然后快速解析
                    row_html = row.html
                    # 从id属性提取故障ID
                    row_id = row.attr('id') or ''
                    fault_id = row_id.replace('t_rtm_faultMainRowDiv', '') if row_id else ''

                    data = self.extract_row_data_fast(row_html, fault_id)
                    if data:
                        data_list.append(data)
                        # 简洁输出（类似Leg Data）
                        print(f"   📝 第{i+1}行: {data['机号']} - {data['航班号']} - {data['故障描述'][:30]}...")
                except Exception as e:
                    print(f"   ⚠️ 提取第{i+1}行失败: {e}")
                    continue

            print(f"\n   ✅ 成功提取 {len(data_list)} 条故障记录")
            return data_list

        except Exception as e:
            print(f"   ❌ 提取数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def extract_row_data_fast(self, row_html, fault_id):
        """
        针对复杂 HTML 结构优化的快速提取算法

        核心优化:
        1. 优先从隐藏 input 获取核心元数据（最准确）
        2. 从 <a> 标签 title 属性获取完整故障描述（解决截断问题）
        3. 增加唯一ID字段用于去重判断
        4. 更健壮的HTML清理逻辑

        Args:
            row_html: 行HTML字符串
            fault_id: 故障ID

        Returns:
            dict: 故障数据字典
        """
        data = {}
        import re
        from html import unescape

        try:
            # 提取原始数据（保持HTML结构对应的字段名）
            def get_hidden_val(name_id):
                match = re.search(f'id="{name_id}{fault_id}"[^>]*value="([^"]*)"', row_html)
                return unescape(match.group(1)) if match else ""

            # 从隐藏域提取
            data['FlightlegId'] = get_hidden_val('rtmFlightlegId')
            data['ReportId'] = get_hidden_val('rtmReportId')
            data['故障类型'] = get_hidden_val('faultType')
            data['时间'] = get_hidden_val('messageTime')

            # 提取机号
            aircraft_match = re.search(r'<p[^>]*>(B-[\w]+)</p>', row_html.replace('&nbsp;', ''))
            data['机号'] = aircraft_match.group(1) if aircraft_match else ""

            # 提取所有li内容
            li_contents = re.findall(r'<li[^>]*class="li0"[^>]*>(.*?)</li>', row_html, re.DOTALL)

            def clean_html(raw_html):
                content = re.sub(r'<[^>]+>', '', raw_html)
                return unescape(content).replace('&nbsp;', '').strip()

            if len(li_contents) >= 11:
                data['机型'] = clean_html(li_contents[1])
                data['航空公司'] = clean_html(li_contents[2])
                data['航班号'] = clean_html(li_contents[3])
                data['航段'] = clean_html(li_contents[4])
                data['故障码'] = clean_html(li_contents[5])
                # li_contents[6] 是时间

                # 故障描述（从title属性获取完整内容）
                desc_match = re.search(r'<a[^>]*title="([^"]*)"', li_contents[7])
                data['故障描述'] = unescape(desc_match.group(1)) if desc_match else clean_html(li_contents[7])

                data['阶段'] = clean_html(li_contents[8])
                # li_contents[9] 通常是空的
                data['状态'] = clean_html(li_contents[10])

                # ATA章节（倒数第二个li，7%宽度）
                ata_match = re.findall(r'<li[^>]*style="width:7%;">(.*?)</li>', row_html, re.DOTALL)
                if len(ata_match) >= 2:
                    data['ATA章节'] = clean_html(ata_match[1])  # 取最后一个7%的li
                else:
                    data['ATA章节'] = ""

            # 添加提取时间
            data['提取时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            return data

        except Exception as e:
            print(f"      ❌ 深度解析失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def extract_row_data(self, row):
        """
        从单行中提取故障数据（DOM操作模式，作为备用）

        HTML 结构分析：
        - 机号: li[0] 中的文本
        - 机型: li[1]
        - 航空公司: li[2]
        - 航班号: li[3]
        - 航段: li[4]
        - 故障码: li[5]
        - 时间: li[6]
        - 故障描述: li[7] 中的 <a> 标签
        - 状态: li[8]
        - ATA章节: li[10]

        Args:
            row: 行元素

        Returns:
            dict: 故障数据字典
        """
        data = {}

        try:
            # 获取所有 li 元素
            lis = row.eles('tag:li@@class=li0')

            if len(lis) < 11:
                print(f"      ⚠️ 列数不足: {len(lis)}")
                return None

            # 提取各列数据
            # 机号 (li[0])
            aircraft_text = lis[0].text.strip()
            # 从文本中提取机号（包含B-XXXX格式）
            import re
            aircraft_match = re.search(r'B-\d{4}', aircraft_text)
            data['机号'] = aircraft_match.group(0) if aircraft_match else aircraft_text

            # 机型 (li[1])
            data['机型'] = lis[1].text.strip()

            # 航空公司 (li[2])
            data['航空公司'] = lis[2].text.strip()

            # 航班号 (li[3])
            data['航班号'] = lis[3].text.strip()

            # 航段 (li[4])
            data['航段'] = lis[4].text.strip()

            # 故障码 (li[5])
            data['故障码'] = lis[5].text.strip()

            # 时间 (li[6])
            data['时间'] = lis[6].text.strip()

            # 故障描述 (li[7] 中的 <a> 标签)
            fault_link = lis[7].ele('tag:a')
            if fault_link:
                data['故障描述'] = fault_link.text.strip()
                data['故障类型'] = fault_link.attr('title') or ''
            else:
                data['故障描述'] = lis[7].text.strip()
                data['故障类型'] = ''

            # 阶段 (li[8])
            data['阶段'] = lis[8].text.strip()

            # 状态 (li[9])
            state_div = lis[9].ele('tag:div')
            data['状态'] = state_div.text.strip() if state_div else lis[9].text.strip()

            # ATA章节 (li[10])
            data['ATA章节'] = lis[10].text.strip()

            # 添加提取时间
            data['提取时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            return data

        except Exception as e:
            print(f"      ❌ 提取行数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def save_to_csv(self, data, filename=None):
        """
        保存故障数据到CSV文件

        Args:
            data: 故障数据列表
            filename: 文件名（可选）

        Returns:
            str: 保存的文件路径，失败返回 None
        """
        if not data:
            print("   ❌ 没有数据可保存")
            return None

        try:
            # 确定保存路径 - 使用 data/daily_raw 文件夹
            today_str = datetime.now().strftime('%Y-%m-%d')
            data_dir = Path("data") / "daily_raw" / today_str
            data_dir.mkdir(parents=True, exist_ok=True)

            if filename is None:
                filename = f"fault_data_{today_str}.csv"

            file_path = data_dir / filename

            # 定义字段顺序（按照实际页面表头）
            fieldnames = [
                '获取时间', '机号', '机型', '航空公司', '航班号',
                'ATA', '航段', '触发时间', '描述', '故障类型',
                '飞行阶段', '处理状态', '类别-优先权', 'FlightlegId', 'ReportId'
            ]

            # 写入CSV文件（覆盖模式）
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # 写入表头
                writer.writeheader()

                # 写入数据行，进行字段映射
                for row in data:
                    # 字段映射：原始字段名 -> 实际表头字段名
                    row_data = {
                        '获取时间': row.get('提取时间', ''),
                        '机号': row.get('机号', ''),
                        '机型': row.get('机型', ''),
                        '航空公司': row.get('航空公司', ''),
                        '航班号': row.get('航班号', ''),
                        'ATA': row.get('ATA章节', ''),
                        '航段': row.get('航段', ''),
                        '触发时间': row.get('时间', ''),
                        '描述': row.get('故障描述', ''),
                        '故障类型': row.get('故障类型', ''),
                        '飞行阶段': row.get('阶段', ''),
                        '处理状态': row.get('状态', ''),
                        '类别-优先权': '',  # 暂时为空
                        'FlightlegId': row.get('FlightlegId', ''),
                        'ReportId': row.get('ReportId', '')
                    }
                    writer.writerow(row_data)

            print(f"   ✅ 数据已保存到: {file_path}")
            print(f"   📊 共保存 {len(data)} 条记录")
            return str(file_path)

        except Exception as e:
            print(f"   ❌ 保存文件失败: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """
    独立运行的故障监控主程序 (循环模式)

    说明:
    - 此脚本会连接到独立的故障监控浏览器（端口9333）
    - 每5分钟自动刷新一次故障数据
    - 使用独立用户目录，与Leg数据完全隔离
    """
    print("🚀 启动独立故障监控 (端口 9333)...")

    fetcher = FaultFetcher()

    # 获取配置中的飞机列表
    from config.config_loader import load_config
    config_loader = load_config()
    config = config_loader.get_all_config()
    aircraft_list = config.get('aircraft_list', [])

    # 连接浏览器
    page = fetcher.connect_browser()
    if not page:
        print("\n❌ 无法连接到浏览器")
        print("💡 请确保已经通过快捷方式启动了故障监控专用浏览器（端口9333）！")
        return

    # 首次登录检查
    fetcher.smart_login(page)

    print("\n⏰ 开始循环监控: 每 5 分钟刷新一次")
    print("="*60)

    try:
        while True:
            target_date = fetcher.get_today_date()
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 执行刷新...")

            # 抓取数据
            data = fetcher.navigate_to_target_page(page, target_date, aircraft_list)

            if data:
                csv_file = fetcher.save_to_csv(data)
                if csv_file:
                    print(f"✅ 保存成功: {os.path.basename(csv_file)}")

            # 等待 5 分钟 (300秒)
            print("⏳ 等待 5 分钟...")
            time.sleep(300)

    except KeyboardInterrupt:
        print("\n👋 停止监控")


if __name__ == "__main__":
    main()

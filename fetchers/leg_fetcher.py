# -*- coding: utf-8 -*-
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
import time
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from fetchers.base_fetcher import BaseFetcher


class LegFetcher(BaseFetcher):
    """航段数据抓取器（优化版）"""

    def get_data_prefix(self):
        """返回数据文件前缀"""
        return "leg_data"

    def check_page_ready(self, page, aircraft_list, target_date):
        """
        检查页面是否已就绪（已在目标页面且设置完成）

        核心逻辑:
        1. 一旦进入目标页面就停留在那里
        2. 首次进入需要设置机号和日期
        3. 后续只需点击查询按钮

        检测策略优化:
        - 给页面一点时间加载（可能刚跳转过来）
        - 检查日期和数据行综合判断

        Args:
            page: ChromiumPage 对象
            aircraft_list: 飞机列表
            target_date: 目标日期

        Returns:
            bool: True 表示已就绪，False 表示需要初始化
        """
        print("\n" + "="*60)
        print("🔍 页面状态检测")
        print("="*60)

        current_url = page.url
        print(f"📍 当前URL: {current_url}")

        # 核心检查: 是否在目标页面
        if "lineLogController/index.html" not in current_url:
            print("   ❌ 不在目标页面")
            print("   → 需要导航到 lineLogController/index.html")
            return False

        print("   ✅ 已在目标页面: lineLogController/index.html")

        # 给页面一点时间加载元素（可能刚跳转过来）
        print("   ⏳ 等待页面元素加载...")
        time.sleep(1)

        # 检查页面元素是否加载完成
        start_input = page.ele('tag:input@@id=startTime')
        if not start_input:
            print("   ⚠️ 页面元素未加载完成")
            return False

        # 检查当前日期设置
        current_date = start_input.attr('value') or ''
        print(f"📅 当前页面日期: [{current_date}]")
        print(f"📅 目标抓取日期: [{target_date}]")

        # 检查日期是否匹配
        date_mismatch = target_date not in current_date

        # 检查是否有数据行（最直接的判断标准）
        data_con = page.ele('tag:div@@id=dataCon1')
        if data_con:
            rows = data_con.eles('tag:div@@class=tr_title')
            if rows:
                # 有数据行，说明已经设置过机号
                if date_mismatch:
                    # 日期不匹配，但页面已就绪
                    # 只需更新日期，不需要重新选择机号
                    print(f"   ✅ 页面已就绪（机号已设置）")
                    print(f"   ⚠️ 日期不匹配，需要更新日期")
                    print(f"   📊 当前数据行: {len(rows)}")
                    print(f"   ⚡ 策略: 更新日期后直接查询")
                    print("="*60)

                    # 更新日期
                    print(f"\n🔄 更新日期为: {target_date}")
                    start_input.run_js('this.value = arguments[0]', target_date)
                    start_input.run_js('this.dispatchEvent(new Event("change", {bubbles: true}))')

                    end_input = page.ele('tag:input@@id=endTime')
                    if end_input:
                        end_input.run_js('this.value = arguments[0]', target_date)
                        end_input.run_js('this.dispatchEvent(new Event("change", {bubbles: true}))')

                    # 点击查询按钮
                    query_btn = page.ele('tag:input@@value=查询 @@class=button_partial2')
                    if query_btn:
                        query_btn.click(by_js=True)
                        print("   ✅ 已更新日期并点击查询")

                    # 等待数据刷新
                    time.sleep(2)

                    return True

                else:
                    # 日期匹配，页面就绪
                    print(f"   ✅ 页面已就绪！")
                    print(f"   📅 日期: {current_date}")
                    print(f"   📊 数据行: {len(rows)}")
                    print(f"   ⚡ 可使用快速刷新模式")
                    print("="*60)
                    return True

        # 如果没有数据行，说明确实需要初始化
        if date_mismatch:
            print("   → 需要初始化: 日期不匹配且无数据")
        else:
            print("   → 需要初始化: 未检测到数据")
        print("   💡 说明: 首次运行或需要重新设置查询条件")
        print("="*60)
        return False

    def quick_refresh(self, page):
        """
        快速刷新：只点击查询按钮

        核心逻辑:
        - 系统已在目标页面，机号和日期已设置
        - 只需要点击查询按钮刷新数据
        - 不需要任何页面跳转或表单填写

        Args:
            page: ChromiumPage 对象

        Returns:
            bool: 是否成功
        """
        print("\n" + "="*60)
        print("⚡ 快速刷新模式")
        print("="*60)
        print("💡 核心策略: 停留在当前页面，只点击查询按钮")

        # 点击查询按钮
        print("🔍 查找查询按钮...")
        query_btn = page.ele('tag:input@@value=查询 @@class=button_partial2')
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
            data_con = page.ele('tag:div@@id=dataCon1')
            if data_con:
                rows = data_con.eles('tag:div@@class=tr_title')
                if rows:
                    print(f"   ✅ 数据已刷新 (耗时: {i+2}秒)")
                    print(f"   📊 当前数据行数: {len(rows)}")
                    print("="*60)
                    return True
            print(f"   ⏳ 等待中... ({i+2}/8秒)")
            time.sleep(1)

        print("   ⚠️ 数据刷新较慢，继续提取")
        print("="*60)
        return True

    def select_aircrafts(self, page, aircraft_list):
        """
        选择指定的飞机(通过序列号筛选)

        优化:
        1. 先检查是否已选择目标飞机，避免重复操作
        2. 精确定位序列号下拉框，避免误操作其他下拉框（如所属客户）
        """
        print(f"\n📋 开始选择飞机...")

        # 等待页面完全加载
        print("   ⏳ 等待页面元素加载...")
        time.sleep(2)

        # ========== 精确定位序列号下拉框 ==========
        label_ele = page.ele('tag:p@text()=序列号:')
        if not label_ele:
            print("   ❌ 未找到'序列号'标签")
            return False

        print("   ✅ 找到标签: 序列号")

        # 查找标签旁边的下拉框
        aircraft_dropdown = None

        # 方法1: 通过父元素查找
        parent = label_ele.parent()
        if parent:
            # 在父元素中查找 filter-option
            dropdown = parent.ele('tag:div@@class=filter-option')
            if dropdown:
                aircraft_dropdown = dropdown
                print("   ✅ 通过父元素找到序列号下拉框")
            else:
                # 尝试查找父元素的下一个兄弟元素
                next_sibling = parent.next()
                if next_sibling:
                    dropdown = next_sibling.ele('tag:div@@class=filter-option')
                    if dropdown:
                        aircraft_dropdown = dropdown
                        print("   ✅ 通过兄弟元素找到序列号下拉框")

        if not aircraft_dropdown:
            print("   ❌ 未找到序列号下拉框")
            return False

        # ========== 检查当前选择状态 ==========
        print("   🔍 检查当前选择状态...")

        # 点击下拉框查看当前选择
        aircraft_dropdown.click(by_js=True)
        time.sleep(1)

        # 只在序列号下拉框内查找选项
        # 通过下拉框的父元素来限定查找范围
        dropdown_container = aircraft_dropdown.parent()
        if dropdown_container:
            # 在容器内查找已选择的选项
            selected_elements = dropdown_container.eles('tag:li@@class=selected')
            selected_aircrafts = []
            for ele in selected_elements:
                text = ele.text.strip()
                if text and text != '请选择...':
                    selected_aircrafts.append(text)

            print(f"   📋 序列号已选择: {selected_aircrafts}")

            # 检查是否所有目标飞机都已选择
            all_selected = True
            for aircraft in aircraft_list:
                found = False
                for selected in selected_aircrafts:
                    if aircraft in selected:
                        found = True
                        break
                if not found:
                    all_selected = False
                    break

            if all_selected and len(selected_aircrafts) == len(aircraft_list):
                print("   ✅ 所有目标飞机已选择，跳过选择步骤")
                # 关闭下拉框
                try:
                    page.ele('tag:body').click()
                except:
                    pass
                return True

        # 关闭下拉框，准备重新选择
        try:
            page.ele('tag:body').click()
        except:
            pass
        time.sleep(0.5)

        # ========== 重新选择飞机 ==========
        print("   🔄 需要重新选择飞机...")

        # 再次点击下拉框
        aircraft_dropdown.click(by_js=True)
        time.sleep(1)

        # 先取消所有已选择的飞机选项（只在序列号下拉框内操作）
        print("   🔍 清空序列号已选项...")

        if dropdown_container:
            # 在容器内查找已选择的选项并取消
            selected_elements = dropdown_container.eles('tag:li@@class=selected')
            for ele in selected_elements:
                text = ele.text.strip()
                if text and text != '请选择...':
                    print(f"   🔄 取消选择: {text}")
                    ele.click(by_js=True)
                    time.sleep(0.3)

        time.sleep(1)

        # 选择指定的飞机（只在序列号下拉框内操作）
        print("   🎯 开始选择目标飞机...")
        selected_count = 0

        if dropdown_container:
            for aircraft in aircraft_list:
                # 在容器内查找所有选项
                all_options = dropdown_container.eles('tag:li')
                found = False
                for ele in all_options:
                    text = ele.text.strip()
                    # 使用包含匹配
                    if aircraft in text:
                        print(f"   ✅ 选择飞机: {text}")
                        try:
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

    def extract_table_data(self, page):
        """从表格中提取航段数据"""
        print("\n📊 开始提取表格数据...")

        try:
            # 找到数据容器 #dataCon
            data_con = page.ele('tag:div@@id=dataCon')
            if not data_con:
                print("   ❌ 未找到数据容器 #dataCon")
                return None

            print("   ✅ 找到数据容器")

            # 找到数据行(.tr_title)
            rows = data_con.eles('tag:div@@class=tr_title')
            print(f"   ✅ 找到 {len(rows)} 行数据")

            if not rows:
                print("   ❌ 表格为空")
                return None

            # 表头(固定的列名)
            headers = [
                '日期', '执飞飞机', '航班号', '起飞机场', '着陆机场', 'MSN',
                'OUT', 'OFF', 'ON', 'IN', '运行情况',
                'OUT油量(kg)', 'OFF油量(kg)', 'ON油量(kg)', 'IN油量(kg)'
            ]

            # 提取每一行的数据
            data_rows = []
            for i, row in enumerate(rows):
                try:
                    # 获取所有列 div
                    cells = row.eles('tag:div')

                    # 提取数据 - 精确定位数据单元格
                    # HTML结构分析：
                    # 1. 第1个div是复选框（width:30px）- 需要跳过
                    # 2. 然后是15个数据div，每个数据div后都有一个<span></span>
                    # 3. 数据div有 class="longtext" 或 class="showOptSpan"
                    row_data = []

                    # 方法：找到所有带 class="longtext" 或 class="showOptSpan" 的 div
                    for cell in cells:
                        # 检查 class 属性
                        class_attr = cell.attr('class') or ''

                        # 只保留有 longtext 或 showOptSpan 类的元素
                        if 'longtext' not in class_attr and 'showOptSpan' not in class_attr:
                            continue

                        # 提取文本
                        text = cell.text.strip()

                        # 处理空值 - 保留位置
                        if text in ['&nbsp;', '\xa0', '']:
                            row_data.append('')
                        else:
                            # 去掉末尾的 &nbsp;
                            if text.endswith('&nbsp;'):
                                text = text[:-6].strip()

                            # 特殊处理：标准化航班号（将EU/VJ统一为VJ）
                            # 假设当前正在处理第3列（航班号），索引为2
                            if len(row_data) == 2:  # 已经处理了2列，当前是第3列（航班号）
                                # 标准化航班号：统一EU和VJ为VJ
                                text = str(text).strip().upper()
                                # 提取数字部分
                                import re
                                match = re.search(r'\d+', text)
                                if match:
                                    text = f'VJ{match.group()}'

                            row_data.append(text)

                    # 确保始终有15列（防御性检查）
                    if len(row_data) < 15:
                        row_data.extend([''] * (15 - len(row_data)))

                    # 只取前15列
                    data_rows.append(row_data[:15])
                    print(f"   📝 第{i+1}行: {row_data[0]} - {row_data[1]} - {row_data[2]} (OUT:{row_data[6]}, OFF:{row_data[7]}, ON:{row_data[8]}, IN:{row_data[9]})")

                except Exception as e:
                    print(f"   ⚠️ 提取第{i+1}行失败: {e}")
                    continue

            if not data_rows:
                print("   ❌ 未能提取到有效数据")
                return None

            # 构建CSV数据(表头 + 数据行)
            csv_data = [headers] + data_rows

            print(f"\n   ✅ 成功提取 {len(data_rows)} 行数据")
            return csv_data

        except Exception as e:
            print(f"   ❌ 提取数据出错: {e}")
            import traceback
            traceback.print_exc()
            return None

    def navigate_to_target_page(self, page, target_date):
        """
        导航到目标页面并执行抓取逻辑（优化版）

        核心逻辑:
        1. 一旦进入 https://cis.comac.cc:8004/caphm/lineLogController/index.html 就停留
        2. 首次运行: 填写机号和日期，点击查询
        3. 后续运行: 直接点击查询按钮（机号和日期已设置）

        :param page: ChromiumPage 对象
        :param target_date: 目标日期
        :return: 成功返回数据,失败返回 None
        """
        print("\n" + "="*60)
        print("🚀 航段数据抓取器启动")
        print(f"⏰ 启动时间: {time.strftime('%H:%M:%S')}")
        print(f"📅 目标日期: {target_date}")
        print(f"✈️ 监控飞机: {', '.join(self.aircraft_list)}")
        print("="*60)

        # ========== 步骤0: 检查页面状态 ==========
        print("\n🔍 步骤0: 检查页面状态")

        if self.check_page_ready(page, self.aircraft_list, target_date):
            # 页面已就绪，使用快速刷新模式
            print("\n✨ 检测结果: 页面已就绪")
            print("⚡ 使用快速刷新模式: 只点击查询按钮")
            print("⏱️ 预计耗时: 2-3秒")
            print("💡 机号和日期已设置，无需重复填写")

            if not self.quick_refresh(page):
                return None

            # 提取数据
            print("\n🎯 步骤: 提取数据")
            return self.extract_table_data(page)

        # ========== 页面未就绪，执行初始化流程 ==========
        print("\n🔧 检测结果: 页面未就绪")
        print("🔧 执行首次初始化流程")
        print("⏱️ 预计耗时: 15-20秒")
        print("💡 只需设置一次: 机号和日期")

        # ========== 步骤1: 导航到目标页面 ==========
        print("\n🎯 步骤1: 导航到目标页面")
        target_url = "https://cis.comac.cc:8004/caphm/lineLogController/index.html"

        current_url = page.url
        if "lineLogController/index.html" in current_url:
            print("   ✅ 已在目标页面")
        else:
            print(f"   📍 当前页面: {current_url}")
            print(f"   🎯 目标页面: {target_url}")

            # 如果从8010端口访问，先跳转到8004首页
            if "cis.comac.cc:8004" not in current_url and "cis.comac.cc:8010" in current_url:
                print("   🔄 从8010端口访问，先跳转到8004首页初始化...")
                intermediate_url = "https://cis.comac.cc:8004/caphm/mainController/index.html"
                page.get(url=intermediate_url)

                # 等待页面加载
                print("   ⏳ 等待8004首页初始化...")
                for i in range(8):
                    time.sleep(1)
                    if "mainController/index.html" in page.url:
                        print(f"   ✅ 8004首页已就绪 ({i+1}秒)")
                        break

                # 额外等待，确保JavaScript框架完全加载
                print("   ⏳ 等待页面框架完全加载...")
                time.sleep(3)

            # 跳转到目标页面
            print(f"   🚀 导航到目标页面...")
            page.get(url=target_url)

            # 验证是否到达目标页面
            print("   🔍 验证页面...")
            time.sleep(2)

            max_wait = 10
            navigated = False
            for i in range(max_wait):
                current_url = page.url
                print(f"   📍 第{i+1}次检查: {current_url}")

                if "lineLogController/index.html" in current_url:
                    print(f"   ✅ 成功到达目标页面!")
                    print(f"   💡 此后将停留在此页面")
                    navigated = True
                    break
                else:
                    time.sleep(1)

            if not navigated:
                print(f"   ❌ 导航失败！")
                return None

        # ========== 步骤2: 选择飞机（首次运行） ==========
        print("\n🎯 步骤2: 选择飞机（只需设置一次）")
        if not self.select_aircrafts(page, self.aircraft_list):
            return None

        # ========== 步骤3: 设置日期（首次运行） ==========
        print("\n🎯 步骤3: 设置日期（只需设置一次）")

        # 设置开始时间
        start_input = page.ele('tag:input@@id=startTime')
        if start_input:
            start_input.run_js('this.value = arguments[0]', target_date)
            start_input.run_js('this.dispatchEvent(new Event("change", {bubbles: true}))')
            print(f"   ✅ 开始时间: {target_date}")
            time.sleep(0.5)
        else:
            print("   ⚠️ 未找到开始时间输入框")

        # 设置结束时间
        end_input = page.ele('tag:input@@id=endTime')
        if end_input:
            end_input.run_js('this.value = arguments[0]', target_date)
            end_input.run_js('this.dispatchEvent(new Event("change", {bubbles: true}))')
            print(f"   ✅ 结束时间: {target_date}")
            time.sleep(0.5)
        else:
            print("   ⚠️ 未找到结束时间输入框")

        # ========== 步骤4: 点击查询按钮 ==========
        print("\n🎯 步骤4: 点击查询按钮")
        query_btn = page.ele('tag:input@@value=查询 @@class=button_partial2')
        if query_btn:
            query_btn.click(by_js=True)
            print("   ✅ 已点击查询按钮")
        else:
            print("   ❌ 未找到查询按钮")
            return None

        # ========== 步骤5: 等待数据加载 ==========
        print("\n⏳ 等待数据加载...")
        time.sleep(3)

        # 等待数据容器出现
        for i in range(10):
            data_con = page.ele('tag:div@@id=dataCon1')
            if data_con:
                print(f"   ✅ 数据已加载 ({i+1}秒)")
                break
            print(f"   ⏳ 等待数据... ({i+1}/10)")
            time.sleep(1)
        else:
            print("   ❌ 数据加载超时")
            return None

        # ========== 步骤6: 提取数据 ==========
        print("\n🎯 步骤6: 提取数据")
        print("💡 下次运行将直接点击查询按钮，无需重复设置")
        return self.extract_table_data(page)


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

# -*- coding: utf-8 -*-
"""
航段数据抓取模块

功能:
- 导航到航段数据页面 (lineLogController/index.html)
- 选择指定的飞机(通过序列号筛选)
- 设置日期为当天
- 点击查询按钮
- 获取并保存航段数据
"""
import time
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from modules.base_fetcher import BaseFetcher


class LegFetcher(BaseFetcher):
    """航段数据抓取器"""

    def get_data_prefix(self):
        """返回数据文件前缀"""
        return "leg_data"

    def select_aircrafts(self, page, aircraft_list):
        """选择指定的飞机(通过序列号筛选)"""
        print(f"\n📋 开始选择飞机...")

        # 等待页面完全加载
        print("   ⏳ 等待页面元素加载...")
        time.sleep(3)

        # 通过查找标签文本定位下拉框
        label_ele = page.ele('tag:p@text()=序列号:')
        if label_ele:
            print("   ✅ 找到标签: 序列号")

            # 找到标签旁边的下拉框 div
            aircraft_dropdown = None

            # 方法1: 查找标签的父元素,然后找同级的下拉框
            parent = label_ele.parent()
            if parent:
                # 在父元素的同级或兄弟元素中查找 filter-option
                dropdown = parent.ele('tag:div@@class=filter-option')
                if dropdown:
                    aircraft_dropdown = dropdown
                    print("   ✅ 通过父元素找到下拉框")
                else:
                    # 尝试查找父元素的下一个兄弟元素
                    next_sibling = parent.next()
                    if next_sibling:
                        dropdown = next_sibling.ele('tag:div@@class=filter-option')
                        if dropdown:
                            aircraft_dropdown = dropdown
                            print("   ✅ 通过兄弟元素找到下拉框")

            # 方法2: 如果上面都失败,直接查找所有 filter-option
            if not aircraft_dropdown:
                all_dropdowns = page.eles('tag:div@@class=filter-option')
                if len(all_dropdowns) > 0:
                    # 通常是第一个或第二个
                    aircraft_dropdown = all_dropdowns[0]
                    print(f"   ✅ 找到 {len(all_dropdowns)} 个下拉框,使用第一个")

            if aircraft_dropdown:
                aircraft_dropdown.click(by_js=True)
                time.sleep(1)
                print("   ✅ 已点击序列号下拉框")
            else:
                print("   ❌ 未找到序列号下拉框")
                return False
        else:
            print("   ❌ 未找到'序列号'标签")
            print("   🔍 尝试直接定位下拉框...")
            # 直接查找所有 filter-option
            all_dropdowns = page.eles('tag:div@@class=filter-option')
            if len(all_dropdowns) > 0:
                print(f"   ✅ 找到 {len(all_dropdowns)} 个下拉框")
                all_dropdowns[0].click(by_js=True)
                time.sleep(1)
                print("   ✅ 已点击第一个下拉框")
            else:
                print("   ❌ 未找到任何下拉框")
                return False

        # 等待下拉选项出现
        time.sleep(2)

        # 先取消所有已选择的飞机选项(清空所有选项)
        print("   🔍 清空所有已选项...")
        text_elements = page.eles('tag:span@@class=text')
        for ele in text_elements:
            parent = ele.parent()
            if parent:
                parent_attr = parent.attr('class') or ''
                if 'selected' in parent_attr or 'active' in parent_attr:
                    # 取消所有选中的选项
                    text = ele.text.strip()
                    print(f"   🔄 取消选择: {text}")
                    parent.click(by_js=True)
                    time.sleep(0.3)

        time.sleep(1)

        # 选择指定的飞机(直接匹配飞机号)
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
        导航到目标页面并执行抓取逻辑

        :param page: ChromiumPage 对象
        :param target_date: 目标日期
        :return: 成功返回数据,失败返回 None
        """
        # ========== 步骤1: 导航到航段数据页面 ==========
        print("\n🎯 步骤1: 导航到航段数据页面")
        target_url = "https://cis.comac.cc:8004/caphm/lineLogController/index.html"

        current_url = page.url
        if "lineLogController/index.html" in current_url:
            print("   ✅ 已在航段数据页面")
        else:
            print(f"   📍 当前页面: {current_url}")

            # ========== 策略：多阶段导航 ==========
            # 阶段1: 如果不在8004端口，先跳转到mainController首页初始化
            if "cis.comac.cc:8004" not in current_url and "cis.comac.cc:8010" in current_url:
                print("   🔄 检测到从8010端口访问，先跳转到8004首页初始化...")
                intermediate_url = "https://cis.comac.cc:8004/caphm/mainController/index.html"
                page.get(url=intermediate_url)

                # 等待中间页面加载
                print("   ⏳ 等待8004首页初始化...")
                for i in range(8):
                    time.sleep(1)
                    if "mainController/index.html" in page.url:
                        print(f"   ✅ 8004首页已就绪 ({i+1}秒)")
                        break

                # 额外等待，确保JavaScript框架完全加载
                print("   ⏳ 等待页面框架完全加载...")
                time.sleep(3)

            # 阶段2: 现在跳转到目标页面
            print(f"   🎯 目标页面: {target_url}")
            print(f"   🚀 开始导航...")

            page.get(url=target_url)

            # 验证是否真的导航到了目标页面
            print("   🔍 验证页面是否已切换...")
            time.sleep(2)  # 给页面一些时间开始加载

            max_wait = 10
            navigated = False
            for i in range(max_wait):
                current_url = page.url
                print(f"   📍 第{i+1}次检查: {current_url}")

                if "lineLogController/index.html" in current_url:
                    print(f"   ✅ 成功导航到航段数据页面!")
                    navigated = True
                    break
                else:
                    time.sleep(1)

            if not navigated:
                print(f"   ❌ 导航失败！页面未切换到目标地址")
                print(f"   📍 最终停留: {page.url}")
                print(f"   🎯 目标地址: {target_url}")
                return None

        # ========== 步骤2: 选择飞机 ==========
        print("\n🎯 步骤2: 选择飞机")
        if not self.select_aircrafts(page, self.aircraft_list):
            return None

        # ========== 步骤3: 设置时间范围 ==========
        print("\n🎯 步骤3: 设置时间范围")

        # 设置开始时间 - readonly输入框需要用JavaScript设置值
        start_input = page.ele('tag:input@@id=startTime')
        if start_input:
            # 使用元素对象直接运行JavaScript设置值
            start_input.run_js('this.value = arguments[0]', target_date)
            # 触发change事件以确保系统识别
            start_input.run_js('this.dispatchEvent(new Event("change", {bubbles: true}))')
            print(f"   ✅ 开始时间设置为: {target_date}")
            time.sleep(0.5)
        else:
            print("   ⚠️ 未找到开始时间输入框")

        # 设置结束时间
        end_input = page.ele('tag:input@@id=endTime')
        if end_input:
            # 使用元素对象直接运行JavaScript设置值
            end_input.run_js('this.value = arguments[0]', target_date)
            # 触发change事件
            end_input.run_js('this.dispatchEvent(new Event("change", {bubbles: true}))')
            print(f"   ✅ 结束时间设置为: {target_date}")
            time.sleep(0.5)
        else:
            print("   ⚠️ 未找到结束时间输入框")

        # ========== 步骤4: 点击查询 ==========
        print("\n🎯 步骤4: 点击【查询】")
        query_btn = page.ele('tag:input@@value=查询 @@class=button_partial2')
        if query_btn:
            query_btn.click(by_js=True)
            print("   ✅ 已点击查询按钮")
        else:
            print("   ❌ 未找到查询按钮")
            return None

        # ========== 步骤5: 等待表格加载 ==========
        print("\n⏳ 等待表格加载...")
        time.sleep(3)  # 等待3秒让表格加载

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

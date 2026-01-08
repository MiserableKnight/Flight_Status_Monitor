# -*- coding: utf-8 -*-
"""
航班数据抓取模块

功能:
- 导航到运力统计(商飞)页面
- 选择指定的飞机
- 设置日期为当天
- 点击查询按钮
- 获取并保存航班数据
"""
import time
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from modules.base_fetcher import BaseFetcher


class FlightFetcher(BaseFetcher):
    """航班数据抓取器"""

    def get_data_prefix(self):
        """返回数据文件前缀"""
        return "flight_data"

    def select_aircrafts(self, page, aircraft_list):
        """选择指定的飞机"""
        print(f"\n📋 开始选择飞机...")

        # 点击"飞机号"下拉框(使用 data-id 属性精确定位)
        aircraft_dropdown = page.ele('tag:button@data-id=tailnumber')
        if aircraft_dropdown:
            aircraft_dropdown.click(by_js=True)
            time.sleep(1)
            print("   ✅ 已点击飞机号下拉框")
        else:
            print("   ❌ 未找到飞机号下拉框")
            return False

        # 等待下拉选项出现
        time.sleep(2)

        # 先取消所有已选择的选项(防止多选)
        print("   🔍 检查并清除已选项...")
        text_elements = page.eles('tag:span@@class=text')
        for ele in text_elements:
            # 检查父元素是否包含 selected 或 active 类
            parent = ele.parent()
            if parent:
                parent_attr = parent.attr('class') or ''
                if 'selected' in parent_attr or 'active' in parent_attr:
                    print(f"   🔄 取消选择: {ele.text}")
                    parent.click(by_js=True)
                    time.sleep(0.3)

        time.sleep(1)

        # 选择指定的飞机(精确匹配完整文本)
        aircraft_mapping = {
            "B-652G": "C909-185/B-652G",
            "B-656E": "C909-196/B-656E"
        }

        print("   🎯 开始选择目标飞机...")
        for aircraft in aircraft_list:
            target_text = aircraft_mapping.get(aircraft, aircraft)

            # 重新获取元素列表(因为DOM可能已更新)
            text_elements = page.eles('tag:span@@class=text')
            found = False
            for ele in text_elements:
                if ele.text.strip() == target_text:
                    print(f"   ✅ 选择飞机: {ele.text}")
                    try:
                        # 尝试点击父元素(通常是可点击的选项)
                        parent = ele.parent()
                        if parent:
                            parent.click(by_js=True)
                        else:
                            ele.click(by_js=True)
                    except Exception as e:
                        print(f"   ⚠️ 点击失败: {e}")
                    time.sleep(0.5)
                    found = True
                    break

            if not found:
                print(f"   ❌ 未找到飞机: {aircraft} ({target_text})")

        # 点击其他地方关闭下拉框
        try:
            page.ele('tag:body').click()
        except:
            pass

        time.sleep(1)
        return True

    def extract_table_data(self, page):
        """从表格中提取数据(只提取最后一行的第10-15列)"""
        print("\n📊 开始提取表格数据...")

        try:
            # 找到表格
            table = page.ele('tag:table@@id=travel')
            if not table:
                print("   ❌ 未找到表格")
                return None

            # 获取所有行
            rows = table.eles('tag:tr')
            print(f"   ✅ 找到 {len(rows)} 行数据")

            if not rows:
                print("   ❌ 表格为空")
                return None

            # 获取最后一行
            last_row = rows[-1]
            print(f"   🎯 提取最后一行...")

            # 分别获取 th 和 td 元素
            th_cells = last_row.eles('tag:th')
            td_cells = last_row.eles('tag:td')
            all_cells = th_cells + td_cells  # 合并

            print(f"   📊 最后一行共有 {len(all_cells)} 列")

            if len(all_cells) < 15:
                print(f"   ❌ 列数不足: 需要15列,实际只有{len(all_cells)}列")
                # 打印所有列以便调试
                for i, cell in enumerate(all_cells):
                    print(f"      列{i+1}: {cell.text.strip()}")
                return None

            # 提取第10-15列(索引9-14,因为索引从0开始)
            target_columns = []
            for i in range(9, 15):  # 索引9到14,对应第10-15列
                if i < len(all_cells):
                    cell_value = all_cells[i].text.strip()
                    target_columns.append(cell_value)
                    print(f"   📝 第{i+1}列: {cell_value}")

            # 构建CSV数据(包含表头和数据行)
            csv_data = [
                ['air_time', 'block_time', 'fc', 'flight_leg', 'daily_utilization_air_time', 'daily_utilization_block time'],
                target_columns
            ]

            print(f"\n   ✅ 成功提取数据")
            print(f"   📊 提取的数据: {target_columns}")
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
        # ========== 步骤1: 点击"数据报表" ==========
        print("\n🎯 步骤1: 点击【数据报表】")
        data_report_link = page.ele('tag:a@@id=AID870')
        if data_report_link:
            data_report_link.click(by_js=True)
            print("   ✅ 已点击数据报表")
            time.sleep(2)
        else:
            print("   ❌ 未找到数据报表链接")
            return None

        # ========== 步骤2: 点击"运力统计(商飞)" ==========
        print("\n🎯 步骤2: 点击【运力统计(商飞)】")
        capacity_link = page.ele('tag:a@@text=运力统计(商飞)')
        if not capacity_link:
            capacity_link = page.ele('tag:a@href=/caphm/lineLogNewController/indexSF.html')

        if capacity_link:
            capacity_link.click(by_js=True)
            print("   ✅ 已点击运力统计(商飞)")
            time.sleep(3)
        else:
            print("   ❌ 未找到运力统计链接")
            return None

        # ========== 步骤3: 选择飞机 ==========
        print("\n🎯 步骤3: 选择飞机")
        if not self.select_aircrafts(page, self.aircraft_list):
            return None

        # ========== 步骤4: 设置时间范围 ==========
        print("\n🎯 步骤4: 设置时间范围")

        # 设置开始时间
        start_input = page.ele('tag:input@@id=startTime')
        if start_input:
            start_input.clear()
            start_input.input(target_date)
            print(f"   ✅ 开始时间设置为: {target_date}")
            time.sleep(0.5)
        else:
            print("   ⚠️ 未找到开始时间输入框")

        # 设置结束时间
        end_input = page.ele('tag:input@@id=endTime')
        if end_input:
            end_input.clear()
            end_input.input(target_date)
            print(f"   ✅ 结束时间设置为: {target_date}")
            time.sleep(0.5)
        else:
            print("   ⚠️ 未找到结束时间输入框")

        # ========== 步骤5: 点击查询 ==========
        print("\n🎯 步骤5: 点击【查询】")
        search_btn = page.ele('tag:button@@name=searchBtn')
        if search_btn:
            search_btn.click(by_js=True)
            print("   ✅ 已点击查询按钮")
        else:
            print("   ❌ 未找到查询按钮")
            return None

        # ========== 步骤6: 等待表格加载 ==========
        print("\n⏳ 等待表格加载...")
        time.sleep(5)  # 等待5秒让表格完全加载

        # 等待表格出现
        for i in range(10):
            table = page.ele('tag:table@@id=travel')
            if table:
                print(f"   ✅ 表格已加载 ({i+1}秒)")
                break
            print(f"   ⏳ 等待表格... ({i+1}/10)")
            time.sleep(1)
        else:
            print("   ❌ 表格加载超时")
            return None

        # ========== 步骤7: 提取并保存数据 ==========
        print("\n🎯 步骤7: 提取数据")
        return self.extract_table_data(page)


def main(target_date=None):
    """
    主函数:抓取航班数据

    :param target_date: 可选,指定要抓取的目标日期(YYYY-MM-DD格式)
                       如果为None,则抓取今天的数据
    """
    print("🚀 开始抓取航班数据...")

    fetcher = FlightFetcher()
    return fetcher.main(target_date)


if __name__ == "__main__":
    import sys

    # 支持命令行参数指定日期
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]

    main(target_date)

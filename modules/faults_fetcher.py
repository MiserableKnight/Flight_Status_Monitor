# -*- coding: utf-8 -*-
"""
故障数据抓取模块

功能:
- 导航到综合监控页面
- 选择指定的飞机(通过序列号/飞机号筛选)
- 点击查询按钮
- 获取并保存故障数据(包含航段历史)
"""
import time
import re
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from modules.base_fetcher import BaseFetcher


class FaultsFetcher(BaseFetcher):
    """故障数据抓取器"""

    def get_data_prefix(self):
        """返回数据文件前缀"""
        return "faults_data"

    def select_aircrafts(self, page, aircraft_list):
        """在故障监控页面选择指定的飞机"""
        print(f"\n📋 开始选择飞机...")

        # 先尝试找到标签"序列号/飞机号"旁边的下拉框
        # 方法1: 通过查找标签文本定位
        label_ele = page.ele('tag:p@text()=序列号/飞机号:')
        if label_ele:
            print("   ✅ 找到标签: 序列号/飞机号")

            # 找到标签旁边的下拉框 div
            # 尝试多种方式定位
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
                print("   ✅ 已点击序列号/飞机号下拉框")
            else:
                print("   ❌ 未找到序列号/飞机号下拉框")
                # 打印页面结构帮助调试
                print("   🔍 调试信息: 打印页面上的所有filter-option...")
                all_divs = page.eles('tag:div')
                for div in all_divs[:20]:  # 只打印前20个
                    cls = div.attr('class') or ''
                    if 'filter' in cls.lower():
                        print(f"      找到: class={cls}")
                return False
        else:
            print("   ❌ 未找到'序列号/飞机号'标签")
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
        for aircraft in aircraft_list:
            # 重新获取元素列表
            text_elements = page.eles('tag:span@@class=text')
            found = False
            for ele in text_elements:
                text = ele.text.strip()
                # 使用包含匹配,但要确保匹配到的是飞机相关选项
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
                    found = True
                    break

            if not found:
                print(f"   ❌ 未找到飞机: {aircraft}")

        # 点击其他地方关闭下拉框
        try:
            page.ele('tag:body').click()
        except:
            pass

        time.sleep(1)
        return True

    def extract_history_info(self, history_li):
        """从航段历史 li 元素中提取历史信息"""
        try:
            # 获取所有 history block
            history_blocks = history_li.eles('tag:div@@class=hl_block')

            if not history_blocks:
                return ''

            # 统计每个 block 的历史数据
            history_summary = []

            for idx, block in enumerate(history_blocks, 1):
                # 从 onmouseover 属性提取历史数据
                onmouseover_attr = block.attr('onmouseover')
                if onmouseover_attr and 'showHistoryPopDiv' in onmouseover_attr:
                    # 提取参数中的历史数据 (第3个参数)
                    match = re.search(r"showHistoryPopDiv\([^,]+,[^,]+,'([^']+)'\)", onmouseover_attr)
                    if match:
                        history_data = match.group(1)
                        # 统计各种状态的次数
                        phases = history_data.split(',')
                        phase_count = {}
                        for phase in phases:
                            phase = phase.strip()
                            if phase and phase != 'null':
                                phase_count[phase] = phase_count.get(phase, 0) + 1

                        # 生成摘要
                        if phase_count:
                            summary_parts = [f"{k}:{v}" for k, v in sorted(phase_count.items())]
                            history_summary.append(f"组{idx}({','.join(summary_parts)})")

            return '; '.join(history_summary) if history_summary else f'{len(history_blocks)}组'

        except Exception as e:
            # 如果解析失败,返回简单的统计
            history_blocks = history_li.eles('tag:div@@class=hl_block')
            return f'{len(history_blocks)}组(详细解析失败)'

    def extract_fault_data(self, page, target_date=None):
        """从综合监控页面提取故障数据(逐行提取,包含子行)"""
        print("\n📊 开始提取故障数据...")

        if not target_date:
            target_date = self.get_today_date()

        try:
            # 找到数据容器 div id="dataCon"
            data_container = page.ele('tag:div@@id=dataCon')
            if not data_container:
                print("   ❌ 未找到数据容器")
                return None

            # 获取所有包含数据的 ul 元素
            # 根据HTML结构,每行数据在一个 ul 标签内
            all_uls = data_container.eles('tag:ul')
            print(f"   ✅ 找到 {len(all_uls)} 个数据行")

            if not all_uls:
                print("   ❌ 没有故障数据")
                return None

            # 提取每条故障记录
            csv_data = []
            csv_data.append([
                '飞机号', '机型', '航空公司', '航班号', '航段数', '当前航段',
                '消息时间', '故障描述', '飞行阶段', '故障类型', '状态',
                '处理人', '类别-优先权', '航段历史'
            ])

            for idx, ul_row in enumerate(all_uls, 1):
                try:
                    # 获取所有 li 元素
                    li_elements = ul_row.eles('tag:li@@class=li0')

                    if len(li_elements) < 8:
                        continue  # 跳过不完整的行

                    # 第7个li: 消息时间(用于日期检查)
                    message_time = ''
                    if li_elements[6]:
                        message_time = li_elements[6].text.strip()

                    # 检查日期,如果不是当天数据则停止提取
                    if message_time and len(message_time) >= 10:
                        row_date = message_time[:10]  # 提取日期部分 YYYY-MM-DD
                        if row_date != target_date:
                            print(f"   ⏹️  第 {idx} 行日期为 {row_date},不是目标日期 {target_date},停止提取")
                            print(f"   ✅ 已提取 {len(csv_data)-1} 条当天数据")
                            break

                    print(f"   📝 处理第 {idx}/{len(all_uls)} 条记录...")

                    # 提取各个字段
                    aircraft = ''
                    aircraft_type = ''
                    airline = ''
                    flight_no = ''
                    leg_count = ''
                    current_leg = ''
                    fault_desc = ''
                    flight_phase = ''
                    fault_type = ''
                    state = ''
                    handler = ''
                    class_priority = ''  # 类别-优先权
                    history_info = ''

                    # 第1个li: 飞机号
                    if li_elements[0]:
                        aircraft_p = li_elements[0].ele('tag:p')
                        if aircraft_p:
                            aircraft = aircraft_p.text.strip()

                    # 第2个li: 机型
                    if li_elements[1]:
                        aircraft_type = li_elements[1].text.strip()

                    # 第3个li: 航空公司
                    if li_elements[2]:
                        airline = li_elements[2].text.strip()

                    # 第4个li: 航班号
                    if li_elements[3]:
                        flight_no = li_elements[3].text.strip()

                    # 第5个li: 航段数
                    if li_elements[4]:
                        leg_count = li_elements[4].text.strip()

                    # 第6个li: 当前航段
                    if li_elements[5]:
                        current_leg = li_elements[5].text.strip()

                    # 第8个li: 故障描述和重复标志
                    if li_elements[7]:
                        # 检查是否有重复标志图标(通过查找所有 img 元素)
                        try:
                            all_imgs = li_elements[7].eles('tag:img')
                            for img in all_imgs:
                                # 检查图片的 title 属性是否包含"重复"相关文本
                                title = img.attr('title') or ''
                                if '重复' in title or '连续' in title:
                                    fault_desc = '[R] '  # 添加重复标志
                                    break
                        except:
                            pass

                        fault_link = li_elements[7].ele('tag:a')
                        if fault_link:
                            fault_desc += fault_link.text.strip()

                        # 从 hidden input 获取故障类型
                        fault_type_input = li_elements[7].ele('tag:input@@name=type')
                        if fault_type_input:
                            fault_type = fault_type_input.attr('value')

                    # 第9个li: 飞行阶段
                    if len(li_elements) > 8 and li_elements[8]:
                        flight_phase = li_elements[8].text.strip()

                    # 第10个li: 处理人
                    if len(li_elements) > 9 and li_elements[9]:
                        handler = li_elements[9].text.strip()

                    # 第11个li: 状态
                    if len(li_elements) > 10 and li_elements[10]:
                        state_div = li_elements[10].ele('tag:div')
                        if state_div:
                            state = state_div.text.strip()

                    # 第12个li: 类别-优先权
                    if len(li_elements) > 11 and li_elements[11]:
                        # 获取这个 li 内部的所有 div
                        inner_divs = li_elements[11].eles('tag:div')
                        for div in inner_divs:
                            text = div.text.strip()
                            if text and text not in ['类别', '优先权']:
                                class_priority = text
                                break

                    # 第13个li: 航段历史
                    if len(li_elements) > 12 and li_elements[12]:
                        history_info = self.extract_history_info(li_elements[12])

                    # 添加到数据列表
                    csv_data.append([
                        aircraft, aircraft_type, airline, flight_no, leg_count, current_leg,
                        message_time, fault_desc, flight_phase, fault_type, state,
                        handler, class_priority, history_info
                    ])

                    print(f"      ✅ {aircraft} | {fault_desc[:40] if fault_desc else ''}... | {message_time}")

                except Exception as e:
                    print(f"      ⚠️ 解析第 {idx} 行出错: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            print(f"\n   ✅ 成功提取 {len(csv_data)-1} 条故障记录")
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
        # ========== 步骤1: 点击"综合监控" ==========
        print("\n🎯 步骤1: 点击【综合监控】")
        integrated_monitor_link = page.ele('tag:a@@id=AID1932')
        if integrated_monitor_link:
            integrated_monitor_link.click(by_js=True)
            print("   ✅ 已点击综合监控")
            time.sleep(3)
        else:
            print("   ❌ 未找到综合监控链接")
            return None

        # ========== 步骤2: 选择飞机 ==========
        print("\n🎯 步骤2: 选择飞机")
        if not self.select_aircrafts(page, self.aircraft_list):
            return None

        # ========== 步骤3: 点击查询 ==========
        print("\n🎯 步骤3: 点击【查询】")
        search_btn = page.ele('tag:input@@value=查询')
        if not search_btn:
            search_btn = page.ele('tag:input@@onclick=showDataNew()')

        if search_btn:
            search_btn.click(by_js=True)
            print("   ✅ 已点击查询按钮")
        else:
            print("   ❌ 未找到查询按钮")
            return None

        # ========== 步骤4: 等待数据加载 ==========
        print("\n⏳ 等待数据加载...")
        time.sleep(5)

        # 等待数据容器出现
        for i in range(10):
            data_container = page.ele('tag:div@@id=dataCon')
            if data_container:
                print(f"   ✅ 数据已加载 ({i+1}秒)")
                break
            print(f"   ⏳ 等待数据加载... ({i+1}/10)")
            time.sleep(1)
        else:
            print("   ❌ 数据加载超时")
            return None

        # ========== 步骤5: 提取数据 ==========
        print("\n🎯 步骤5: 提取数据")
        return self.extract_fault_data(page, target_date=target_date)


def main(target_date=None):
    """
    主函数:抓取故障数据

    :param target_date: 可选,指定要抓取的目标日期(YYYY-MM-DD格式)
                       如果为None,则抓取今天的数据
    """
    print("🚀 开始抓取故障数据...")

    fetcher = FaultsFetcher()
    return fetcher.main(target_date)


if __name__ == "__main__":
    import sys

    # 支持命令行参数指定日期
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]

    main(target_date)

# -*- coding: utf-8 -*-
from DrissionPage import ChromiumPage, ChromiumOptions
import time
import csv
import configparser
import os
from datetime import datetime
from logger import get_logger

# ================= 配置文件读取 =================
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.ini')

def load_config():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"❌ 配置文件不存在: {CONFIG_FILE}")
    config.read(CONFIG_FILE, encoding='utf-8')
    try:
        return {
            'username': config.get('credentials', 'username'),
            'password': config.get('credentials', 'password'),
            'user_data_path': config.get('paths', 'user_data_path'),
            'target_url': config.get('target', 'url')
        }
    except Exception as e:
        raise ValueError(f"配置文件缺失: {e}")

try:
    cfg = load_config()
    USER_DATA_PATH = cfg['user_data_path']

    # 读取飞机号列表
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')

    if config.has_section('aircraft') and config.has_option('aircraft', 'aircraft_list'):
        aircraft_list_str = config.get('aircraft', 'aircraft_list')
        AIRCRAFT_LIST = [x.strip() for x in aircraft_list_str.split(',')]
        print(f"✅ 读取到 {len(AIRCRAFT_LIST)} 架飞机: {', '.join(AIRCRAFT_LIST)}")
    else:
        print("⚠️ 配置文件中未找到飞机号列表，使用默认值")
        AIRCRAFT_LIST = ["B-652G", "B-656E"]
except Exception as e:
    print(f"❌ 初始化失败: {e}")
    exit(1)

# Initialize logger
log = get_logger()
log("Faults Data Fetch Script Started")

# ================= 数据抓取主逻辑 =================

def get_today_date():
    """获取当天日期，格式: YYYY-MM-DD"""
    return datetime.now().strftime("%Y-%m-%d")

def wait_and_click(page, selector, timeout=10, desc="元素"):
    """等待元素出现并点击"""
    for i in range(timeout):
        ele = page.ele(selector)
        if ele and ele.states.is_displayed:
            print(f"   ✅ 找到 {desc}")
            ele.click(by_js=True)
            time.sleep(1)
            return True
        time.sleep(1)
        print(f"   ⏳ 等待 {desc}... ({i+1}/{timeout})")
    print(f"   ❌ 超时: 未找到 {desc}")
    return False

def select_fault_aircrafts(page, aircraft_list):
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

        # 方法1: 查找标签的父元素，然后找同级的下拉框
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

        # 方法2: 如果上面都失败，直接查找所有 filter-option
        if not aircraft_dropdown:
            all_dropdowns = page.eles('tag:div@@class=filter-option')
            if len(all_dropdowns) > 0:
                # 通常是第一个或第二个
                aircraft_dropdown = all_dropdowns[0]
                print(f"   ✅ 找到 {len(all_dropdowns)} 个下拉框，使用第一个")

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

    # 先取消所有已选择的飞机选项（只取消包含飞机号的选项）
    print("   🔍 检查并清除已选项...")
    text_elements = page.eles('tag:span@@class=text')
    for ele in text_elements:
        parent = ele.parent()
        if parent:
            parent_attr = parent.attr('class') or ''
            if 'selected' in parent_attr or 'active' in parent_attr:
                # 只取消包含飞机号（B-开头）或完整航班的选项
                text = ele.text.strip()
                if text.startswith('B-') or text.startswith('C909-'):
                    print(f"   🔄 取消选择: {text}")
                    parent.click(by_js=True)
                    time.sleep(0.3)

    time.sleep(1)

    # 选择指定的飞机（直接匹配飞机号）
    print("   🎯 开始选择目标飞机...")
    for aircraft in aircraft_list:
        # 重新获取元素列表
        text_elements = page.eles('tag:span@@class=text')
        found = False
        for ele in text_elements:
            text = ele.text.strip()
            # 使用包含匹配，但要确保匹配到的是飞机相关选项
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

def extract_fault_data(page, target_date=None):
    """从综合监控页面提取故障数据（逐行提取，包含子行）"""
    print("\n📊 开始提取故障数据...")

    if not target_date:
        target_date = get_today_date()

    try:
        # 找到数据容器 div id="dataCon"
        data_container = page.ele('tag:div@@id=dataCon')
        if not data_container:
            print("   ❌ 未找到数据容器")
            return None

        # 获取所有包含数据的 ul 元素
        # 根据HTML结构，每行数据在一个 ul 标签内
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

                # 第7个li: 消息时间（用于日期检查）
                message_time = ''
                if li_elements[6]:
                    message_time = li_elements[6].text.strip()

                # 检查日期，如果不是当天数据则停止提取
                if message_time and len(message_time) >= 10:
                    row_date = message_time[:10]  # 提取日期部分 YYYY-MM-DD
                    if row_date != target_date:
                        print(f"   ⏹️  第 {idx} 行日期为 {row_date}，不是目标日期 {target_date}，停止提取")
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
                    # 检查是否有重复标志图标（通过查找所有 img 元素）
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
                    history_info = extract_history_info(li_elements[12])

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

def extract_history_info(history_li):
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
                import re
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
        # 如果解析失败，返回简单的统计
        history_blocks = history_li.eles('tag:div@@class=hl_block')
        return f'{len(history_blocks)}组(详细解析失败)'

def save_to_csv(data, filename=None):
    """保存数据到CSV文件"""
    if not data:
        print("   ❌ 没有数据可保存")
        return None

    # 生成文件名
    if not filename:
        today = get_today_date()
        filename = f"faults_data_{today}.csv"

    # 确保data文件夹存在
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"   📁 创建data文件夹: {data_dir}")

    filepath = os.path.join(data_dir, filename)

    try:
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerows(data)
        print(f"\n✅ 数据已保存到: {filepath}")
        return filepath
    except Exception as e:
        print(f"   ❌ 保存CSV失败: {e}")
        return None

def main(target_date=None):
    """
    主函数：抓取故障数据

    :param target_date: 可选，指定要抓取的目标日期（YYYY-MM-DD格式）
                       如果为None，则抓取今天的数据
    """
    print("🚀 开始抓取故障数据...")

    # 确定要抓取的日期
    if target_date:
        target = target_date
        print(f"🎯 目标日期：{target}")
        log(f"Fetching faults data for: {target}")
    else:
        target = get_today_date()
        print(f"🎯 默认抓取今天的数据：{target}")
        log(f"Fetching today's faults data: {target}")

    # 连接到现有浏览器会话
    co = ChromiumOptions()
    co.set_user_data_path(USER_DATA_PATH)
    co.set_local_port(9222)

    try:
        page = ChromiumPage(co)
        print("✅ 浏览器连接成功！")
        log("Browser connected successfully")
    except Exception as e:
        print(f"❌ 浏览器连接失败: {e}")
        print("请先运行 automation_login.py 完成登录")
        log(f"Browser connection failed: {e}", "ERROR")
        return

    # ========== 智能登录系统 ==========
    print("\n🔍 检查当前页面状态...")
    current_url = page.url
    print(f"📍 当前URL: {current_url}")

    # 如果在新标签页，导航到登录页
    if "chrome://" in current_url or current_url == "about:blank" or "newtab" in current_url:
        print("🌐 检测到空白页，导航到登录页面...")
        page.get("https://cis2.comac.cc:8040/portal/")
        time.sleep(2)
        current_url = page.url

    # 如果不是空白页也不是登录页，直接跳转到首页
    is_blank_page = "chrome://" in current_url or current_url == "about:blank" or "newtab" in current_url
    is_login_page = ("portal" in current_url and "login" in current_url) or "rbacUsersController/login.html" in current_url

    if not is_blank_page and not is_login_page:
        print("🚀 不在登录流程中，直接跳转到系统首页...")
        page.get("https://cis.comac.cc:8004/caphm/mainController/index.html")
        time.sleep(2)
        current_url = page.url

    # 智能等待：监控所有可能的页面状态
    print("\n⏳ 智能监控页面跳转...")
    max_wait = 60
    found_target = False
    login_executed = False

    for i in range(max_wait):
        # 实时检测URL变化
        current_url = page.url

        # 情况1: 已在目标首页
        if "mainController/index.html" in current_url:
            print(f"   ✅ 已在首页！")
            found_target = True
            break

        # 情况2: 在portal登录页 - 需要填充账号密码
        elif "portal" in current_url and "login" in current_url:
            if not login_executed and page.ele('#loginPwd'):
                print(f"   🔒 检测到portal登录页，开始登录...")
                try:
                    # 填账号
                    user_ele = page.ele('tag:input@@placeholder=请输入账号')
                    if not user_ele:
                        user_ele = page.ele('tag:input@@type=text')

                    if user_ele:
                        user_ele.clear()
                        user_ele.input(cfg.get('username', ''))
                        try:
                            page.ele('text:FLYWIN').click(by_js=True)
                        except:
                            pass

                    # 填密码并提交
                    pwd_ele = page.ele('#loginPwd')
                    if pwd_ele:
                        pwd_ele.clear()
                        pwd_ele.input(cfg.get('password', ''))
                        print(f"   ⚡ 提交登录...")
                        pwd_ele.input('\n')
                        login_executed = True

                except Exception as e:
                    print(f"   ❌ 登录出错: {e}")

        # 情况3: 在rbacUsersController中间页 - 需要点击WEB
        elif "rbacUsersController/login.html" in current_url:
            web_btn = page.ele('text:WEB')
            if web_btn and web_btn.states.is_displayed:
                print(f"   👀 检测到中间页，点击 'WEB' 按钮...")
                web_btn.click(by_js=True)

        # 情况4: 已在系统内其他页面
        elif "cis.comac.cc:8004" in current_url:
            print(f"   ✅ 已在系统内")
            found_target = True
            break

        # 每5秒打印一次进度（减少输出）
        if i % 10 == 0 and i > 0:
            print(f"   ⏳ 等待中... {i//2}秒", end="\r")

        # 快速检测，0.5秒间隔
        time.sleep(0.5)

    print()  # 换行

    # 最终验证
    if found_target or "mainController/index.html" in page.url:
        print(f"🎉 准备完成！当前页面: {page.title}")
        log("系统就绪", "SUCCESS")
    else:
        print(f"❌ 超时或异常，当前页面: {page.url}")
        log("页面状态异常", "ERROR")
        return

    time.sleep(0.5)

    # ========== 步骤1: 点击"综合监控" ==========
    print("\n🎯 步骤1: 点击【综合监控】")
    integrated_monitor_link = page.ele('tag:a@@id=AID1932')
    if integrated_monitor_link:
        integrated_monitor_link.click(by_js=True)
        print("   ✅ 已点击综合监控")
        time.sleep(3)
    else:
        print("   ❌ 未找到综合监控链接")
        return

    # ========== 步骤2: 选择飞机 ==========
    print("\n🎯 步骤2: 选择飞机")
    if not select_fault_aircrafts(page, AIRCRAFT_LIST):
        return

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
        return

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
        return

    # ========== 步骤5: 提取并保存数据 ==========
    print("\n🎯 步骤5: 提取并保存数据")
    fault_data = extract_fault_data(page, target_date=target)

    if fault_data:
        csv_file = save_to_csv(fault_data, filename=f"faults_data_{target}.csv")
        if csv_file:
            print(f"\n🎉 故障数据抓取完成！")
            print(f"📄 文件路径: {csv_file}")
            print(f"📊 总记录数: {len(fault_data)-1}")
            log(f"Faults data saved successfully: {csv_file}", "SUCCESS")
        else:
            print("\n❌ 保存失败")
            log("Failed to save faults data", "ERROR")
    else:
        print("\n❌ 未提取到数据")
        log("No faults data extracted", "ERROR")

    print("\n✨ 任务完成")
    log(f"Faults data task completed for {target}", "SUCCESS")

if __name__ == "__main__":
    import sys

    # 支持命令行参数指定日期
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]

    main(target_date)

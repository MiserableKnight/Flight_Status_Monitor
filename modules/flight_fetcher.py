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
log("Flight Data Fetch Script Started")

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

def select_aircrafts(page, aircraft_list):
    """选择指定的飞机"""
    print(f"\n📋 开始选择飞机...")

    # 点击"飞机号"下拉框（使用 data-id 属性精确定位）
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

    # 先取消所有已选择的选项（防止多选）
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

    # 选择指定的飞机（精确匹配完整文本）
    aircraft_mapping = {
        "B-652G": "C909-185/B-652G",
        "B-656E": "C909-196/B-656E"
    }

    print("   🎯 开始选择目标飞机...")
    for aircraft in aircraft_list:
        target_text = aircraft_mapping.get(aircraft, aircraft)

        # 重新获取元素列表（因为DOM可能已更新）
        text_elements = page.eles('tag:span@@class=text')
        found = False
        for ele in text_elements:
            if ele.text.strip() == target_text:
                print(f"   ✅ 选择飞机: {ele.text}")
                try:
                    # 尝试点击父元素（通常是可点击的选项）
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

def extract_table_data(page):
    """从表格中提取数据（只提取最后一行的第10-15列）"""
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
            print(f"   ❌ 列数不足: 需要15列，实际只有{len(all_cells)}列")
            # 打印所有列以便调试
            for i, cell in enumerate(all_cells):
                print(f"      列{i+1}: {cell.text.strip()}")
            return None

        # 提取第10-15列（索引9-14，因为索引从0开始）
        target_columns = []
        for i in range(9, 15):  # 索引9到14，对应第10-15列
            if i < len(all_cells):
                cell_value = all_cells[i].text.strip()
                target_columns.append(cell_value)
                print(f"   📝 第{i+1}列: {cell_value}")

        # 构建CSV数据（包含表头和数据行）
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

def save_to_csv(data, filename=None):
    """保存数据到CSV文件"""
    if not data:
        print("   ❌ 没有数据可保存")
        return None

    # 生成文件名
    if not filename:
        today = get_today_date()
        filename = f"flight_data_{today}.csv"

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
    主函数：抓取航班数据

    :param target_date: 可选，指定要抓取的目标日期（YYYY-MM-DD格式）
                       如果为None，则抓取今天的数据
    """
    print("🚀 开始抓取航班数据...")

    # 确定要抓取的日期
    if target_date:
        target = target_date
        print(f"🎯 目标日期：{target}")
        log(f"Fetching data for: {target}")
    else:
        target = get_today_date()
        print(f"🎯 默认抓取今天的数据：{target}")
        log(f"Fetching today's data: {target}")

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

    # ========== 步骤1: 点击"数据报表" ==========
    print("\n🎯 步骤1: 点击【数据报表】")
    data_report_link = page.ele('tag:a@@id=AID870')
    if data_report_link:
        data_report_link.click(by_js=True)
        print("   ✅ 已点击数据报表")
        time.sleep(2)
    else:
        print("   ❌ 未找到数据报表链接")
        return

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
        return

    # 切换到右侧iframe（如果需要）
    # 根据HTML结构，内容可能在 rightframe 中
    # 这里先尝试直接在主页面操作

    # ========== 步骤3: 选择飞机 ==========
    print("\n🎯 步骤3: 选择飞机")
    if not select_aircrafts(page, AIRCRAFT_LIST):
        return

    # ========== 步骤4: 设置时间范围 ==========
    print("\n🎯 步骤4: 设置时间范围")

    # 设置开始时间
    start_input = page.ele('tag:input@@id=startTime')
    if start_input:
        start_input.clear()
        start_input.input(target)
        print(f"   ✅ 开始时间设置为: {target}")
        time.sleep(0.5)
    else:
        print("   ⚠️ 未找到开始时间输入框")

    # 设置结束时间
    end_input = page.ele('tag:input@@id=endTime')
    if end_input:
        end_input.clear()
        end_input.input(target)
        print(f"   ✅ 结束时间设置为: {target}")
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
        return

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
        return

    # ========== 步骤7: 提取并保存数据 ==========
    print("\n🎯 步骤7: 提取并保存数据")
    table_data = extract_table_data(page)

    if table_data:
        csv_file = save_to_csv(table_data, filename=f"flight_data_{target}.csv")
        if csv_file:
            print(f"\n🎉 数据抓取完成！")
            print(f"📄 文件路径: {csv_file}")
            print(f"📊 总行数: {len(table_data)}")
            log(f"Data saved successfully: {csv_file}", "SUCCESS")
        else:
            print("\n❌ 保存失败")
            log("Failed to save data", "ERROR")
    else:
        print("\n❌ 未提取到数据")
        log("No data extracted", "ERROR")

    print("\n✨ 任务完成")
    log(f"Task completed for {target}", "SUCCESS")

if __name__ == "__main__":
    import sys

    # 支持命令行参数指定日期
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]

    main(target_date)

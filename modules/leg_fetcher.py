# -*- coding: utf-8 -*-
"""
航段数据抓取模块

功能：
- 导航到航段数据页面 (lineLogController/index.html)
- 选择指定的飞机（通过序列号筛选）
- 设置日期为当天
- 点击查询按钮
- 获取并保存航段数据
"""
from DrissionPage import ChromiumPage, ChromiumOptions
import time
import csv
import configparser
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.logger import get_logger

# ================= 配置文件读取 =================
CONFIG_FILE = os.path.join(project_root, 'config/config.ini')

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
log("Leg Data Fetch Script Started")

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
    """选择指定的飞机（通过序列号筛选）"""
    print(f"\n📋 开始选择飞机...")

    # 等待页面完全加载
    print("   ⏳ 等待页面元素加载...")
    time.sleep(3)

    # 使用与 faults_fetcher.py 相同的成熟模式
    # 方法1: 通过查找标签文本定位
    label_ele = page.ele('tag:p@text()=序列号:')
    if label_ele:
        print("   ✅ 找到标签: 序列号")

        # 找到标签旁边的下拉框 div
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

    # 先取消所有已选择的飞机选项（只取消包含飞机号的选项）
    print("   🔍 检查并清除已选项...")
    text_elements = page.eles('tag:span@@class=text')
    for ele in text_elements:
        parent = ele.parent()
        if parent:
            parent_attr = parent.attr('class') or ''
            if 'selected' in parent_attr or 'active' in parent_attr:
                # 只取消包含飞机号（B-开头）的选项
                text = ele.text.strip()
                if text.startswith('B-'):
                    print(f"   🔄 取消选择: {text}")
                    parent.click(by_js=True)
                    time.sleep(0.3)

    time.sleep(1)

    # 选择指定的飞机（直接匹配飞机号）
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

def extract_table_data(page):
    """从表格中提取航段数据"""
    print("\n📊 开始提取表格数据...")

    try:
        # 找到数据容器 #dataCon
        data_con = page.ele('tag:div@@id=dataCon')
        if not data_con:
            print("   ❌ 未找到数据容器 #dataCon")
            return None

        print("   ✅ 找到数据容器")

        # 找到数据行（.tr_title）
        rows = data_con.eles('tag:div@@class=tr_title')
        print(f"   ✅ 找到 {len(rows)} 行数据")

        if not rows:
            print("   ❌ 表格为空")
            return None

        # 表头（固定的列名）
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

                # 提取数据（跳过前几个div，它们是复选框等）
                row_data = []
                # 从第2个div开始（索引1），每4个div中取第3个（包含文本的）
                # 实际结构：checkbox div -> 文本div -> span -> ...

                # 更简单的方法：直接获取所有有文本的 div
                for cell in cells:
                    text = cell.text.strip()
                    if text and text not in ['', '\n', '\t']:
                        # 过滤掉复选框等非数据元素
                        # 数据div通常有特定的宽度样式
                        style = cell.attr('style') or ''
                        if 'width' in style or 'text-align' in style:
                            row_data.append(text)

                # 只取前15列
                if len(row_data) >= 15:
                    data_rows.append(row_data[:15])
                    print(f"   📝 第{i+1}行: {row_data[0]} - {row_data[1]} - {row_data[3]}")
                else:
                    print(f"   ⚠️ 第{i+1}行数据不完整: {len(row_data)}列")

            except Exception as e:
                print(f"   ⚠️ 提取第{i+1}行失败: {e}")
                continue

        if not data_rows:
            print("   ❌ 未能提取到有效数据")
            return None

        # 构建CSV数据（表头 + 数据行）
        csv_data = [headers] + data_rows

        print(f"\n   ✅ 成功提取 {len(data_rows)} 行数据")
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
        filename = f"leg_data_{today}.csv"

    # 确保data文件夹存在
    data_dir = os.path.join(project_root, 'data/daily_raw')
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
    主函数：抓取航段数据

    :param target_date: 可选，指定要抓取的目标日期（YYYY-MM-DD格式）
                       如果为None，则抓取今天的数据
    """
    print("🚀 开始抓取航段数据...")

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
        print("请先启动Chrome调试模式")
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

    # ========== 步骤1: 导航到航段数据页面 ==========
    print("\n🎯 步骤1: 导航到航段数据页面")
    target_url = "https://cis.comac.cc:8004/caphm/lineLogController/index.html"

    current_url = page.url
    if "lineLogController/index.html" in current_url:
        print("   ✅ 已在航段数据页面")
    else:
        print(f"   📍 正在导航到: {target_url}")
        page.get(url=target_url)

        # 等待页面加载完成
        print("   ⏳ 等待页面加载...")
        time.sleep(5)  # 增加等待时间到5秒
        print("   ✅ 已导航到航段数据页面")

    # ========== 步骤2: 选择飞机 ==========
    print("\n🎯 步骤2: 选择飞机")
    if not select_aircrafts(page, AIRCRAFT_LIST):
        return

    # ========== 步骤3: 设置时间范围 ==========
    print("\n🎯 步骤3: 设置时间范围")

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

    # ========== 步骤4: 点击查询 ==========
    print("\n🎯 步骤4: 点击【查询】")
    query_btn = page.ele('tag:input@@value=查询 @@class=button_partial2')
    if query_btn:
        query_btn.click(by_js=True)
        print("   ✅ 已点击查询按钮")
    else:
        print("   ❌ 未找到查询按钮")
        return

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
        return

    # ========== 步骤6: 提取并保存数据 ==========
    print("\n🎯 步骤6: 提取并保存数据")
    table_data = extract_table_data(page)

    if table_data:
        csv_file = save_to_csv(table_data, filename=f"leg_data_{target}.csv")
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

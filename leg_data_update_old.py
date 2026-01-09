# -*- coding: utf-8 -*-
"""
Leg Data Update Script
更新航段数据到主CSV文件，支持状态变化邮件通知
功能：
1. 将每日获取的leg data添加到总表
2. 统一航班号格式（前两位改为VJ）
3. 计算空中时间（ON-OFF）和空地时间（IN-OUT）
4. 追踪航班状态变化并发送邮件通知
5. 根据历史数据预计落地时间
"""
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
import json
import re

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from core.logger import get_logger
from core.email_notifier import FlightStatusNotifier

# 初始化日志
log = get_logger()

# 每架飞机的航班序列（按时间顺序，从晚到早）
AIRCRAFT_FLIGHTS = {
    'B-656E': ['VJ107', 'VJ118', 'VJ119', 'VJ108'],
    'B-652G': ['VJ105', 'VJ112', 'VJ113', 'VJ106']
}

# 航班信息（航班号: 航线描述）
FLIGHT_INFO = {
    'VJ108': '昆岛飞河内',
    'VJ119': '胡志明飞昆岛',
    'VJ106': '昆岛飞河内',
    'VJ113': '胡志明飞昆岛',
    'VJ118': '昆岛飞胡志明',
    'VJ112': '昆岛飞胡志明',
    'VJ107': '河内飞昆岛',
    'VJ105': '河内飞昆岛'
}

# 机场名称映射
AIRPORT_MAPPING = {
    'VVCS-昆仑国际机场': '昆岛',
    'VVNB-内排国际机场': '河内',
    'VVTS-新山一国际机场': '胡志明'
}

# 状态追踪配置
STATUS_FILE = os.path.join(project_root, 'data', 'leg_status.json')


def calculate_time_diff(off_time, on_time):
    """
    计算时间差（分钟）
    :param off_time: 起飞时间 (HH:MM)
    :param on_time: 着陆时间 (HH:MM)
    :return: 时间差（分钟），如果任一时间为空则返回None
    """
    if pd.isna(off_time) or pd.isna(on_time) or off_time == '' or on_time == '':
        return None

    try:
        # 解析时间
        off_hour, off_min = map(int, str(off_time).split(':'))
        on_hour, on_min = map(int, str(on_time).split(':'))

        # 计算分钟差
        off_minutes = off_hour * 60 + off_min
        on_minutes = on_hour * 60 + on_min

        # 处理跨天情况（如果着陆时间小于起飞时间，说明跨天）
        if on_minutes < off_minutes:
            on_minutes += 24 * 60

        return on_minutes - off_minutes
    except Exception as e:
        log(f"计算时间差失败: {e}, off_time={off_time}, on_time={on_time}", "ERROR")
        return None


def format_minutes(minutes):
    """
    将分钟数格式化为 "X小时Y分钟" 格式
    :param minutes: 分钟数
    :return: 格式化字符串
    """
    if minutes is None or minutes <= 0:
        return "未知"

    hours = minutes // 60
    mins = minutes % 60

    if hours > 0 and mins > 0:
        return f"{hours}小时{mins}分钟"
    elif hours > 0:
        return f"{hours}小时"
    else:
        return f"{mins}分钟"


def normalize_flight_number(flight_num):
    """
    统一航班号格式，将前两位字母改为VJ（大写）
    :param flight_num: 原始航班号
    :return: 标准化后的航班号
    """
    if pd.isna(flight_num) or flight_num == '':
        return flight_num

    flight_num = str(flight_num).strip().upper()

    # 使用正则表达式提取数字部分
    match = re.match(r'^[A-Z]*(\d+)$', flight_num)
    if match:
        num_part = match.group(1)
        return f'VJ{num_part}'

    return flight_num


def load_status():
    """
    加载航班状态文件
    :return: 状态字典
    """
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"加载状态文件失败: {e}", "ERROR")
            return {}
    return {}


def save_status(status_data):
    """
    保存航班状态到文件
    :param status_data: 状态字典
    """
    try:
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"保存状态文件失败: {e}", "ERROR")


def get_flight_key(flight_num, date_str):
    """
    生成航班唯一标识键
    :param flight_num: 航班号
    :param date_str: 日期字符串
    :return: 唯一键
    """
    return f"{flight_num}_{date_str}"


def parse_time_vietnam(time_str):
    """
    解析时间字符串并转换为越南时间（实际时间-1小时）
    :param time_str: 时间字符串 (HH:MM)
    :return: 越南时间字符串 (HH:MM)，如果解析失败返回None
    """
    if pd.isna(time_str) or time_str == '':
        return None

    try:
        hour, minute = map(int, str(time_str).split(':'))
        # 减去1小时（考虑跨天）
        hour -= 1
        if hour < 0:
            hour += 24

        return f"{hour:02d}:{minute:02d}"
    except:
        return None


def get_airport_name(airport_full):
    """
    从完整机场名称获取简短名称
    :param airport_full: 完整机场名称（如 "VVCS-昆仑国际机场"）
    :return: 简短名称（如 "昆岛"）
    """
    if pd.isna(airport_full):
        return "未知"

    return AIRPORT_MAPPING.get(str(airport_full), str(airport_full).split('-')[-1] if '-' in str(airport_full) else str(airport_full))


def is_flight_completed(row):
    """
    判断航班是否已完成（所有4个阶段都有值）
    :param row: 数据行
    :return: True表示已完成，False表示未完成
    """
    out = not pd.isna(row['OUT']) and row['OUT'] != ''
    off = not pd.isna(row['OFF']) and row['OFF'] != ''
    on = not pd.isna(row['ON']) and row['ON'] != ''
    inn = not pd.isna(row['IN']) and row['IN'] != ''

    return out and off and on and inn


def get_current_flight_status(df_aircraft, aircraft_num):
    """
    获取飞机当前正在执行的航班状态

    :param df_aircraft: 该飞机的所有航班数据
    :param aircraft_num: 飞机号
    :return: (状态消息列表) - 每架飞机只返回一条状态消息
    """
    flight_sequence = AIRCRAFT_FLIGHTS.get(aircraft_num, [])

    # 按航班序列顺序查找第一个未完成的航班
    current_flight = None
    current_row = None
    last_completed_flight = None
    last_completed_row = None

    for flight_num in flight_sequence:
        # 找到该航班的数据行
        flight_rows = df_aircraft[df_aircraft['航班号'] == flight_num]
        if len(flight_rows) > 0:
            row = flight_rows.iloc[0]
            completed = is_flight_completed(row)

            if completed:
                # 记录最后一个已完成的航班
                last_completed_flight = flight_num
                last_completed_row = row
            else:
                # 找到第一个未完成的航班
                current_flight = flight_num
                current_row = row
                break

    # 如果找到当前正在执行的航班
    if current_row is not None:
        out_val = current_row['OUT'] if not pd.isna(current_row['OUT']) and current_row['OUT'] != '' else None
        off_val = current_row['OFF'] if not pd.isna(current_row['OFF']) and current_row['OFF'] != '' else None
        on_val = current_row['ON'] if not pd.isna(current_row['ON']) and current_row['ON'] != '' else None
        inn_val = current_row['IN'] if not pd.isna(current_row['IN']) and current_row['IN'] != '' else None

        # 根据状态生成消息
        if inn_val is not None:
            # 已滑入 - 这是下一个航班的准备状态
            airport = get_airport_name(current_row['着陆机场'])
            # 查找下一个航班
            current_idx = flight_sequence.index(current_flight)
            if current_idx < len(flight_sequence) - 1:
                next_flight = flight_sequence[current_idx + 1]
                return [f"{aircraft_num}在{airport}未起飞，计划执行{next_flight}"]
            else:
                return [f"{aircraft_num}在{airport}已完成今日航班"]

        elif on_val is not None:
            # 已着陆
            vn_time = parse_time_vietnam(on_val)
            time_str = f"越南时间{vn_time}" if vn_time else "越南时间未知"
            airport = get_airport_name(current_row['着陆机场'])
            return [f"{aircraft_num}执行{current_flight}航班，已于{time_str}在{airport}着陆"]

        elif off_val is not None:
            # 已起飞
            vn_time = parse_time_vietnam(off_val)
            time_str = f"越南时间{vn_time}" if vn_time else "越南时间未知"
            airport = get_airport_name(current_row['起飞机场'])
            return [f"{aircraft_num}执行{current_flight}航班，已于{time_str}从{airport}起飞"]

        elif out_val is not None:
            # 已滑出
            vn_time = parse_time_vietnam(out_val)
            time_str = f"越南时间{vn_time}" if vn_time else "越南时间未知"
            airport = get_airport_name(current_row['起飞机场'])
            return [f"{aircraft_num}执行{current_flight}航班，已于{time_str}滑出"]

        else:
            # 还未开始
            return [f"{aircraft_num}计划执行{current_flight}航班"]

    # 如果所有航班都完成了
    elif last_completed_row is not None:
        airport = get_airport_name(last_completed_row['着陆机场'])
        # 查找下一个航班
        last_idx = flight_sequence.index(last_completed_flight)
        if last_idx < len(flight_sequence) - 1:
            next_flight = flight_sequence[last_idx + 1]
            return [f"{aircraft_num}在{airport}未起飞，计划执行{next_flight}"]
        else:
            # 所有航班都已完成
            return [f"{aircraft_num}在{airport}已完成今日所有航班"]

    # 如果没有任何数据
    return [f"{aircraft_num}暂无航班数据"]


def get_aircraft_status_notifications(df_new):
    """
    获取所有飞机的当前状态通知

    :param df_new: 当天的航班数据
    :return: 通知消息列表
    """
    notifications = []

    # 按飞机分组
    for aircraft_num in AIRCRAFT_FLIGHTS.keys():
        df_aircraft = df_new[df_new['执飞飞机'] == aircraft_num]

        if len(df_aircraft) == 0:
            notifications.append(f"{aircraft_num}暂无今日航班数据")
            continue

        # 获取该飞机的当前状态
        status_messages = get_current_flight_status(df_aircraft, aircraft_num)
        notifications.extend(status_messages)

    return notifications


def update_leg_data(target_date=None):
    """
    更新航段数据到主表

    :param target_date: 可选，指定要更新的目标日期（YYYY-MM-DD格式）
                       如果为None，则更新今天的数据
    :return: 是否成功
    """
    log("航段数据更新脚本启动")

    # 确定目标日期
    if target_date:
        target = datetime.strptime(target_date, '%Y-%m-%d').date()
    else:
        target = datetime.now().date()

    target_date_str = target.strftime('%Y-%m-%d')

    print(f"📅 目标日期：{target_date_str}")

    # 文件路径
    main_file = os.path.join(project_root, 'data', 'leg_data.csv')
    daily_file = os.path.join(project_root, 'data', 'daily_raw', f'leg_data_{target_date_str}.csv')

    # 检查每日数据文件是否存在
    if not os.path.exists(daily_file):
        print(f"❌ 错误：找不到当天数据文件 {daily_file}")
        log(f"Daily data file not found: {daily_file}", "ERROR")
        return False

    # 读取每天的数据
    print(f"📖 读取每日数据文件...")
    try:
        df_daily = pd.read_csv(daily_file)
        print(f"   ✅ 读取到 {len(df_daily)} 行数据")
    except Exception as e:
        print(f"❌ 读取每日数据文件失败：{e}")
        log(f"Failed to read daily data: {e}", "ERROR")
        return False

    # 如果主文件不存在，创建新的
    if not os.path.exists(main_file):
        print(f"⚠️ 主文件不存在，将创建新文件")
        df_main = pd.DataFrame()
    else:
        # 读取主数据文件
        print(f"📖 读取主数据文件...")
        try:
            df_main = pd.read_csv(main_file)
            print(f"   ✅ 读取到 {len(df_main)} 行数据")
        except Exception as e:
            print(f"❌ 读取主数据文件失败：{e}")
            log(f"Failed to read main data: {e}", "ERROR")
            return False

    # 删除主文件中当天的所有数据（如果存在）
    if len(df_main) > 0 and '日期' in df_main.columns:
        original_count = len(df_main)

        # 解析目标日期为 datetime 对象
        target_dt = datetime.strptime(target_date_str, '%Y-%m-%d')

        # 标准化日期格式以便比较（处理 / 和 - 两种格式）
        def normalize_and_parse(date_str):
            if pd.isna(date_str):
                return None
            date_str = str(date_str).strip()
            # 替换 / 为 -
            date_str = date_str.replace('/', '-')
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except:
                return None

        df_main_temp = df_main.copy()
        df_main_temp['日期_解析'] = df_main_temp['日期'].apply(normalize_and_parse)

        # 删除当天数据
        df_main = df_main[df_main_temp['日期_解析'] != target_dt.date()]

        removed_count = original_count - len(df_main)
        if removed_count > 0:
            print(f"   🗑️ 删除了 {removed_count} 行当天旧数据")

    # 标准化航班号并添加计算字段
    print(f"🔄 处理数据...")

    # 创建新数据副本
    df_new = df_daily.copy()

    # 标准化航班号
    if '航班号' in df_new.columns:
        df_new['航班号'] = df_new['航班号'].apply(normalize_flight_number)
        print(f"   ✅ 航班号已标准化")

    # 计算空中时间和空地时间
    if 'OFF' in df_new.columns and 'ON' in df_new.columns:
        df_new['空中时间(分钟)'] = df_new.apply(
            lambda row: calculate_time_diff(row['OFF'], row['ON']),
            axis=1
        )
        print(f"   ✅ 计算空中时间")

    if 'OUT' in df_new.columns and 'IN' in df_new.columns:
        df_new['空地时间(分钟)'] = df_new.apply(
            lambda row: calculate_time_diff(row['OUT'], row['IN']),
            axis=1
        )
        print(f"   ✅ 计算空地时间")

    # 确保所有必需的列都存在（与 daily raw 文件结构一致）
    required_columns = [
        '日期', '执飞飞机', '航班号', '起飞机场', '着陆机场', 'MSN',
        'OUT', 'OFF', 'ON', 'IN', '运行情况',
        'OUT油量(kg)', 'OFF油量(kg)', 'ON油量(kg)', 'IN油量(kg)',
        '空中时间(分钟)', '空地时间(分钟)'
    ]

    # 添加缺失的列
    for col in required_columns:
        if col not in df_new.columns:
            df_new[col] = None

    # 重新排列列顺序
    df_new = df_new[required_columns]

    # 合并数据
    if len(df_main) > 0:
        # 使用新数据的列结构（标准化的列）
        # 对于主文件中缺少的列，填充None
        for col in df_new.columns:
            if col not in df_main.columns:
                df_main[col] = None

        # 重新排列主文件的列以匹配新数据的顺序
        df_main = df_main[df_new.columns]

        df_updated = pd.concat([df_main, df_new], ignore_index=True)
    else:
        df_updated = df_new.copy()

    # 保存更新后的主文件
    try:
        # 先保存到临时文件
        temp_file = main_file + '.tmp'
        df_updated.to_csv(temp_file, index=False, encoding='utf-8-sig')

        # 删除原文件
        if os.path.exists(main_file):
            os.remove(main_file)

        # 重命名临时文件
        os.rename(temp_file, main_file)

        print(f"\n✅ 已更新主数据文件：{main_file}")
        print(f"📊 总行数：{len(df_updated)}")
        log(f"Updated main file: {main_file}, added {len(df_new)} rows", "SUCCESS")
    except Exception as e:
        print(f"❌ 保存主数据文件失败：{e}")
        log(f"Failed to save main data: {e}", "ERROR")
        # 清理临时文件
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        return False

    # 检测状态变化并发送通知
    print(f"\n📧 检查状态变化...")

    # 初始化通知器
    notifier = FlightStatusNotifier()

    if notifier.is_enabled():
        # 获取所有飞机的当前状态通知
        all_notifications = get_aircraft_status_notifications(df_new)

        # 发送通知邮件
        if all_notifications:
            if notifier.send_flight_status_notification(all_notifications, target_date_str):
                print(f"   ✅ 已发送状态通知邮件（{len(all_notifications)}条）")
                log(f"Sent status notification: {len(all_notifications)} changes", "SUCCESS")
            else:
                print(f"   ⚠️ 邮件发送失败")
        else:
            print(f"   ℹ️ 无状态变化")
    else:
        print(f"   ⚠️ 邮件通知未启用，跳过状态通知")

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("航段数据更新脚本")
    print("=" * 60)

    # 支持命令行参数指定日期
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]

    success = update_leg_data(target_date)

    if success:
        print("\n✅ 更新完成！")
        sys.exit(0)
    else:
        print("\n⚠️ 更新失败")
        sys.exit(1)

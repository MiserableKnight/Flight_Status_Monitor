# -*- coding: utf-8 -*-
"""
航班状态监控脚本
功能：
- 对比新旧数据，检测航班状态变化
- 发送状态变化邮件通知
"""
import pandas as pd
from datetime import datetime
import os
import sys

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

# 机场名称映射
AIRPORT_MAPPING = {
    'VVCS-昆仑国际机场': '昆岛',
    'VVNB-内排国际机场': '河内',
    'VVTS-新山一国际机场': '胡志明'
}

# 状态文件路径
STATUS_FILE = os.path.join(project_root, 'data', 'leg_last_status.json')


def parse_time_vietnam(time_str):
    """
    解析时间字符串并转换为越南时间（实际时间-1小时）
    """
    if pd.isna(time_str) or time_str == '':
        return None

    try:
        hour, minute = map(int, str(time_str).split(':'))
        hour -= 1
        if hour < 0:
            hour += 24
        return f"{hour:02d}:{minute:02d}"
    except:
        return None


def get_airport_name(airport_full):
    """从完整机场名称获取简短名称"""
    if pd.isna(airport_full):
        return "未知"
    return AIRPORT_MAPPING.get(str(airport_full), str(airport_full).split('-')[-1] if '-' in str(airport_full) else str(airport_full))


def is_flight_completed(row):
    """判断航班是否已完成（所有4个阶段都有值）"""
    out = not pd.isna(row['OUT']) and row['OUT'] != ''
    off = not pd.isna(row['OFF']) and row['OFF'] != ''
    on = not pd.isna(row['ON']) and row['ON'] != ''
    inn = not pd.isna(row['IN']) and row['IN'] != ''
    return out and off and on and inn


def get_flight_status_key(row):
    """生成航班状态唯一标识"""
    return f"{row['执飞飞机']}_{row['航班号']}_{row['日期']}"


def get_flight_status_hash(row):
    """生成航班状态哈希值（用于比较状态是否变化）"""
    status = {
        'OUT': str(row['OUT']) if not pd.isna(row['OUT']) and row['OUT'] != '' else None,
        'OFF': str(row['OFF']) if not pd.isna(row['OFF']) and row['OFF'] != '' else None,
        'ON': str(row['ON']) if not pd.isna(row['ON']) and row['ON'] != '' else None,
        'IN': str(row['IN']) if not pd.isna(row['IN']) and row['IN'] != '' else None
    }
    return str(status)


def load_last_status():
    """加载上次保存的状态"""
    if os.path.exists(STATUS_FILE):
        try:
            import json
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"加载状态文件失败: {e}", "ERROR")
            return {}
    return {}


def save_current_status(status_dict):
    """保存当前状态"""
    try:
        import json
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_dict, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"保存状态文件失败: {e}", "ERROR")


def get_current_flight_status(df_aircraft, aircraft_num):
    """获取飞机当前正在执行的航班状态"""
    flight_sequence = AIRCRAFT_FLIGHTS.get(aircraft_num, [])

    current_flight = None
    current_row = None
    last_completed_flight = None
    last_completed_row = None

    for flight_num in flight_sequence:
        flight_rows = df_aircraft[df_aircraft['航班号'] == flight_num]
        if len(flight_rows) > 0:
            row = flight_rows.iloc[0]
            completed = is_flight_completed(row)

            if completed:
                last_completed_flight = flight_num
                last_completed_row = row
            else:
                current_flight = flight_num
                current_row = row
                break

    if current_row is not None:
        out_val = current_row['OUT'] if not pd.isna(current_row['OUT']) and current_row['OUT'] != '' else None
        off_val = current_row['OFF'] if not pd.isna(current_row['OFF']) and current_row['OFF'] != '' else None
        on_val = current_row['ON'] if not pd.isna(current_row['ON']) and current_row['ON'] != '' else None
        inn_val = current_row['IN'] if not pd.isna(current_row['IN']) and current_row['IN'] != '' else None

        if inn_val is not None:
            airport = get_airport_name(current_row['着陆机场'])
            current_idx = flight_sequence.index(current_flight)
            if current_idx < len(flight_sequence) - 1:
                next_flight = flight_sequence[current_idx + 1]
                return [f"{aircraft_num}在{airport}；计划执行{next_flight}。"]
            else:
                return [f"{aircraft_num}在{airport}；已完成今日航班。"]

        elif on_val is not None:
            vn_time = parse_time_vietnam(on_val)
            time_str = f"越南时间{vn_time}" if vn_time else "越南时间未知"
            airport = get_airport_name(current_row['着陆机场'])
            return [f"{aircraft_num}执行{current_flight}航班，已于{time_str}在{airport}着陆。"]

        elif off_val is not None:
            vn_time = parse_time_vietnam(off_val)
            time_str = f"越南时间{vn_time}" if vn_time else "越南时间未知"
            airport = get_airport_name(current_row['起飞机场'])
            return [f"{aircraft_num}执行{current_flight}航班，已于{time_str}从{airport}起飞。"]

        elif out_val is not None:
            vn_time = parse_time_vietnam(out_val)
            time_str = f"越南时间{vn_time}" if vn_time else "越南时间未知"
            airport = get_airport_name(current_row['起飞机场'])
            return [f"{aircraft_num}执行{current_flight}航班，已于{time_str}滑出。"]

        else:
            return [f"{aircraft_num}计划执行{current_flight}航班。"]

    elif last_completed_row is not None:
        airport = get_airport_name(last_completed_row['着陆机场'])
        last_idx = flight_sequence.index(last_completed_flight)
        if last_idx < len(flight_sequence) - 1:
            next_flight = flight_sequence[last_idx + 1]
            return [f"{aircraft_num}在{airport}；计划执行{next_flight}。"]
        else:
            return [f"{aircraft_num}在{airport}；已完成今日所有航班。"]

    return [f"{aircraft_num}暂无航班数据"]


def detect_status_changes(df_new):
    """
    检测航班状态变化

    Args:
        df_new: 新获取的航班数据

    Returns:
        (是否有变化, 通知消息列表)
    """
    last_status = load_last_status()
    current_status = {}
    notifications = []
    has_changes = False

    # 构建当前状态字典
    for _, row in df_new.iterrows():
        key = get_flight_status_key(row)
        hash_value = get_flight_status_hash(row)
        current_status[key] = hash_value

        # 检查是否有变化
        if key in last_status:
            if last_status[key] != hash_value:
                has_changes = True
                print(f"   检测到状态变化: {key}")
        else:
            # 新增的航班
            has_changes = True
            print(f"   检测到新航班: {key}")

    # 如果有变化，生成当前状态通知
    if has_changes:
        for aircraft_num in AIRCRAFT_FLIGHTS.keys():
            df_aircraft = df_new[df_new['执飞飞机'] == aircraft_num]
            if len(df_aircraft) > 0:
                status_messages = get_current_flight_status(df_aircraft, aircraft_num)
                notifications.extend(status_messages)

    # 保存当前状态
    save_current_status(current_status)

    return has_changes, notifications


def monitor_flight_status(target_date=None):
    """
    监控航班状态变化并发送通知

    Args:
        target_date: 目标日期（YYYY-MM-DD格式），默认为今天
    """
    log("航班状态监控脚本启动")

    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')

    print(f"📅 监控日期：{target_date}")

    # 读取 daily_raw 中最新抓取的数据
    daily_file = os.path.join(project_root, 'data', 'daily_raw', f'leg_data_{target_date}.csv')

    if not os.path.exists(daily_file):
        print(f"❌ 错误：找不到数据文件 {daily_file}")
        log(f"Data file not found: {daily_file}", "ERROR")
        return False

    try:
        df = pd.read_csv(daily_file)
        print(f"   ✅ 读取到 {len(df)} 行数据（最新抓取）")
    except Exception as e:
        print(f"❌ 读取数据文件失败：{e}")
        log(f"Failed to read data: {e}", "ERROR")
        return False

    # 生成当前状态通知（基于最新数据）
    print("\n📊 生成当前航班状态...")
    notifications = []

    for aircraft_num in AIRCRAFT_FLIGHTS.keys():
        df_aircraft = df[df['执飞飞机'] == aircraft_num]
        if len(df_aircraft) > 0:
            status_messages = get_current_flight_status(df_aircraft, aircraft_num)
            notifications.extend(status_messages)

    if not notifications:
        print("   ℹ️ 无航班状态数据")
        return True

    # 发送通知
    if notifications:
        notifier = FlightStatusNotifier()

        if notifier.is_enabled():
            subject = f"航班状态 - {target_date}"
            body = '\n'.join(notifications)

            if notifier.send_email(subject, body):
                print(f"   ✅ 已发送状态通知邮件（{len(notifications)}条）")
                log(f"Sent flight status notification: {len(notifications)} updates", "SUCCESS")
            else:
                print(f"   ⚠️ 邮件发送失败")
        else:
            print(f"   ⚠️ 邮件通知未启用")
            # 打印通知内容
            print("\n📧 通知内容：")
            for msg in notifications:
                print(f"   - {msg}")

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("航班状态监控脚本")
    print("=" * 60)

    # 支持命令行参数指定日期
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]

    success = monitor_flight_status(target_date)

    if success:
        print("\n✅ 监控完成！")
        sys.exit(0)
    else:
        print("\n⚠️ 监控失败")
        sys.exit(1)

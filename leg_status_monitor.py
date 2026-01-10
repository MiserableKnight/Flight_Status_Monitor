# -*- coding: utf-8 -*-
"""
航班状态监控脚本

⚠️ 时间策略说明：
- 项目内部统一使用北京时间
- 数据存储使用北京时间
- 邮件展示时转换为越南时间（北京时间-1小时）

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
from core.leg_status_notifier import LegStatusNotifier
from config.config_loader import load_config
from config.flight_schedule import FlightSchedule

# 初始化日志
log = get_logger()

# 加载统一配置
config_loader = load_config()
gmail_config = config_loader.get_gmail_config()

# 机场名称映射
AIRPORT_MAPPING = {
    'VVCS-昆仑国际机场': '昆岛',
    'VVNB-内排国际机场': '河内',
    'VVTS-新山一国际机场': '胡志明'
}


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


def get_flight_route(flight_number):
    """获取航班航线描述（中文）"""
    flight_info = FlightSchedule.get_flight_info(flight_number)
    if flight_info and 'route' in flight_info:
        route = flight_info['route']
        # 将机场代码转换为中文
        route_mapping = {
            'HAN': '河内',
            'VCS': '昆岛',
            'SGN': '胡志明'
        }
        parts = route.split('-')
        if len(parts) == 2:
            departure = route_mapping.get(parts[0], parts[0])
            arrival = route_mapping.get(parts[1], parts[1])
            return f"{departure}-{arrival}"
    return ""


def is_flight_completed(row):
    """判断航班是否已完成（所有4个阶段都有值）"""
    out = not pd.isna(row['OUT']) and row['OUT'] != ''
    off = not pd.isna(row['OFF']) and row['OFF'] != ''
    on = not pd.isna(row['ON']) and row['ON'] != ''
    inn = not pd.isna(row['IN']) and row['IN'] != ''
    return out and off and on and inn


def get_flight_sequence_sorted(df_aircraft):
    """
    从飞机数据中获取按计划时间排序的航班序列

    ⚠️ 重要修复: 使用航线链完整性检测
    - 根据实际执行的航班判断所属航线链
    - 返回完整的航线链序列,而不是仅返回已出现的航班
    - 只有完成航线链的最后一个航班(VJ106/VJ108回到河内),才算完成当日任务

    Args:
        df_aircraft: 该飞机的所有航班数据

    Returns:
        list: 完整的航线链航班号列表(按计划时间排序)
    """
    # 获取实际出现的航班号
    actual_flights = []
    for _, row in df_aircraft.iterrows():
        flight_num = row['航班号']
        if flight_num not in actual_flights:
            actual_flights.append(flight_num)

    if not actual_flights:
        return []

    # 根据第一个航班判断航线类型
    first_flight = actual_flights[0]
    route_chain = FlightSchedule.get_route_chain(first_flight)

    if route_chain:
        # 找到所属航线链,返回完整序列
        # 这样即使只执行了VJ118,也知道后面还有VJ119和VJ108
        return route_chain
    else:
        # 未知航线,使用实际航班按时间排序
        flight_list = []
        for _, row in df_aircraft.iterrows():
            flight_num = row['航班号']
            flight_info = FlightSchedule.get_flight_info(flight_num)

            if flight_info:
                scheduled_time = flight_info['scheduled_departure']
            else:
                scheduled_time = row['OUT'] if pd.notna(row['OUT']) else '00:00'

            flight_list.append({
                'flight_number': flight_num,
                'scheduled_time': scheduled_time
            })

        flight_list.sort(key=lambda x: x['scheduled_time'])
        return [f['flight_number'] for f in flight_list]


def get_current_flight_status(df_aircraft, aircraft_num):
    """
    获取飞机当前正在执行的航班状态

    ⚠️ 重要: 现在基于完整航线链判断状态
    - 只有完成航线链最后一个航班(VJ106/VJ108),才算完成当日所有航班
    - 中间航班完成后,会显示下一个计划航班
    """
    # 获取完整的航线链序列
    flight_sequence = get_flight_sequence_sorted(df_aircraft)

    if not flight_sequence:
        return [f"{aircraft_num}暂无航班数据"]

    current_flight = None
    current_row = None
    last_completed_flight = None
    last_completed_row = None

    # 遍历航线链,查找当前执行和已完成的航班
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
        else:
            # 航线链中的航班还未出现在数据中
            current_flight = flight_num
            current_row = None
            break

    # 情况1: 有正在执行的航班
    if current_row is not None:
        out_val = current_row['OUT'] if not pd.isna(current_row['OUT']) and current_row['OUT'] != '' else None
        off_val = current_row['OFF'] if not pd.isna(current_row['OFF']) and current_row['OFF'] != '' else None
        on_val = current_row['ON'] if not pd.isna(current_row['ON']) and current_row['ON'] != '' else None
        inn_val = current_row['IN'] if not pd.isna(current_row['IN']) and current_row['IN'] != '' else None

        if inn_val is not None:
            # 已落地
            airport = get_airport_name(current_row['着陆机场'])
            route = get_flight_route(current_flight)
            route_str = f"（{route}）" if route else ""
            current_idx = flight_sequence.index(current_flight)

            # 检查是否是航线链最后一个航班
            if current_idx == len(flight_sequence) - 1:
                # 最后一个航班落地,完成当日所有任务
                return [f"{aircraft_num}停靠{airport}；已完成今日所有航班。"]
            else:
                # 还有后续航班
                next_flight = flight_sequence[current_idx + 1]
                return [f"{aircraft_num}停靠{airport}；计划执行{next_flight}。"]

        elif on_val is not None:
            # 空中/落地但未滑入
            vn_time = parse_time_vietnam(on_val)
            time_str = f"越南时间{vn_time}" if vn_time else "越南时间未知"
            airport = get_airport_name(current_row['着陆机场'])
            route = get_flight_route(current_flight)
            route_str = f"（{route}）" if route else ""
            return [f"{aircraft_num}执行{current_flight}{route_str}，已于{time_str}在{airport}落地。"]

        elif off_val is not None:
            # 已起飞
            vn_time = parse_time_vietnam(off_val)
            time_str = f"越南时间{vn_time}" if vn_time else "越南时间未知"
            airport = get_airport_name(current_row['起飞机场'])
            route = get_flight_route(current_flight)
            route_str = f"（{route}）" if route else ""
            return [f"{aircraft_num}执行{current_flight}{route_str}，已于{time_str}从{airport}起飞。"]

        elif out_val is not None:
            # 已滑出
            vn_time = parse_time_vietnam(out_val)
            time_str = f"越南时间{vn_time}" if vn_time else "越南时间未知"
            airport = get_airport_name(current_row['起飞机场'])
            route = get_flight_route(current_flight)
            route_str = f"（{route}）" if route else ""
            return [f"{aircraft_num}执行{current_flight}{route_str}，已于{time_str}滑出。"]

        else:
            # 计划中
            route = get_flight_route(current_flight)
            route_str = f"（{route}）" if route else ""
            return [f"{aircraft_num}计划执行{current_flight}{route_str}。"]

    # 情况2: 上一航班已完成,查看下一个航班
    elif last_completed_row is not None:
        airport = get_airport_name(last_completed_row['着陆机场'])
        last_idx = flight_sequence.index(last_completed_flight)

        # 检查是否是航线链最后一个航班
        if last_idx == len(flight_sequence) - 1:
            # 最后一个航班已完成
            return [f"{aircraft_num}停靠{airport}；已完成今日所有航班。"]
        else:
            # 还有后续航班
            next_flight = flight_sequence[last_idx + 1]
            return [f"{aircraft_num}停靠{airport}；计划执行{next_flight}。"]

    # 情况3: 第一个航班还未开始
    elif current_flight is not None:
        route = get_flight_route(current_flight)
        route_str = f"（{route}）" if route else ""
        return [f"{aircraft_num}计划执行{current_flight}{route_str}。"]

    return [f"{aircraft_num}暂无航班数据"]


def monitor_flight_status(target_date=None):
    """
    监控航班状态变化并发送通知

    逻辑：
    1. 生成当前状态
    2. 对比上次保存的邮件状态
    3. 只有状态变化才发送邮件
    4. 发送成功后保存当前状态

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
    current_notifications = []

    # 动态获取所有飞机（从实际数据中）
    all_aircraft = df['执飞飞机'].unique()
    print(f"   ✅ 检测到 {len(all_aircraft)} 架飞机")

    # 为每架飞机生成状态消息
    for aircraft_num in all_aircraft:
        df_aircraft = df[df['执飞飞机'] == aircraft_num]
        if len(df_aircraft) > 0:
            status_messages = get_current_flight_status(df_aircraft, aircraft_num)
            current_notifications.extend(status_messages)

    if not current_notifications:
        print("   ℹ️ 无航班状态数据")
        return True

    # 生成当前状态的唯一标识（用于对比）
    import hashlib
    current_status_text = '\n'.join(current_notifications)
    current_status_hash = hashlib.md5(current_status_text.encode('utf-8')).hexdigest()

    # 加载上次发送的邮件状态
    last_email_status_file = os.path.join(project_root, 'data', 'last_email_status.json')
    last_status_hash = None

    if os.path.exists(last_email_status_file):
        try:
            with open(last_email_status_file, 'r', encoding='utf-8') as f:
                import json
                last_email_data = json.load(f)
                last_status_hash = last_email_data.get('status_hash')
                print(f"   📋 上次邮件状态哈希: {last_status_hash}")
        except Exception as e:
            print(f"   ⚠️ 读取上次邮件状态失败: {e}")

    # 对比状态
    print(f"   📊 当前状态哈希: {current_status_hash}")

    if current_status_hash == last_status_hash:
        print(f"\n   ℹ️ 状态无变化，跳过邮件发送")
        log("No status changes detected, skipping email notification", "INFO")
        return True

    print(f"\n   ✅ 检测到状态变化，发送邮件通知")

    # 发送通知（使用统一配置）
    if current_notifications:
        notifier = LegStatusNotifier(config_dict=gmail_config)

        if notifier.is_enabled():
            subject = f"航班状态 - {target_date}"
            body = '\n'.join(current_notifications)

            if notifier.send_email(subject, body):
                print(f"   ✅ 已发送状态通知邮件（{len(current_notifications)}条）")
                log(f"Sent flight status notification: {len(current_notifications)} updates", "SUCCESS")

                # 保存当前邮件状态
                try:
                    import json
                    os.makedirs(os.path.dirname(last_email_status_file), exist_ok=True)
                    with open(last_email_status_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            'status_hash': current_status_hash,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'notifications': current_notifications
                        }, f, ensure_ascii=False, indent=2)
                    print(f"   💾 已保存当前邮件状态")
                except Exception as e:
                    print(f"   ⚠️ 保存邮件状态失败: {e}")
            else:
                print(f"   ⚠️ 邮件发送失败")
        else:
            print(f"   ⚠️ 邮件通知未启用")
            # 打印通知内容
            print("\n📧 通知内容：")
            for msg in current_notifications:
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

# -*- coding: utf-8 -*-
"""
故障状态监控脚本

功能：
- 读取每日故障数据
- 读取航班起降时间数据
- 生成故障汇总信息（含时间背景）
- 发送故障邮件通知（每天一次）
"""
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
import hashlib
import re

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.logger import get_logger
from core.fault_status_notifier import FaultStatusNotifier
from core.fault_filter import FaultFilter
from config.config_loader import load_config
from config.flight_phase_mapping import get_phase_name, get_fault_type_name, get_phase_name_without_suffix
from config.flight_schedule import FlightSchedule

# 初始化日志
log = get_logger()

# 机场代码到城市名称的映射
AIRPORT_TO_CITY = {
    'VVNB': '河内',
    'VVTS': '胡志明',
    'VVCS': '昆岛'
}

# 加载统一配置
config_loader = load_config()
gmail_config = config_loader.get_gmail_config()


def parse_time_str(time_str):
    """
    解析时间字符串为 datetime.time 对象

    支持两种格式：
    - HH:MM:SS（完整时间）
    - HH:MM（只有小时和分钟，秒默认为0）

    Args:
        time_str: 时间字符串，格式如 "10:17:50" 或 "10:17" 或 "2026-01-13 10:17:50"

    Returns:
        datetime.time 对象，解析失败返回 None
    """
    if pd.isna(time_str) or not time_str:
        return None

    # 如果包含日期，只取时间部分
    if isinstance(time_str, str) and ' ' in time_str:
        time_str = time_str.split(' ')[-1]

    try:
        # 解析时间 HH:MM:SS 或 HH:MM
        parts = str(time_str).split(':')
        if len(parts) == 3:
            # HH:MM:SS 格式
            hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2])
            # 验证时间有效性
            if 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59:
                return datetime.strptime(time_str, '%H:%M:%S').time()
        elif len(parts) == 2:
            # HH:MM 格式，秒默认为0
            hour, minute = int(parts[0]), int(parts[1])
            # 验证时间有效性
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return datetime.strptime(f"{time_str}:00", '%H:%M:%S').time()
        return None
    except:
        return None


def calculate_time_context(fault_time_str, flight_times):
    """
    计算故障时间相对于航班关键时间点的时间差

    逻辑：
    1. 将故障时间与航班的 OUT/OFF/ON/IN 四个时间点排序
    2. 找到故障时间在时间轴上的位置：
       - 在 OFF 之后，ON 之前 → "起飞后X分钟"
       - 在 ON 之后，IN 之前 → "降落后X分钟"
       - 在 IN 之后 → "滑入后X分钟"
       - 在 OUT 之前 → "滑出前X分钟"

    Args:
        fault_time_str: 故障发生时间字符串
        flight_times: 航班关键时间点字典 {'OUT': time, 'OFF': time, 'ON': time, 'IN': time}

    Returns:
        str: 时间背景描述，如 "起飞后15分钟"
    """
    fault_time = parse_time_str(fault_time_str)
    if not fault_time:
        return None

    # 解析航班关键时间点
    times = {}
    for key, time_str in flight_times.items():
        t = parse_time_str(time_str)
        if t:
            times[key] = t

    if not times:
        return None

    # 定义时间点顺序
    time_events = [
        ('OUT', '滑出'),
        ('OFF', '起飞'),
        ('ON', '降落'),
        ('IN', '滑入')
    ]

    # 将故障时间转换为分钟数（从0:00开始）
    fault_minutes = fault_time.hour * 60 + fault_time.minute + fault_time.second / 60

    # 找到故障时间在时间轴上的位置
    # 按顺序检查每个时间点，找到故障时间所在的区间
    last_event_key = None
    last_event_time = None
    last_event_name = None

    for event_key, event_name in time_events:
        if event_key not in times:
            continue

        event_time = times[event_key]
        event_minutes = event_time.hour * 60 + event_time.minute + event_time.second / 60

        # 如果故障时间在这个时间点之后，更新为最后一个时间点
        if fault_minutes >= event_minutes:
            last_event_key = event_key
            last_event_time = event_time
            last_event_name = event_name
        else:
            # 故障时间在这个时间点之前，停止查找
            break

    if last_event_name and last_event_time:
        # 计算时间差
        last_minutes = last_event_time.hour * 60 + last_event_time.minute + last_event_time.second / 60
        diff_minutes = fault_minutes - last_minutes

        # 计算分钟数（四舍五入）
        minutes = int(round(diff_minutes))

        if minutes == 0:
            return f"{last_event_name}时"
        elif minutes < 60:
            return f"{last_event_name}后{minutes}分钟"
        else:
            hours = minutes // 60
            remain_minutes = minutes % 60
            if remain_minutes == 0:
                return f"{last_event_name}后{hours}小时"
            else:
                return f"{last_event_name}后{hours}小时{remain_minutes}分钟"
    elif 'OUT' in times:
        # 如果故障时间在所有时间点之前，相对于滑出时间
        out_time = times['OUT']
        out_minutes = out_time.hour * 60 + out_time.minute + out_time.second / 60
        diff_minutes = out_minutes - fault_minutes

        minutes = int(round(diff_minutes))
        if minutes == 0:
            return "滑出时"
        elif minutes < 60:
            return f"滑出前{minutes}分钟"
        else:
            hours = minutes // 60
            remain_minutes = minutes % 60
            if remain_minutes == 0:
                return f"滑出前{hours}小时"
            else:
                return f"滑出前{hours}小时{remain_minutes}分钟"

    return None


def clean_description(description: str) -> str:
    """
    清理故障描述，移除方括号及其内容

    移除的模式包括：
    - [数字开头的内容] 如 [761 111 00]
    - [CAUTION]、[WARNING] 等状态标识

    Args:
        description: 原始故障描述

    Returns:
        str: 清理后的故障描述

    Examples:
        >>> clean_description('[761 111 00]ENG NO TAKEOFF DATA[CAUTION]')
        'ENG NO TAKEOFF DATA'
        >>> clean_description('ADC1:INTERNAL FAULT')
        'ADC1:INTERNAL FAULT'
    """
    if not description:
        return ''

    # 移除所有方括号及其内容
    # 模式：\[.*?\] 匹配 [...]
    cleaned = re.sub(r'\[.*?\]', '', description)

    # 移除多余的空格
    cleaned = ' '.join(cleaned.split())

    return cleaned.strip()


def extract_city_name(airport_str):
    """
    从机场字符串中提取城市名称

    Args:
        airport_str: 机场字符串，格式如 "VVTS-新山一国际机场" 或 "VVTS"

    Returns:
        str: 城市名称，如 "胡志明"
    """
    if not airport_str:
        return None

    # 如果包含"-"，提取机场代码部分
    if '-' in airport_str:
        airport_code = airport_str.split('-')[0].strip()
    else:
        airport_code = airport_str.strip()

    # 映射到城市名称
    return AIRPORT_TO_CITY.get(airport_code)


def get_route_pair(flight_num, departure_airport_str, arrival_airport_str):
    """
    获取城市对字符串

    优先从实际机场数据中提取，如果失败则从配置文件中获取

    Args:
        flight_num: 航班号
        departure_airport_str: 起飞机场字符串
        arrival_airport_str: 着陆机场字符串

    Returns:
        str: 城市对字符串，如 "河内-昆岛"，如果获取失败返回 None
    """
    # 尝试从实际机场数据中提取
    dep_city = extract_city_name(departure_airport_str)
    arr_city = extract_city_name(arrival_airport_str)

    if dep_city and arr_city:
        return f"{dep_city}-{arr_city}"

    # 如果实际数据无法获取，尝试从配置文件获取
    flight_info = FlightSchedule.get_flight_info(flight_num)
    if flight_info and 'route' in flight_info:
        route = flight_info['route']
        # route 格式如 "HAN-VCS"，需要转换为中文城市名
        parts = route.split('-')
        if len(parts) == 2:
            # 机场代码到城市名的映射
            city_map = {
                'HAN': '河内',
                'SGN': '胡志明',
                'VCS': '昆岛'
            }
            dep = city_map.get(parts[0])
            arr = city_map.get(parts[1])
            if dep and arr:
                return f"{dep}-{arr}"

    return None


def load_flight_times(target_date):
    """
    加载航班起降时间数据和机场信息

    Args:
        target_date: 目标日期字符串

    Returns:
        dict: {(机号, 航班号): {'OUT': time, 'OFF': time, 'ON': time, 'IN': time,
                                'departure_airport': str, 'arrival_airport': str}}
    """
    leg_file = os.path.join(project_root, 'data', 'daily_raw', f'leg_data_{target_date}.csv')

    if not os.path.exists(leg_file):
        log(f"航班数据文件不存在: {leg_file}", "WARNING")
        return {}

    try:
        # 读取CSV文件
        try:
            df = pd.read_csv(leg_file, encoding='utf-8-sig')
        except:
            df = pd.read_csv(leg_file, encoding='gbk')

        flight_times = {}

        for _, row in df.iterrows():
            key = (row['执飞飞机'], row['航班号'])
            flight_times[key] = {
                'OUT': row.get('OUT', ''),
                'OFF': row.get('OFF', ''),
                'ON': row.get('ON', ''),
                'IN': row.get('IN', ''),
                'departure_airport': row.get('起飞机场', ''),
                'arrival_airport': row.get('着陆机场', '')
            }

        log(f"成功加载 {len(flight_times)} 条航班时间数据")
        return flight_times

    except Exception as e:
        log(f"读取航班数据失败: {e}", "ERROR")
        return {}


def generate_fault_summary(df, target_date, flight_times_dict=None):
    """
    生成故障汇总信息

    Args:
        df: 故障数据DataFrame
        target_date: 目标日期
        flight_times_dict: 航班时间数据字典 {(机号, 航班号): {'OUT': ..., 'OFF': ..., 'ON': ..., 'IN': ...}}

    Returns:
        str: 故障汇总文本
    """
    if df.empty:
        return "今日无故障记录\n"

    # 如果没有提供航班时间数据，尝试加载
    if flight_times_dict is None:
        flight_times_dict = load_flight_times(target_date)

    # 按飞机分组
    aircraft_groups = df.groupby('机号')

    summary_lines = []

    for aircraft_num, group in aircraft_groups:
        summary_lines.append(f"{aircraft_num}:")

        # 按航班号分组，并收集每个航班的最新故障时间
        flight_groups = group.groupby('航班号')

        # 收集每个航班的故障数据和最新故障时间
        flights_data = []
        for flight_num, flight_group in flight_groups:
            # 转换为列表并按触发时间排序（倒序）
            faults = flight_group.to_dict('records')
            faults.sort(key=lambda x: x['触发时间'], reverse=True)

            # 获取该航班的最新故障时间（第一个故障的时间）
            latest_fault_time = faults[0]['触发时间'] if faults else ''

            # 获取该航班的时间数据
            flight_key = (aircraft_num, flight_num)
            flight_data = flight_times_dict.get(flight_key, {})

            flights_data.append({
                'flight_num': flight_num,
                'faults': faults,
                'flight_data': flight_data,
                'latest_fault_time': latest_fault_time
            })

        # 按照最新故障时间倒序排列航班（最新故障的航班在最上面）
        flights_data.sort(key=lambda x: x['latest_fault_time'], reverse=True)

        # 处理排序后的航班
        for flight_info in flights_data:
            flight_num = flight_info['flight_num']
            faults = flight_info['faults']
            flight_data = flight_info['flight_data']

            # 获取城市对信息
            route_pair = None
            if flight_data:
                route_pair = get_route_pair(
                    flight_num,
                    flight_data.get('departure_airport', ''),
                    flight_data.get('arrival_airport', '')
                )

            # 构建航班行，包含城市对
            if route_pair:
                flight_line = f"  {flight_num}（{route_pair}）:"
            else:
                flight_line = f"  {flight_num}:"

            fault_lines = []

            # 提取时间数据（用于计算时间背景）
            flight_times = {
                'OUT': flight_data.get('OUT', ''),
                'OFF': flight_data.get('OFF', ''),
                'ON': flight_data.get('ON', ''),
                'IN': flight_data.get('IN', '')
            }

            for fault in faults:
                trigger_time = fault['触发_time'] if '触发_time' in fault else fault.get('触发时间', '')

                # 只保留时间部分（去除日期）
                if ' ' in trigger_time:
                    # 格式如 "2026-01-13 10:17:50"，只取时间部分
                    time_part = trigger_time.split(' ')[-1]
                else:
                    time_part = trigger_time

                # 格式化故障描述
                description = fault.get('描述', '')
                fault_type = fault.get('故障类型', '')
                phase = fault.get('飞行阶段', '')

                # 清理描述：移除方括号内容
                cleaned_desc = clean_description(description)

                # 将故障类型和飞行阶段缩写转换为中文
                fault_type_cn = get_fault_type_name(fault_type) if fault_type else ''
                # 使用不带"阶段"后缀的飞行阶段名称
                phase_cn = get_phase_name_without_suffix(phase) if phase else ''

                # 计算时间背景
                time_context = None
                if flight_times:
                    time_context = calculate_time_context(trigger_time, flight_times)

                # 构建故障行 - 新格式：滑入阶段（降落后1分钟），有CAS：ENG NO TAKEOFF DATA
                fault_line_parts = []

                # 添加飞行阶段和时间背景
                if phase_cn:
                    if time_context:
                        fault_line_parts.append(f"{phase_cn}（{time_context}）")
                    else:
                        fault_line_parts.append(f"{phase_cn}阶段")
                elif time_context:
                    fault_line_parts.append(f"（{time_context}）")

                # 添加故障类型和描述
                if fault_type_cn:
                    fault_line_parts.append(f"有{fault_type_cn}：{cleaned_desc}")
                else:
                    fault_line_parts.append(cleaned_desc)

                # 组合最终行
                if fault_line_parts:
                    fault_lines.append(f"    - {'，'.join(fault_line_parts)}")
                else:
                    fault_lines.append(f"    - {cleaned_desc}")

            if fault_lines:
                summary_lines.append(flight_line)
                summary_lines.extend(fault_lines[:10])  # 最多显示10条
                if len(fault_lines) > 10:
                    summary_lines.append(f"    ... (还有{len(fault_lines)-10}条)")

        summary_lines.append("")

    return '\n'.join(summary_lines)


def monitor_fault_status(target_date=None):
    """
    监控故障状态并发送通知

    逻辑：
    1. 读取当日故障数据
    2. 读取航班起降时间数据
    3. 生成故障汇总（含时间背景）
    4. 对比上次邮件状态哈希
    5. 只有数据变化才发送邮件
    6. 发送成功后保存当前状态

    Args:
        target_date: 目标日期（YYYY-MM-DD格式），默认为今天
    """
    log("故障状态监控脚本启动")

    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')

    print(f"📅 监控日期：{target_date}")

    # 读取 daily_raw 中最新抓取的数据
    daily_file = os.path.join(project_root, 'data', 'daily_raw', f'fault_data_{target_date}.csv')

    if not os.path.exists(daily_file):
        print(f"❌ 错误：找不到数据文件 {daily_file}")
        log(f"Data file not found: {daily_file}", "ERROR")
        return False

    try:
        # 读取CSV文件，处理可能的编码问题
        try:
            df = pd.read_csv(daily_file, encoding='utf-8-sig')
        except:
            df = pd.read_csv(daily_file, encoding='gbk')

        # 重命名可能的列名变体（处理编码问题）
        if '触发_time' in df.columns and '触发时间' not in df.columns:
            df.rename(columns={'触发_time': '触发时间'}, inplace=True)

        print(f"   ✅ 读取到 {len(df)} 行数据")

        # 应用故障过滤规则
        print("\n🔍 应用故障过滤规则...")
        try:
            filter_obj = FaultFilter()
            filter_stats = filter_obj.get_filter_stats()
            print(f"   📋 过滤规则: 组合规则 {filter_stats['single_filter_rules']} 条, 关联规则 {filter_stats['group_filter_rules']} 条")

            df = filter_obj.apply_filters(df)
            print(f"   ✅ 过滤后剩余 {len(df)} 行数据")
        except Exception as e:
            print(f"   ⚠️ 过滤失败，继续使用原始数据: {e}")
            log(f"Filter application failed: {e}", "WARNING")
    except Exception as e:
        print(f"❌ 读取数据文件失败：{e}")
        log(f"Failed to read data: {e}", "ERROR")
        return False

    # 加载航班时间数据
    print("\n✈️ 加载航班时间数据...")
    flight_times = load_flight_times(target_date)
    if flight_times:
        print(f"   ✅ 成功加载 {len(flight_times)} 条航班时间记录")
    else:
        print(f"   ⚠️ 未找到航班时间数据，邮件将不包含时间背景信息")

    # 生成故障汇总
    print("\n📊 生成故障汇总...")
    fault_summary = generate_fault_summary(df, target_date, flight_times)

    # 生成当前数据的唯一标识（用于对比）
    current_hash = hashlib.md5(
        f"{target_date}_{len(df)}".encode('utf-8')
    ).hexdigest()

    # 加载上次发送的邮件状态
    last_email_status_file = os.path.join(project_root, 'data', 'last_fault_email_status.json')
    last_hash = None

    if os.path.exists(last_email_status_file):
        try:
            import json
            with open(last_email_status_file, 'r', encoding='utf-8') as f:
                last_email_data = json.load(f)
                last_hash = last_email_data.get('data_hash')
                print(f"   📋 上次邮件数据哈希: {last_hash}")
        except Exception as e:
            print(f"   ⚠️ 读取上次邮件状态失败: {e}")

    # 对比状态
    print(f"   📊 当前数据哈希: {current_hash}")

    if current_hash == last_hash:
        print(f"\n   ℹ️ 数据无变化，跳过邮件发送")
        log("No data changes detected, skipping email notification", "INFO")
        return True

    print(f"\n   ✅ 检测到数据变化，发送邮件通知")

    # 发送通知（使用统一配置）
    notifier = FaultStatusNotifier(config_dict=gmail_config)

    if notifier.is_enabled():
        # 不发送附件，只发送邮件内容
        attachment = None

        if notifier.send_fault_status_notification(fault_summary, target_date, attachment):
            print(f"   ✅ 已发送故障汇总邮件")
            log(f"Sent fault status notification for {target_date}", "SUCCESS")

            # 保存当前邮件状态
            try:
                import json
                os.makedirs(os.path.dirname(last_email_status_file), exist_ok=True)
                with open(last_email_status_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'data_hash': current_hash,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'fault_count': len(df),
                        'date': target_date
                    }, f, ensure_ascii=False, indent=2)
                print(f"   💾 已保存当前邮件状态")
            except Exception as e:
                print(f"   ⚠️ 保存邮件状态失败: {e}")
        else:
            print(f"   ⚠️ 邮件发送失败")
            return False
    else:
        print(f"   ⚠️ 邮件通知未启用")
        # 打印通知内容
        print("\n📧 通知内容：")
        print(fault_summary)

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("故障状态监控脚本")
    print("=" * 60)

    # 支持命令行参数指定日期
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]

    success = monitor_fault_status(target_date)

    if success:
        print("\n✅ 监控完成！")
        sys.exit(0)
    else:
        print("\n⚠️ 监控失败")
        sys.exit(1)

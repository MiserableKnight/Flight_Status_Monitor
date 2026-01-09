# -*- coding: utf-8 -*-
"""
Leg Data Update Script
更新航段数据到主CSV文件
功能：
1. 将每日获取的leg data添加到总表
2. 统一航班号格式（前两位改为VJ）
3. 计算空中时间（ON-OFF）和空地时间（IN-OUT）
4. 更新完成后触发状态监控
"""
import pandas as pd
from datetime import datetime
import os
import sys
import subprocess

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from core.logger import get_logger

# 初始化日志
log = get_logger()


def calculate_time_diff(off_time, on_time):
    """计算时间差（分钟）"""
    if pd.isna(off_time) or pd.isna(on_time) or off_time == '' or on_time == '':
        return None

    try:
        off_hour, off_min = map(int, str(off_time).split(':'))
        on_hour, on_min = map(int, str(on_time).split(':'))
        off_minutes = off_hour * 60 + off_min
        on_minutes = on_hour * 60 + on_min

        if on_minutes < off_minutes:
            on_minutes += 24 * 60

        return on_minutes - off_minutes
    except Exception as e:
        log(f"计算时间差失败: {e}", "ERROR")
        return None


def normalize_flight_number(flight_num):
    """统一航班号格式，将前两位字母改为VJ"""
    if pd.isna(flight_num) or flight_num == '':
        return flight_num

    flight_num = str(flight_num).strip().upper()
    match = str(flight_num).replace('EU', '').replace('VJ', '')

    if match.isdigit():
        return f'VJ{match}'

    return flight_num


def update_leg_data(target_date=None):
    """
    更新航段数据到主表

    :param target_date: 可选，指定要更新的目标日期（YYYY-MM-DD格式）
    """
    log("航段数据更新脚本启动")

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

    # 🔍 检测状态变化（在更新之前）
    print(f"\n🔍 检测状态变化...")
    try:
        # 导入状态监控模块
        sys.path.insert(0, project_root)
        from leg_status_monitor import load_last_status, get_flight_status_key, get_flight_status_hash

        last_status = load_last_status()
        has_changes = False
        changes_detected = []

        for _, row in df_daily.iterrows():
            key = get_flight_status_key(row)
            hash_value = get_flight_status_hash(row)

            if key in last_status:
                if last_status[key] != hash_value:
                    has_changes = True
                    changes_detected.append(key)
                    print(f"   ✅ 状态变化: {key}")
            else:
                # 新航班
                has_changes = True
                changes_detected.append(key)
                print(f"   🆕 新航班: {key}")

        if not has_changes:
            print(f"\n   ℹ️ 状态无变化，跳过更新主表")
            log(f"No status changes detected, skipping update", "INFO")
            return True  # 返回True表示任务完成（虽然没有更新）

        print(f"\n   ✅ 检测到 {len(changes_detected)} 个状态变化，将继续更新主表")

    except Exception as e:
        print(f"   ⚠️ 状态检测失败，将继续更新：{e}")
        log(f"Status detection failed: {e}", "WARNING")
        has_changes = True  # 如果检测失败，默认继续更新

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

    # 删除主文件中当天的所有数据
    if len(df_main) > 0 and '日期' in df_main.columns:
        original_count = len(df_main)
        target_dt = datetime.strptime(target_date_str, '%Y-%m-%d')

        def normalize_and_parse(date_str):
            if pd.isna(date_str):
                return None
            date_str = str(date_str).strip().replace('/', '-')
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except:
                return None

        df_main_temp = df_main.copy()
        df_main_temp['日期_解析'] = df_main_temp['日期'].apply(normalize_and_parse)
        df_main = df_main[df_main_temp['日期_解析'] != target_dt.date()]

        removed_count = original_count - len(df_main)
        if removed_count > 0:
            print(f"   🗑️ 删除了 {removed_count} 行当天旧数据")

    # 标准化航班号并添加计算字段
    print(f"🔄 处理数据...")
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

    # 确保所有必需的列都存在
    required_columns = [
        '日期', '执飞飞机', '航班号', '起飞机场', '着陆机场', 'MSN',
        'OUT', 'OFF', 'ON', 'IN', '运行情况',
        'OUT油量(kg)', 'OFF油量(kg)', 'ON油量(kg)', 'IN油量(kg)',
        '空中时间(分钟)', '空地时间(分钟)'
    ]

    for col in required_columns:
        if col not in df_new.columns:
            df_new[col] = None

    df_new = df_new[required_columns]

    # 合并数据
    if len(df_main) > 0:
        for col in df_new.columns:
            if col not in df_main.columns:
                df_main[col] = None
        df_main = df_main[df_new.columns]
        df_updated = pd.concat([df_main, df_new], ignore_index=True)
    else:
        df_updated = df_new.copy()

    # 保存更新后的主文件
    try:
        temp_file = main_file + '.tmp'
        df_updated.to_csv(temp_file, index=False, encoding='utf-8-sig')

        if os.path.exists(main_file):
            os.remove(main_file)

        os.rename(temp_file, main_file)

        print(f"\n✅ 已更新主数据文件：{main_file}")
        print(f"📊 总行数：{len(df_updated)}")
        log(f"Updated main file: {main_file}, added {len(df_new)} rows", "SUCCESS")
    except Exception as e:
        print(f"❌ 保存主数据文件失败：{e}")
        log(f"Failed to save main data: {e}", "ERROR")
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        return False

    # 触发状态监控
    print(f"\n📧 触发状态监控...")
    try:
        monitor_script = os.path.join(project_root, 'leg_status_monitor.py')
        result = subprocess.run(
            [sys.executable, monitor_script, target_date_str],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.stdout:
            print(result.stdout)
        if result.returncode != 0 and result.stderr:
            print(f"   ⚠️ 状态监控警告: {result.stderr}")
    except Exception as e:
        print(f"   ⚠️ 状态监控执行失败: {e}")

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("航段数据更新脚本")
    print("=" * 60)

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

"""
Flight Data Update Script
更新航班数据到主CSV文件，自动计算累计值
"""
import pandas as pd
from datetime import datetime, timedelta
import os
import glob
import shutil
from logger import get_logger

# Initialize logger
log = get_logger()


def get_backup_dir():
    """获取或创建备份目录"""
    backup_dir = os.path.join(os.path.dirname(__file__), 'data', 'backup')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        print(f"   📁 创建备份目录: {backup_dir}")
    return backup_dir


def clean_old_backups(backup_dir, max_backups=3):
    """清理旧备份，只保留最新的max_backups个"""
    pattern = os.path.join(backup_dir, 'flight_data_backup_*.csv')
    backups = sorted(glob.glob(pattern), key=os.path.getmtime)

    while len(backups) > max_backups:
        oldest = backups.pop(0)
        try:
            os.remove(oldest)
            print(f"   🗑️ 删除旧备份: {os.path.basename(oldest)}")
        except Exception as e:
            print(f"   ⚠️ 删除失败 {oldest}: {e}")


def create_backup(main_file):
    """创建带时间戳的备份"""
    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'flight_data_backup_{timestamp}.csv'
    backup_path = os.path.join(backup_dir, backup_filename)

    try:
        shutil.copy2(main_file, backup_path)
        print(f"   ✅ 创建备份: {backup_filename}")

        # 清理旧备份，只保留3个
        clean_old_backups(backup_dir, max_backups=3)

        return True
    except Exception as e:
        print(f"   ❌ 备份失败: {e}")
        return False


def load_daily_data(date_str):
    """
    加载指定日期的每日数据文件
    :param date_str: 日期字符串，格式：YYYY-MM-DD
    :return: DataFrame with daily data or None
    """
    filename = f"data/flight_data_{date_str}.csv"
    if not os.path.exists(filename):
        return None

    df = pd.read_csv(filename)
    # 确保只有一行数据
    if len(df) == 0:
        return None

    return df.iloc[0]


def calculate_days_since_start(current_date):
    """
    计算从2025-04-19到当前日期的天数
    :param current_date: 当前日期 datetime对象
    :return: 天数
    """
    start_date = datetime(2025, 4, 19)
    return (current_date - start_date).days + 1


def update_flight_data(target_date=None):
    """
    主更新函数：检测缺失日期并填充数据

    :param target_date: 可选，指定要更新的目标日期（YYYY-MM-DD格式）
                       如果为None，则更新到今天
    """
    log("Update script started")

    # 读取主数据文件
    main_file = "data/flight_data.csv"
    if not os.path.exists(main_file):
        print(f"❌ 错误：主数据文件 {main_file} 不存在！")
        log(f"Main data file not found: {main_file}", "ERROR")
        return False

    df_main = pd.read_csv(main_file)

    # 获取最后一行的日期
    last_date_str = str(df_main.iloc[-1]['date'])
    last_date = datetime.strptime(last_date_str, "%Y/%m/%d")

    print(f"📅 主数据文件最后一行日期：{last_date.strftime('%Y-%m-%d')}")
    log(f"Last date in CSV: {last_date.strftime('%Y-%m-%d')}")

    # 确定目标日期
    if target_date:
        target = datetime.strptime(target_date, '%Y-%m-%d')
    else:
        target = datetime.now().date()

    # 如果目标日期已经存在，不需要更新
    if last_date.date() >= target:
        print(f"✅ 数据已是最新（最后日期：{last_date.strftime('%Y-%m-%d')}，目标：{target.strftime('%Y-%m-%d')}）")
        return True

    # 计算需要填充的日期范围
    date_to_fill = last_date + timedelta(days=1)
    dates_needed = []

    current = date_to_fill
    while current.date() <= target:
        dates_needed.append(current)
        current = current + timedelta(days=1)

    if not dates_needed:
        print("ℹ️ 没有需要填充的日期")
        return True

    print(f"\n📋 需要填充的日期：{len(dates_needed)} 天")
    for d in dates_needed:
        print(f"   - {d.strftime('%Y-%m-%d')}")

    # 获取最后一行的累计值
    last_cumulative = {
        'air_time': df_main.iloc[-1]['cumulative_air_time'],
        'block_time': df_main.iloc[-1]['cumulative_block_time'],
        'fc': df_main.iloc[-1]['cumulative_fc'],
        'flight_leg': df_main.iloc[-1]['cumulative_flight_leg']
    }

    # 逐日添加数据
    new_rows = []
    missing_dates = []

    for date in dates_needed:
        date_str = date.strftime('%Y-%m-%d')
        print(f"\n🔄 处理日期：{date_str}")

        # 加载当天的数据
        daily_data = load_daily_data(date_str)

        if daily_data is None:
            print(f"   ⚠️ 找不到 {date_str} 的数据文件，标记为缺失")
            missing_dates.append(date_str)
            continue

        # 提取每日数据
        air_time = daily_data['air_time']
        block_time = daily_data['block_time']
        fc = daily_data['fc']
        flight_leg = daily_data['flight_leg']
        daily_util_air_time = daily_data['daily_utilization_air_time']
        daily_util_block_time = daily_data['daily_utilization_block time']

        # 计算累计值
        cumulative_air_time = last_cumulative['air_time'] + air_time
        cumulative_block_time = last_cumulative['block_time'] + block_time
        cumulative_fc = last_cumulative['fc'] + fc
        cumulative_flight_leg = last_cumulative['flight_leg'] + flight_leg

        # 计算天数（从2025-04-19到当前日期的天数 - 46）
        days_since_start = calculate_days_since_start(date) - 46

        # 计算累计日利用率
        if days_since_start > 0:
            cumulative_daily_util_air_time = (cumulative_air_time / days_since_start) / 2
            cumulative_daily_util_block_time = (cumulative_block_time / days_since_start) / 2
        else:
            cumulative_daily_util_air_time = daily_util_air_time
            cumulative_daily_util_block_time = daily_util_block_time

        # 构建新行
        new_row = {
            'date': date.strftime('%Y/%m/%d'),
            'air_time': air_time,
            'block_time': block_time,
            'fc': fc,
            'flight_leg': flight_leg,
            'daily_utilization_air_time': daily_util_air_time,
            'daily_utilization_block time': daily_util_block_time,
            'cumulative_air_time': cumulative_air_time,
            'cumulative_block_time': cumulative_block_time,
            'cumulative_fc': cumulative_fc,
            'cumulative_flight_leg': cumulative_flight_leg,
            'cumulative_daily_utilization_air_time': cumulative_daily_util_air_time,
            'cumulative_daily_utilization_block_time': cumulative_daily_util_block_time
        }

        new_rows.append(new_row)

        # 更新最后的累计值，供下一天使用
        last_cumulative = {
            'air_time': cumulative_air_time,
            'block_time': cumulative_block_time,
            'fc': cumulative_fc,
            'flight_leg': cumulative_flight_leg
        }

        print(f"   ✅ 空中时间：{air_time:.2f}，累计：{cumulative_air_time:.2f}")
        print(f"   ✅ 档轮时间：{block_time:.2f}，累计：{cumulative_block_time:.2f}")
        print(f"   ✅ 航班数：{fc}，累计：{cumulative_fc:.0f}")
        print(f"   ✅ 航段数：{flight_leg}，累计：{cumulative_flight_leg:.0f}")

    # 如果没有新数据，退出
    if not new_rows:
        print("\nℹ️ 没有添加新数据")
        if missing_dates:
            print(f"⚠️ 缺失的日期：{', '.join(missing_dates)}")
        return False

    # 创建备份
    print("\n💾 创建数据备份...")
    if not create_backup(main_file):
        print("⚠️ 警告：备份失败，但继续更新数据")

    # 将新行转换为DataFrame并追加到主数据
    df_new = pd.DataFrame(new_rows)
    df_updated = pd.concat([df_main, df_new], ignore_index=True)

    # 格式化小数位数：保留两位小数
    df_updated['cumulative_daily_utilization_air_time'] = df_updated['cumulative_daily_utilization_air_time'].round(2)
    df_updated['cumulative_daily_utilization_block_time'] = df_updated['cumulative_daily_utilization_block_time'].round(2)

    # 保存更新后的数据
    df_updated.to_csv(main_file, index=False)
    print(f"\n✅ 已更新主数据文件：{main_file}")
    print(f"📊 添加了 {len(new_rows)} 行新数据")
    print(f"📅 数据范围：{df_updated.iloc[0]['date']} 至 {df_updated.iloc[-1]['date']}")
    log(f"Updated main file: added {len(new_rows)} rows", "SUCCESS")

    # 报告缺失的日期
    if missing_dates:
        print(f"\n⚠️ 以下日期的数据文件缺失，无法更新：")
        for d in missing_dates:
            print(f"   - {d}")
        log(f"Missing dates: {', '.join(missing_dates)}", "WARNING")
        return False

    return True


def get_first_missing_date():
    """
    获取第一个缺失日期（静默模式，用于批处理调用）
    :return: 第一个缺失日期字符串，如果没有缺失返回空字符串
    """
    main_file = "data/flight_data.csv"
    if not os.path.exists(main_file):
        return None

    df_main = pd.read_csv(main_file)
    last_date_str = str(df_main.iloc[-1]['date'])
    last_date = datetime.strptime(last_date_str, "%Y/%m/%d")
    today = datetime.now().date()

    if last_date.date() >= today:
        return None

    # 返回第一个缺失日期
    return (last_date + timedelta(days=1)).strftime('%Y-%m-%d')


if __name__ == "__main__":
    import sys

    # 检查是否是静默模式（用于批处理获取缺失日期）
    if len(sys.argv) > 1 and sys.argv[1] == "--get-missing":
        missing_date = get_first_missing_date()
        if missing_date:
            print(missing_date)
        sys.exit(0)

    print("=" * 60)
    print("航班数据更新脚本")
    print("=" * 60)

    # 支持命令行参数指定日期
    target_date = None
    if len(sys.argv) > 1 and sys.argv[1] != "--get-missing":
        target_date = sys.argv[1]
        print(f"🎯 目标日期：{target_date}")

    success = update_flight_data(target_date)

    if success:
        print("\n✅ 更新完成！")
        sys.exit(0)
    else:
        print("\n⚠️ 更新未完全成功（有缺失数据）")
        sys.exit(1)

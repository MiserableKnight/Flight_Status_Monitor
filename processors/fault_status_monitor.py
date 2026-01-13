# -*- coding: utf-8 -*-
"""
故障状态监控脚本

功能：
- 读取每日故障数据
- 生成故障汇总信息
- 发送故障邮件通知（每天一次）
"""
import pandas as pd
from datetime import datetime
import os
import sys
import hashlib

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.logger import get_logger
from core.fault_status_notifier import FaultStatusNotifier
from config.config_loader import load_config

# 初始化日志
log = get_logger()

# 加载统一配置
config_loader = load_config()
gmail_config = config_loader.get_gmail_config()


def generate_fault_summary(df, target_date):
    """
    生成故障汇总信息

    Args:
        df: 故障数据DataFrame
        target_date: 目标日期

    Returns:
        str: 故障汇总文本
    """
    if df.empty:
        return f"故障信息汇总 - {target_date}\n{'='*40}\n\n今日无故障记录\n"

    # 按飞机分组
    aircraft_groups = df.groupby('机号')

    summary_lines = [
        f"故障信息汇总 - {target_date}",
        "="*40,
        ""
    ]

    total_faults = 0

    for aircraft_num, group in aircraft_groups:
        summary_lines.append(f"{aircraft_num}:")

        # 按航班号分组
        flight_groups = group.groupby('航班号')

        for flight_num, flight_group in flight_groups:
            # 转换为列表并按触发时间排序
            faults = flight_group.to_dict('records')
            faults.sort(key=lambda x: x['触发时间'], reverse=True)

            flight_line = f"  {flight_num}:"
            fault_lines = []

            for fault in faults:
                total_faults += 1
                trigger_time = fault['触发_time'] if '触发_time' in fault else fault.get('触发时间', '')

                # 格式化故障描述
                description = fault.get('描述', '')
                fault_type = fault.get('故障类型', '')
                phase = fault.get('飞行阶段', '')

                # 简化显示：只显示时间和描述
                if phase:
                    fault_lines.append(f"    - {description} ({trigger_time}, {phase})")
                else:
                    fault_lines.append(f"    - {description} ({trigger_time})")

            if fault_lines:
                summary_lines.append(flight_line)
                summary_lines.extend(fault_lines[:10])  # 最多显示10条
                if len(fault_lines) > 10:
                    summary_lines.append(f"    ... (还有{len(fault_lines)-10}条)")

        summary_lines.append("")

    summary_lines.extend([
        "-"*40,
        f"共计: {total_faults}条故障记录"
    ])

    return '\n'.join(summary_lines)


def monitor_fault_status(target_date=None):
    """
    监控故障状态并发送通知

    逻辑：
    1. 读取当日故障数据
    2. 生成故障汇总
    3. 对比上次邮件状态哈希
    4. 只有数据变化才发送邮件
    5. 发送成功后保存当前状态

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
    except Exception as e:
        print(f"❌ 读取数据文件失败：{e}")
        log(f"Failed to read data: {e}", "ERROR")
        return False

    # 生成故障汇总
    print("\n📊 生成故障汇总...")
    fault_summary = generate_fault_summary(df, target_date)

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
        # 准备附件路径
        attachment = daily_file if os.path.exists(daily_file) else None

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

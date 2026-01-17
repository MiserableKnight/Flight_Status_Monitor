"""
发送测试故障邮件

使用当前故障数据发送测试邮件（应用过滤规则后）
"""

import os
import sys
from datetime import datetime

import pandas as pd

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.config_loader import load_config
from core.fault_filter import FaultFilter
from core.fault_status_notifier import FaultStatusNotifier
from core.logger import get_logger

# 导入故障监控脚本的辅助函数
from processors.fault_status_monitor import (
    generate_fault_summary,
    load_flight_times,
)

log = get_logger()

# 机场代码到城市名称的映射
AIRPORT_TO_CITY = {"VVNB": "河内", "VVTS": "胡志明", "VVCS": "昆岛"}

# 加载统一配置
config_loader = load_config()
gmail_config = config_loader.get_gmail_config()


def extract_city_name(airport_str):
    """从机场字符串中提取城市名称"""
    if not airport_str:
        return None

    if "-" in airport_str:
        airport_code = airport_str.split("-")[0].strip()
    else:
        airport_code = airport_str.strip()

    return AIRPORT_TO_CITY.get(airport_code)


def get_route_pair(flight_num, departure_airport_str, arrival_airport_str):
    """获取城市对字符串"""
    dep_city = extract_city_name(departure_airport_str)
    arr_city = extract_city_name(arrival_airport_str)

    if dep_city and arr_city:
        return f"{dep_city}-{arr_city}"

    return None


def send_test_fault_email():
    """发送测试故障邮件"""
    print("=" * 80)
    print("测试故障邮件发送")
    print("=" * 80)

    # 获取今天的日期
    target_date = datetime.now().strftime("%Y-%m-%d")
    print(f"\n📅 测试日期: {target_date}")

    # 读取今日故障数据
    data_file = os.path.join(project_root, "data", "daily_raw", f"fault_data_{target_date}.csv")

    if not os.path.exists(data_file):
        print(f"\n❌ 数据文件不存在: {data_file}")
        return False

    try:
        # 读取CSV文件
        df = pd.read_csv(data_file, encoding="utf-8-sig")

        # 重命名可能的列名变体
        if "触发_time" in df.columns and "触发时间" not in df.columns:
            df.rename(columns={"触发_time": "触发时间"}, inplace=True)

        print(f"\n📊 原始数据: {len(df)} 行")
    except Exception as e:
        print(f"\n❌ 读取数据失败: {e}")
        return False

    # 应用故障过滤规则
    print("\n🔍 应用故障过滤规则...")
    try:
        filter_obj = FaultFilter()
        filter_stats = filter_obj.get_filter_stats()
        print(
            f"   📋 过滤规则: 组合规则 {filter_stats['single_filter_rules']} 条, 关联规则 {filter_stats['group_filter_rules']} 条"
        )

        df = filter_obj.apply_filters(df)
        print(f"   ✅ 过滤后剩余 {len(df)} 行数据")
    except Exception as e:
        print(f"   ⚠️ 过滤失败: {e}")
        return False

    # 加载航班时间数据
    print("\n✈️ 加载航班时间数据...")
    flight_times = load_flight_times(target_date)
    if flight_times:
        print(f"   ✅ 成功加载 {len(flight_times)} 条航班时间记录")
    else:
        print("   ⚠️ 未找到航班时间数据")

    # 生成故障汇总
    print("\n📊 生成故障汇总...")
    fault_summary = generate_fault_summary(df, target_date, flight_times)

    # 打印汇总内容
    print("\n📧 邮件内容预览:")
    print("=" * 80)
    print(fault_summary)
    print("=" * 80)

    # 发送邮件
    print("\n📧 发送测试邮件...")
    notifier = FaultStatusNotifier(config_dict=gmail_config)

    if notifier.is_enabled():
        # 发送邮件（使用自定义主题）
        try:
            # 直接调用内部方法，使用测试主题
            if notifier.send_fault_status_notification(
                fault_summary, target_date, None, subject_prefix="[测试]"
            ):
                print("   ✅ 测试邮件发送成功！")
                log(f"Test fault email sent successfully for {target_date}", "SUCCESS")
                return True
            else:
                print("   ⚠️ 邮件发送失败")
                return False
        except Exception as e:
            print(f"   ⚠️ 发送邮件时出错: {e}")
            # 尝试使用原始方法
            if notifier.send_fault_status_notification(fault_summary, target_date, None):
                print("   ✅ 测试邮件发送成功！")
                return True
            else:
                print("   ⚠️ 邮件发送失败")
                return False
    else:
        print("   ⚠️ 邮件通知未启用")
        print("\nℹ️  请在 config.ini 中启用邮件通知功能")
        return False


if __name__ == "__main__":
    success = send_test_fault_email()

    print("\n" + "=" * 80)
    if success:
        print("✅ 测试邮件发送完成")
    else:
        print("⚠️ 测试邮件发送失败")
    print("=" * 80)

    sys.exit(0 if success else 1)

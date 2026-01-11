# -*- coding: utf-8 -*-
"""
使用真实数据测试异常检测和邮件通知
"""
import sys
import os
import pandas as pd

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from leg_status_monitor import get_current_flight_status
from core.leg_status_notifier import LegStatusNotifier
from config.config_loader import load_config

def test_with_real_data():
    """使用真实数据测试"""
    print("📊 使用真实数据测试异常检测")
    print("="*60)

    # 读取真实数据
    data_file = os.path.join(project_root, 'test', 'data', 'leg_data_2025-05-21.csv')

    if not os.path.exists(data_file):
        print(f"❌ 数据文件不存在: {data_file}")
        return False

    df = pd.read_csv(data_file, encoding='utf-8')
    print(f"✅ 读取到 {len(df)} 行数据")
    print(f"📅 日期: {df['日期'].iloc[0]}")
    print(f"✈️ 飞机: {df['执飞飞机'].unique()}")
    print(f"🔢 航班号: {df['航班号'].unique()}")
    print()

    # 查看数据概览
    print("📋 数据概览：")
    print("-"*60)
    for idx, row in df.iterrows():
        print(f"{row['航班号']}: {row['起飞机场']} -> {row['着陆机场']}")
        print(f"  OUT: {row['OUT']}, OFF: {row['OFF']}, ON: {row['ON']}, IN: {row['IN']}")
    print("-"*60)
    print()

    # 为每架飞机生成状态通知
    all_aircraft = df['执飞飞机'].unique()
    all_notifications = []

    for aircraft_num in all_aircraft:
        df_aircraft = df[df['执飞飞机'] == aircraft_num]
        if len(df_aircraft) > 0:
            print(f"\n🔍 分析飞机: {aircraft_num}")
            print("-"*60)

            notifications = get_current_flight_status(df_aircraft, aircraft_num)
            all_notifications.extend(notifications)

            print("生成的通知：")
            for msg in notifications:
                print(f"  {msg}")
            print()

    # 生成完整邮件内容
    print("\n" + "="*60)
    print("📧 完整邮件内容：")
    print("="*60)

    email_body = '\n'.join(all_notifications)
    print(email_body)
    print()

    # 直接发送邮件
    print("="*60)
    print("📤 发送测试邮件...")
    print("="*60)

    # 加载配置
    config_loader = load_config()
    gmail_config = config_loader.get_gmail_config()

    # 创建通知器
    notifier = LegStatusNotifier(config_dict=gmail_config)

    if notifier.is_enabled():
        subject = f"【真实数据测试】航班状态 - {df['日期'].iloc[0]}"
        if notifier.send_email(subject, email_body):
            print("✅ 测试邮件发送成功！")
            return True
        else:
            print("❌ 邮件发送失败")
            return False
    else:
        print("⚠️ Gmail通知未启用")
        return False


if __name__ == "__main__":
    try:
        success = test_with_real_data()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

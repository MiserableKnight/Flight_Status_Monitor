# -*- coding: utf-8 -*-
"""
测试备降邮件通知
"""
import sys
import os
import pandas as pd

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from core.leg_status_notifier import LegStatusNotifier
from core.diversion_detector import DiversionDetector
from config.config_loader import load_config

def test_diversion_email():
    """测试备降邮件通知"""
    print("📧 测试备降邮件通知")
    print("="*60)

    # 加载配置
    config_loader = load_config()
    gmail_config = config_loader.get_gmail_config()

    # 创建通知器
    notifier = LegStatusNotifier(config_dict=gmail_config)

    if not notifier.is_enabled():
        print("⚠️ Gmail通知未启用，请在config.ini中配置")
        return False

    # 使用真实场景测试备降+状态组合
    # 创建测试数据
    import pandas as pd

    # 场景1: VJ105备降海防并已落地
    test_data1 = pd.DataFrame({
        '执飞飞机': ['B-652G', 'B-652G', 'B-652G', 'B-652G'],
        '航班号': ['VJ105', 'VJ105', 'VJ112', 'VJ113'],
        '起飞机场': ['VVNB-内排国际机场', 'VVNB-内排国际机场', 'VVCI-海防吉碑国际', 'VVTS-新山一国际机场'],
        '着陆机场': ['VVCI-海防吉碑国际', 'VVCI-海防吉碑国际', 'VVTS-新山一国际机场', 'VVCS-昆仑国际机场'],
        'OUT': ['06:45', '06:45', '', ''],
        'OFF': ['06:55', '06:55', '', ''],
        'ON': ['08:00', '08:00', '', ''],
        'IN': ['08:15', '08:15', '', '']
    })

    # 场景2: VJ112起降机场相同（胡志明），已起飞
    test_data2 = pd.DataFrame({
        '执飞飞机': ['B-656E', 'B-656E'],
        '航班号': ['VJ112', 'VJ113'],
        '起飞机场': ['VVTS-新山一国际机场', 'VVTS-新山一国际机场'],
        '着陆机场': ['VVTS-新山一国际机场', 'VVCS-昆仑国际机场'],
        'OUT': ['09:20', ''],
        'OFF': ['09:30', ''],
        'ON': ['', ''],
        'IN': ['', '']
    })

    # 场景3: VJ999非计划航班，在空中
    test_data3 = pd.DataFrame({
        '执飞飞机': ['B-652G'],
        '航班号': ['VJ999'],
        '起飞机场': ['VVNB-内排国际机场'],
        '着陆机场': ['VVCT-芹苴国际机场'],
        'OUT': ['10:00'],
        'OFF': ['10:10'],
        'ON': ['11:30'],
        'IN': ['']
    })

    # 生成测试邮件内容
    from leg_status_monitor import get_current_flight_status

    notifications = []
    notifications.append("📋 场景1: VJ105备降海防并已落地")
    notifications.extend(get_current_flight_status(test_data1, 'B-652G'))
    notifications.append("")
    notifications.append("📋 场景2: VJ112起降机场相同（胡志明），已起飞")
    notifications.extend(get_current_flight_status(test_data2, 'B-656E'))
    notifications.append("")
    notifications.append("📋 场景3: VJ999非计划航班，在空中")
    notifications.extend(get_current_flight_status(test_data3, 'B-652G'))

    email_body = '\n'.join(notifications)

    print("\n📋 邮件内容预览：")
    print("-"*60)
    print(email_body)
    print("-"*60)

    # 发送邮件
    print("\n📤 发送测试邮件...")
    subject = "【测试】备降事件通知 - 航班监控系统"

    if notifier.send_email(subject, email_body):
        print("✅ 测试邮件发送成功！")
        return True
    else:
        print("❌ 测试邮件发送失败")
        return False


if __name__ == "__main__":
    try:
        success = test_diversion_email()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

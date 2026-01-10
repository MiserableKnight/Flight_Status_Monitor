# -*- coding: utf-8 -*-
"""
测试备降通知+状态组合
"""
import sys
import os
import pandas as pd

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from leg_status_monitor import get_current_flight_status, wrap_status_with_diversion
from core.diversion_detector import DiversionDetector

def test_diversion_with_status():
    """测试备降+状态组合通知"""
    print("🧪 测试备降+状态组合通知")
    print("="*60)

    # 创建测试数据 - VJ105备降海防并已落地
    test_data = pd.DataFrame({
        '执飞飞机': ['B-652G', 'B-652G', 'B-652G', 'B-652G'],
        '航班号': ['VJ105', 'VJ105', 'VJ112', 'VJ113'],
        '起飞机场': ['VVNB-内排国际机场', 'VVNB-内排国际机场', 'VVCI-海防吉碑国际', 'VVTS-新山一国际机场'],
        '着陆机场': ['VVCI-海防吉碑国际', 'VVCI-海防吉碑国际', 'VVTS-新山一国际机场', 'VVCS-昆仑国际机场'],
        'OUT': ['06:45', '06:45', '', ''],
        'OFF': ['06:55', '06:55', '', ''],
        'ON': ['08:00', '08:00', '', ''],
        'IN': ['08:15', '08:15', '', '']
    })

    print("\n📊 测试场景1: VJ105备降海防并已落地")
    print("-"*60)
    result = get_current_flight_status(test_data, 'B-652G')
    for msg in result:
        print(msg)

    print("\n" + "="*60)
    print("\n📊 测试场景2: VJ105备降海防，在空中（ON有值，IN无值）")
    print("-"*60)

    test_data2 = pd.DataFrame({
        '执飞飞机': ['B-652G', 'B-652G'],
        '航班号': ['VJ105', 'VJ105'],
        '起飞机场': ['VVNB-内排国际机场', 'VVNB-内排国际机场'],
        '着陆机场': ['VVCI-海防吉碑国际', 'VVCI-海防吉碑国际'],
        'OUT': ['06:45', '06:45'],
        'OFF': ['06:55', '06:55'],
        'ON': ['08:00', '08:00'],
        'IN': ['', '']  # 还未落地
    })

    result2 = get_current_flight_status(test_data2, 'B-652G')
    for msg in result2:
        print(msg)

    print("\n" + "="*60)
    print("\n📊 测试场景3: VJ112起降机场相同（胡志明-胡志明），已滑出")
    print("-"*60)

    test_data3 = pd.DataFrame({
        '执飞飞机': ['B-656E', 'B-656E'],
        '航班号': ['VJ112', 'VJ113'],
        '起飞机场': ['VVTS-新山一国际机场', 'VVTS-新山一国际机场'],
        '着陆机场': ['VVTS-新山一国际机场', 'VVCS-昆仑国际机场'],
        'OUT': ['09:20', ''],
        'OFF': ['', ''],
        'ON': ['', ''],
        'IN': ['', '']
    })

    result3 = get_current_flight_status(test_data3, 'B-656E')
    for msg in result3:
        print(msg)

    print("\n" + "="*60)
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    try:
        test_diversion_with_status()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

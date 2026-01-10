# -*- coding: utf-8 -*-
"""
备降检测功能测试脚本
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config.flight_schedule import FlightSchedule
from core.diversion_detector import DiversionDetector

def test_diversion_detector():
    """测试备降检测器"""
    print("🧪 备降检测器测试")
    print("="*60)

    detector = DiversionDetector()

    # 测试1: 正常航班
    print("\n✅ 测试1: 正常航班 VJ105 (河内->昆岛)")
    result = detector.detect_diversion(
        'VJ105',
        'VVNB-内排国际机场',
        'VVCS-昆仑国际机场'
    )
    print(f"结果: {result if result else '正常，无备降'}")
    assert result is None, "正常航班不应被检测为备降"

    # 测试2: 备降海防
    print("\n⚠️ 测试2: VJ105备降海防")
    result = detector.detect_diversion(
        'VJ105',
        'VVNB-内排国际机场',
        'VVCI-海防吉碑国际'
    )
    assert result is not None, "应检测到备降"
    assert result['diversion_type'] == 'route_mismatch', "备降类型应为 route_mismatch"
    print(f"✅ 检测到备降: {detector.get_diversion_type_description(result['diversion_type'])}")
    print(f"   原计划: {result['original_route']}")
    print(f"   实际执行: {result['actual_route']}")
    print(f"   备降机场: {result['diversion_airport']}")

    # 测试3: 起降机场相同
    print("\n⚠️ 测试3: VJ112起降机场相同（胡志明-胡志明）")
    result = detector.detect_diversion(
        'VJ112',
        'VVTS-新山一国际机场',
        'VVTS-新山一国际机场'
    )
    assert result is not None, "应检测到备降"
    assert result['diversion_type'] == 'same_airport', "备降类型应为 same_airport"
    print(f"✅ 检测到备降: {detector.get_diversion_type_description(result['diversion_type'])}")
    print(f"   原计划: {result['original_route']}")
    print(f"   实际执行: {result['actual_route']}")
    print(f"   备降机场: {result['diversion_airport']}")

    # 测试4: 未知航班
    print("\n⚠️ 测试4: 未知航班号 VJ999")
    result = detector.detect_diversion(
        'VJ999',
        'VVNB-内排国际机场',
        'VVCI-海防吉碑国际'
    )
    assert result is not None, "应检测到备降"
    assert result['diversion_type'] == 'unknown_flight', "备降类型应为 unknown_flight"
    print(f"✅ 检测到备降: {detector.get_diversion_type_description(result['diversion_type'])}")
    print(f"   实际执行: {result['actual_route']}")
    print(f"   备降机场: {result['diversion_airport']}")

    # 测试5: 河内-胡志明异常航线
    print("\n⚠️ 测试5: VJ107备降胡志明（原计划河内->昆岛）")
    result = detector.detect_diversion(
        'VJ107',
        'VVNB-内排国际机场',
        'VVTS-新山一国际机场'
    )
    assert result is not None, "应检测到备降"
    assert result['diversion_type'] == 'route_mismatch', "备降类型应为 route_mismatch"
    print(f"✅ 检测到备降: {detector.get_diversion_type_description(result['diversion_type'])}")
    print(f"   原计划: {result['original_route']}")
    print(f"   实际执行: {result['actual_route']}")
    print(f"   备降机场: {result['diversion_airport']}")

    # 测试6: 机场名称简化
    print("\n🔧 测试6: 机场名称简化")
    test_cases = [
        ('VVNB-内排国际机场', '河内'),
        ('VVCS-昆仑国际机场', '昆岛'),
        ('VVTS-新山一国际机场', '胡志明'),
        ('VVCI-海防吉碑国际', '海防吉碑国际'),
    ]
    for full_name, expected in test_cases:
        result = detector.get_airport_short(full_name)
        print(f"   {full_name} -> {result}")
        assert result == expected, f"期望 {expected}, 得到 {result}"

    print("\n" + "="*60)
    print("✅ 所有测试通过！")

    # 显示备降通知示例
    print("\n📧 备降通知示例：")
    print("-"*60)

    diversion_examples = [
        {
            'aircraft': 'B-652G',
            'flight': 'VJ105',
            'info': {
                'diversion_type': 'route_mismatch',
                'original_route': 'HAN-VCS',
                'actual_route': '河内-海防',
                'diversion_airport': '海防'
            }
        },
        {
            'aircraft': 'B-656E',
            'flight': 'VJ112',
            'info': {
                'diversion_type': 'same_airport',
                'original_route': 'VCS-SGN',
                'actual_route': '胡志明-胡志明',
                'diversion_airport': '胡志明'
            }
        }
    ]

    for ex in diversion_examples:
        detector = DiversionDetector()
        diversion_type = detector.get_diversion_type_description(ex['info']['diversion_type'])
        notification = f"⚠️ {ex['aircraft']} 备降事件：{ex['flight']} {diversion_type}，原计划{ex['info']['original_route']}，实际执行{ex['info']['actual_route']}，备降{ex['info']['diversion_airport']}。异常情况请询问相应专业人员。"
        print(notification)
        print()


if __name__ == "__main__":
    try:
        test_diversion_detector()
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

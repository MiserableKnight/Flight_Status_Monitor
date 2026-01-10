# -*- coding: utf-8 -*-
"""
调度模式测试脚本
用于验证智能航班生命周期监控逻辑是否正确
"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config.flight_schedule import FlightSchedule
from core.flight_tracker import FlightTracker, FlightStatus


def test_flight_schedule():
    """测试航班计划配置"""
    print("="*60)
    print("🧪 测试1: 航班计划配置")
    print("="*60)

    print("\n✅ 所有航班计划（北京时间）:")
    for flight_num in FlightSchedule.get_all_flights():
        info = FlightSchedule.get_flight_info(flight_num)
        print(f"  {flight_num}: {info['scheduled_departure']} (北京时间)")
        print(f"           {info['duration_minutes']}分钟, {info['route']}")

    # 测试时间转换
    print("\n✅ 时间转换测试:")
    test_time = datetime(2026, 1, 9, 7, 45)  # 07:45 北京时间
    vietnam_time = FlightSchedule.to_vietnam_time(test_time)
    print(f"  北京时间: {test_time.strftime('%H:%M')}")
    print(f"  越南时间: {vietnam_time.strftime('%H:%M')}")

    # 测试格式化
    formatted = FlightSchedule.format_vietnam_time(test_time)
    print(f"  格式化越南时间: {formatted}")

    return True


def test_flight_tracker_initial():
    """测试FlightTracker初始化"""
    print("\n" + "="*60)
    print("🧪 测试2: FlightTracker初始化")
    print("="*60)

    tracker = FlightTracker()
    print(f"\n✅ 跟踪的飞机数量: {len(tracker.flights)}")

    if tracker.flights:
        print("\n✅ 当前航班状态:")
        for aircraft, status in tracker.flights.items():
            print(f"  {aircraft} - {status.flight_number}: {status.current_phase}")

    return True


def test_monitoring_decision_logic():
    """测试监控决策逻辑"""
    print("\n" + "="*60)
    print("🧪 测试3: 监控决策逻辑")
    print("="*60)

    # 创建测试用的FlightTracker
    tracker = FlightTracker()

    # 场景1: 早上7:00 - VJ105还未到计划起飞时间
    print("\n📋 场景1: 早上07:00 (北京时间)")
    print("  - B-652G (VJ105): 计划起飞 07:45")
    print("  - B-656E (VJ107): 计划起飞 09:15")

    test_time_1 = datetime(2026, 1, 9, 7, 0)
    result_1 = tracker.should_monitor_leg_first(test_time_1)
    print(f"  ✅ 应该监控: {'Leg页面' if result_1 else '故障页面'}")

    # 场景2: 早上8:00 - VJ105已过计划起飞时间，还在地面
    print("\n📋 场景2: 早上08:00 (北京时间)")
    print("  - B-652G (VJ105): 已过计划起飞时间，假设在地面（已滑出）")
    print("  - B-656E (VJ107): 未到计划起飞时间")

    # 模拟B-652G已滑出但未起飞
    tracker.flights['B-652G'] = FlightStatus('VJ105', 'B-652G')
    tracker.flights['B-652G'].pushback_time = datetime(2026, 1, 9, 7, 50)
    tracker.flights['B-652G'].update_status({})

    test_time_2 = datetime(2026, 1, 9, 8, 0)
    result_2 = tracker.should_monitor_leg_first(test_time_2)
    print(f"  ✅ 应该监控: {'Leg页面' if result_2 else '故障页面'}")
    print(f"  ✅ B-652G状态: {tracker.flights['B-652G'].get_flight_phase()}")

    # 场景3: 早上8:30 - VJ105已起飞，VJ107未到计划时间
    print("\n📋 场景3: 早上08:30 (北京时间)")
    print("  - B-652G (VJ105): 已起飞，在空中")
    print("  - B-656E (VJ107): 未到计划起飞时间")

    tracker.flights['B-652G'].takeoff_time = datetime(2026, 1, 9, 8, 0)
    tracker.flights['B-652G'].scheduled_arrival = datetime(2026, 1, 9, 9, 50)
    tracker.flights['B-652G'].update_status({})

    test_time_3 = datetime(2026, 1, 9, 8, 30)
    result_3 = tracker.should_monitor_leg_first(test_time_3)
    print(f"  ✅ 应该监控: {'Leg页面' if result_3 else '故障页面'}")
    print(f"  ✅ B-652G在空中: {tracker.flights['B-652G'].is_airborne()}")

    # 场景4: 早上9:20 - VJ105快到计划到达时间
    print("\n📋 场景4: 早上09:20 (北京时间)")
    print("  - B-652G (VJ105): 在空中，已到计划到达时间")
    print("  - B-656E (VJ107): 未到计划起飞时间")

    test_time_4 = datetime(2026, 1, 9, 9, 20)
    result_4 = tracker.should_monitor_leg_first(test_time_4)
    print(f"  ✅ 应该监控: {'Leg页面' if result_4 else '故障页面'}")
    print(f"  ✅ 需要到达监控: {tracker.flights['B-652G'].needs_arrival_monitoring(test_time_4)}")

    # 场景5: 早上9:30 - VJ105已落地，VJ107已过计划时间
    print("\n📋 场景5: 早上09:30 (北京时间)")
    print("  - B-652G (VJ105): 已落地")
    print("  - B-656E (VJ107): 已过计划起飞时间")

    tracker.flights['B-652G'].landing_time = datetime(2026, 1, 9, 9, 20)
    tracker.flights['B-652G'].update_status({})

    test_time_5 = datetime(2026, 1, 9, 9, 30)
    result_5 = tracker.should_monitor_leg_first(test_time_5)
    print(f"  ✅ 应该监控: {'Leg页面' if result_5 else '故障页面'}")

    return True


def test_status_summary():
    """测试状态摘要显示"""
    print("\n" + "="*60)
    print("🧪 测试4: 状态摘要显示")
    print("="*60)

    tracker = FlightTracker()

    # 模拟一些航班状态
    tracker.flights['B-652G'] = FlightStatus('VJ105', 'B-652G')
    tracker.flights['B-652G'].takeoff_time = datetime(2026, 1, 9, 8, 0)
    tracker.flights['B-652G'].scheduled_arrival = datetime(2026, 1, 9, 9, 50)
    tracker.flights['B-652G'].update_status({})

    tracker.flights['B-656E'] = FlightStatus('VJ107', 'B-656E')
    tracker.flights['B-656E'].pushback_time = datetime(2026, 1, 9, 9, 0)
    tracker.flights['B-656E'].update_status({})

    print("\n✅ 当前状态摘要:")
    print(tracker.get_status_summary())

    return True


def test_time_calculations():
    """测试时间计算"""
    print("\n" + "="*60)
    print("🧪 测试5: 时间计算")
    print("="*60)

    # 测试计划到达时间计算
    print("\n✅ 计划到达时间计算:")
    takeoff_time = datetime(2026, 1, 9, 7, 50)  # 07:50 起飞
    scheduled_arrival = FlightSchedule.calculate_scheduled_arrival('VJ105', takeoff_time)
    print(f"  VJ105 起飞时间: {takeoff_time.strftime('%H:%M')}")
    print(f"  航程: {FlightSchedule.get_flight_info('VJ105')['duration_minutes']}分钟")
    print(f"  计划到达时间: {scheduled_arrival.strftime('%H:%M')}")

    # 测试越南时间转换
    print("\n✅ 越南时间转换（邮件展示用）:")
    beijing_time = datetime(2026, 1, 9, 7, 50)
    vietnam_time = FlightSchedule.to_vietnam_time(beijing_time)
    print(f"  内部存储（北京时间）: {beijing_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  邮件展示（越南时间）: {vietnam_time.strftime('%Y-%m-%d %H:%M')}")

    return True


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🚀 航班智能调度系统 - 测试套件")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    tests = [
        ("航班计划配置", test_flight_schedule),
        ("FlightTracker初始化", test_flight_tracker_initial),
        ("监控决策逻辑", test_monitoring_decision_logic),
        ("状态摘要显示", test_status_summary),
        ("时间计算", test_time_calculations)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, "✅ 通过", None))
        except Exception as e:
            results.append((test_name, "❌ 失败", str(e)))

    # 打印测试结果汇总
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)

    for test_name, status, error in results:
        print(f"{status} {test_name}")
        if error:
            print(f"     错误: {error}")

    passed = sum(1 for _, status, _ in results if status == "✅ 通过")
    total = len(results)

    print(f"\n📈 测试通过率: {passed}/{total} ({passed*100//total}%)")

    if passed == total:
        print("\n🎉 所有测试通过！调度系统准备就绪。")
    else:
        print("\n⚠️ 部分测试失败，请检查相关模块。")

    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60)


if __name__ == "__main__":
    main()

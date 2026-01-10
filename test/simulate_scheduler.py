# -*- coding: utf-8 -*-
"""
调度模式运行模拟
模拟一整天(06:30-21:00)的调度运行过程，展示页面切换逻辑
"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config.flight_schedule import FlightSchedule
from core.flight_tracker import FlightTracker, FlightStatus


def simulate_full_day():
    """模拟一整天的调度运行"""
    print("="*70)
    print("🛫 航班智能调度系统 - 完整运行模拟")
    print("="*70)
    print(f"模拟日期: 2026-01-09")
    print(f"模拟时间范围: 06:30 - 21:00 (北京时间)")
    print("="*70)

    # 初始化跟踪器
    tracker = FlightTracker()

    # 模拟的关键时间点（北京时间）
    scenarios = [
        ("06:30", "系统启动", "等待VJ105计划起飞时间", {}),
        ("07:45", "VJ105计划起飞时间", "开始监控Leg页面，等待滑出", {}),
        ("07:50", "VJ105滑出", "继续监控Leg页面", {
            'B-652G': {'pushback': '07:50'}
        }),
        ("08:00", "VJ105起飞", "切换到故障监控页面", {
            'B-652G': {'takeoff': '08:00', 'calculate_arrival': True}
        }),
        ("08:30", "VJ105在空中，VJ107未到计划时间", "继续监控故障页面", {}),
        ("09:15", "VJ107计划起飞时间", "切换到Leg页面，等待滑出", {}),
        ("09:20", "VJ107滑出", "继续监控Leg页面", {
            'B-656E': {'pushback': '09:20'}
        }),
        ("09:30", "VJ107起飞，VJ105接近到达时间", "等待VJ105落地", {
            'B-656E': {'takeoff': '09:30', 'calculate_arrival': True}
        }),
        ("09:50", "VJ105计划到达时间", "切换到Leg页面，等待落地", {}),
        ("09:55", "VJ105落地", "继续监控Leg页面，等待滑入", {
            'B-652G': {'landing': '09:55'}
        }),
        ("10:00", "VJ105滑入", "检查VJ107状态，决定下一步", {
            'B-652G': {'in_gate': '10:00'}
        }),
        ("10:20", "VJ112计划起飞时间", "监控VJ112", {}),
        ("11:00", "多个航班", "智能决策监控页面", {}),
        ("15:00", "VJ108计划起飞时间", "监控最后一个航班", {}),
        ("16:30", "所有航班完成", "准备结束", {}),
    ]

    # 显示航班计划参考
    print("\n📋 今日航班计划（北京时间）:")
    print("-"*70)
    for flight_num in FlightSchedule.get_all_flights():
        info = FlightSchedule.get_flight_info(flight_num)
        print(f"  {flight_num}: {info['scheduled_departure']} - {info['route']}")
    print("-"*70)

    # 模拟每个场景
    for i, (time_str, event, description, updates) in enumerate(scenarios, 1):
        print(f"\n{'='*70}")
        print(f"📍 场景 {i}: {time_str} - {event}")
        print(f"📝 {description}")
        print('='*70)

        # 解析时间
        hour, minute = map(int, time_str.split(':'))
        current_time = datetime(2026, 1, 9, hour, minute)

        # 更新航班状态
        for aircraft, changes in updates.items():
            if aircraft not in tracker.flights:
                # 创建新航班状态
                flight_num = 'VJ105' if aircraft == 'B-652G' else 'VJ107'
                tracker.flights[aircraft] = FlightStatus(flight_num, aircraft)

            status = tracker.flights[aircraft]

            if 'pushback' in changes:
                status.pushback_time = datetime(2026, 1, 9, *map(int, changes['pushback'].split(':')))
                print(f"  ✈️ {aircraft}: 滑出 {changes['pushback']}")

            if 'takeoff' in changes:
                status.takeoff_time = datetime(2026, 1, 9, *map(int, changes['takeoff'].split(':')))
                print(f"  🛫 {aircraft}: 起飞 {changes['takeoff']}")

                if changes.get('calculate_arrival'):
                    status.scheduled_arrival = FlightSchedule.calculate_scheduled_arrival(
                        status.flight_number,
                        status.takeoff_time
                    )
                    print(f"  📊 {aircraft}: 计划到达 {status.scheduled_arrival.strftime('%H:%M')}")

            if 'landing' in changes:
                status.landing_time = datetime(2026, 1, 9, *map(int, changes['landing'].split(':')))
                print(f"  🛬 {aircraft}: 落地 {changes['landing']}")

            if 'in_gate' in changes:
                status.in_gate_time = datetime(2026, 1, 9, *map(int, changes['in_gate'].split(':')))
                print(f"  ✅ {aircraft}: 滑入 {changes['in_gate']}")

            status.update_status({})

        # 决策监控页面
        should_monitor_leg = tracker.should_monitor_leg_first(current_time)
        monitor_mode = "📊 Leg数据页面" if should_monitor_leg else "🔧 故障页面"

        print(f"\n  🎯 决策结果: {monitor_mode}")
        print(f"  📊 状态摘要:")

        # 显示简要状态
        for aircraft, status in tracker.flights.items():
            phase_names = {
                'scheduled': '计划中',
                'pushback': '滑出',
                'airborne': '空中',
                'landed': '落地',
                'in_gate': '滑入'
            }
            phase = phase_names.get(status.current_phase, '未知')
            print(f"    {aircraft} ({status.flight_number}): {phase}")

        # 等待用户按键（模拟时间流逝）
        if i < len(scenarios):
            input("\n  按 Enter 键继续到下一个场景...")

    print(f"\n{'='*70}")
    print("🌙 已到达 21:00，系统停止运行")
    print("="*70)
    print("\n✅ 模拟完成！")


def main():
    """主函数"""
    print("\n🎮 调度模式交互式模拟器")
    print("="*70)
    print("这个脚本会模拟一整天的调度运行过程")
    print("展示系统如何智能切换 Leg页面 和 故障页面")
    print("\n按 Enter 键开始模拟...")
    input()

    simulate_full_day()


if __name__ == "__main__":
    main()

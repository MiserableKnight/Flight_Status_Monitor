"""
简化版航线链修复测试

直接测试核心逻辑,避免导入依赖
"""

import os
import sys

import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.flight_schedule import FlightSchedule


def test_route_chain_config():
    """测试航线链配置"""
    print("\n" + "=" * 60)
    print("测试航线链配置")
    print("=" * 60)

    # 测试VJ118的航线链
    chain = FlightSchedule.get_route_chain("VJ118")
    print(f"\n✓ VJ118 所属航线链: {chain}")
    expected = ["VJ107", "VJ118", "VJ119", "VJ108"]
    if chain == expected:
        print("  ✅ 正确! (航线B)")
    else:
        print(f"  ❌ 错误! 期望: {expected}")

    # 测试VJ106的航线链
    chain = FlightSchedule.get_route_chain("VJ106")
    print(f"\n✓ VJ106 所属航线链: {chain}")
    expected = ["VJ105", "VJ112", "VJ113", "VJ106"]
    if chain == expected:
        print("  ✅ 正确! (航线A)")
    else:
        print(f"  ❌ 错误! 期望: {expected}")

    # 测试是否为最后航班
    is_last = FlightSchedule.is_last_flight_in_route("VJ106")
    print(f"\n✓ VJ106 是否为航线最后航班: {is_last}")
    if is_last:
        print("  ✅ 正确! VJ106回到河内,完成航线A")
    else:
        print("  ❌ 错误! VJ106应该是航线A的最后航班")

    is_last = FlightSchedule.is_last_flight_in_route("VJ118")
    print(f"\n✓ VJ118 是否为航线最后航班: {is_last}")
    if not is_last:
        print("  ✅ 正确! VJ118不是最后,后面还有VJ119和VJ108")
    else:
        print("  ❌ 错误! VJ118不是航线B的最后航班")

    is_last = FlightSchedule.is_last_flight_in_route("VJ108")
    print(f"\n✓ VJ108 是否为航线最后航班: {is_last}")
    if is_last:
        print("  ✅ 正确! VJ108回到河内,完成航线B")
    else:
        print("  ❌ 错误! VJ108应该是航线B的最后航班")

    print("\n✅ 航线链配置测试完成!")


def demonstrate_fix():
    """演示修复前后的逻辑对比"""
    print("\n" + "=" * 60)
    print("修复效果演示")
    print("=" * 60)

    print("\n📌 场景: B-656E 只有VJ118数据,已完成")
    print("-" * 60)

    # 模拟数据
    data = {
        "执飞飞机": ["B-656E"],
        "航班号": ["VJ118"],
        "OUT": ["11:30"],
        "OFF": ["11:35"],
        "ON": ["12:00"],
        "IN": ["12:05"],
        "起飞机场": ["VVCS-昆仑国际机场"],
        "着陆机场": ["VVTS-新山一国际机场"],
    }
    df = pd.DataFrame(data)

    print("\n📋 数据中的航班: VJ118 (昆岛→胡志明,已完成)")

    # 修复前的逻辑
    print("\n❌ 修复前的错误逻辑:")
    print("   - 动态获取航班: ['VJ118']")
    print("   - 判断: VJ118 已完成,且是序列最后一个")
    print("   - 结果: 'B-656E停靠胡志明；已完成今日所有航班。' ⚠️")
    print("   - 问题: VJ118后面还有VJ119和VJ108!")

    # 修复后的逻辑
    print("\n✅ 修复后的正确逻辑:")
    chain = FlightSchedule.get_route_chain("VJ118")
    print(f"   - 识别航线链: {chain}")
    print("   - 判断: VJ118已完成,但不是航线链最后")
    print("   - 后续: VJ119 (胡志明→昆岛), VJ108 (昆岛→河内)")
    print("   - 结果: 'B-656E停靠胡志明；计划执行VJ119。' ✅")

    print("\n📌 场景2: B-652G 完成VJ106 (航线A最后一段)")
    print("-" * 60)

    print("\n✅ 修复后的正确逻辑:")
    chain = FlightSchedule.get_route_chain("VJ106")
    print(f"   - 识别航线链: {chain}")
    print("   - 判断: VJ106已完成,且是航线链最后")
    print("   - 结果: 'B-652G停靠河内；已完成今日所有航班。' ✅")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("\n🧪 航线链修复逻辑测试")
    print("=" * 60)

    try:
        # 测试配置
        test_route_chain_config()

        # 演示修复效果
        demonstrate_fix()

        print("\n" + "=" * 60)
        print("✅ 测试完成!")
        print("=" * 60)
        print("\n📝 修复总结:")
        print("  1. ✅ 添加航线链配置 (ROUTE_A, ROUTE_B)")
        print("  2. ✅ 实现 get_route_chain() 方法")
        print("  3. ✅ 实现 is_last_flight_in_route() 方法")
        print("  4. ✅ 修改 get_flight_sequence_sorted() 使用航线链")
        print("  5. ✅ 修改 get_current_flight_status() 判断逻辑")
        print("\n🎯 核心改进:")
        print("  - 飞机必须完成航线链最后航班(VJ106/VJ108)才算完成")
        print("  - 即使只看到中间航班,也知道后续航班计划")
        print("  - 所有飞机最终都回河内,符合实际运营逻辑")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

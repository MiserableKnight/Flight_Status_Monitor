# -*- coding: utf-8 -*-
"""
测试动态机场名称解析
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from leg_status_monitor import get_airport_name

def test_airport_parsing():
    """测试动态机场名称解析"""
    print("🧪 测试动态机场名称解析")
    print("="*60)

    # 测试用例
    test_cases = [
        # 正常机场（使用映射表）
        ('VVCS-昆仑国际机场', '昆岛'),
        ('VVNB-内排国际机场', '河内'),
        ('VVTS-新山一国际机场', '胡志明'),

        # 备降机场（动态解析）
        ('VVCI-海防吉碑国际', '海防吉碑'),
        ('VVCT-芹苴国际机场', '芹苴'),

        # 边界情况
        ('未知机场', '未知机场'),
        ('', '未知'),
    ]

    print("\n测试结果：")
    print("-"*60)

    all_passed = True
    for full_name, expected in test_cases:
        if full_name == '':
            result = get_airport_name(None)  # 测试空值
        else:
            result = get_airport_name(full_name)

        passed = result == expected
        status = "✅" if passed else "❌"

        print(f"{status} {full_name if full_name else '(空值)'} -> {result} (期望: {expected})")

        if not passed:
            all_passed = False

    print("-"*60)

    if all_passed:
        print("\n✅ 所有测试通过！")
        return True
    else:
        print("\n❌ 部分测试失败")
        return False


if __name__ == "__main__":
    success = test_airport_parsing()
    sys.exit(0 if success else 1)

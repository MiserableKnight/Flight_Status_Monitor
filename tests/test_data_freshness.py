"""
测试数据新鲜度检查功能
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 数据过期阈值（秒）
DATA_STALE_THRESHOLD = 300  # 5分钟


def is_data_fresh(timestamp_file):
    """
    检查数据是否是新鲜的
    """
    try:
        if not os.path.exists(timestamp_file):
            print("   ⚠️ 未找到数据更新时间戳文件")
            return False

        with open(timestamp_file, encoding="utf-8") as f:
            timestamp_data = json.load(f)

        last_update_str = timestamp_data.get("last_update_time")
        if not last_update_str:
            print("   ⚠️ 时间戳文件中没有更新时间")
            return False

        # 解析最后更新时间
        last_update = datetime.strptime(last_update_str, "%Y-%m-%d %H:%M:%S")
        current_time = datetime.now()

        # 计算时间差（秒）
        time_diff = (current_time - last_update).total_seconds()

        if time_diff > DATA_STALE_THRESHOLD:
            print(f"   ⚠️ 数据已过期：最后更新于 {last_update_str}（{int(time_diff)}秒前）")
            return False

        print(f"   ✅ 数据新鲜：最后更新于 {last_update_str}（{int(time_diff)}秒前）")
        return True

    except Exception as e:
        print(f"   ⚠️ 检查数据新鲜度失败: {e}")
        return False


def test_data_freshness():
    """测试数据新鲜度检查"""
    print("=" * 60)
    print("测试数据新鲜度检查")
    print("=" * 60)

    # 时间戳文件路径
    timestamp_file = Path("data/last_data_update.json")

    # 测试1: 无时间戳文件
    print("\n测试1: 无时间戳文件")
    timestamp_file = Path("data/last_data_update.json")
    if timestamp_file.exists():
        timestamp_file.unlink()
    result = is_data_fresh(timestamp_file)
    print(f"结果: {'数据新鲜' if result else '数据过期'}")
    assert not result, "无时间戳文件时应返回False"
    print("✅ 测试通过")

    # 测试2: 数据新鲜（1分钟前更新）
    print("\n测试2: 数据新鲜（1分钟前更新）")
    timestamp_file.parent.mkdir(parents=True, exist_ok=True)
    fresh_data = {
        "last_update_time": (datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "scheduler": "LegScheduler",
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
    with open(timestamp_file, "w", encoding="utf-8") as f:
        json.dump(fresh_data, f, ensure_ascii=False, indent=2)

    result = is_data_fresh(timestamp_file)
    print(f"结果: {'数据新鲜' if result else '数据过期'}")
    assert result, "1分钟前的数据应该是新鲜的"
    print("✅ 测试通过")

    # 测试3: 数据过期（10分钟前更新）
    print("\n测试3: 数据过期（10分钟前更新）")
    stale_data = {
        "last_update_time": (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S"),
        "scheduler": "LegScheduler",
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
    with open(timestamp_file, "w", encoding="utf-8") as f:
        json.dump(stale_data, f, ensure_ascii=False, indent=2)

    result = is_data_fresh(timestamp_file)
    print(f"结果: {'数据新鲜' if result else '数据过期'}")
    assert not result, "10分钟前的数据应该是过期的"
    print("✅ 测试通过")

    # 清理
    if timestamp_file.exists():
        timestamp_file.unlink()

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    test_data_freshness()

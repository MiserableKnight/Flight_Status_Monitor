# -*- coding: utf-8 -*-
"""
测试调度器导入
"""
import sys
from pathlib import Path

# 确保项目根目录在Python路径中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("🧪 测试调度器导入...")
print("="*60)

try:
    print("1️⃣ 测试导入 LegScheduler...")
    import schedulers.leg_scheduler
    print("   ✅ schedulers.leg_scheduler 导入成功")

    print("\n2️⃣ 测试导入 FaultScheduler...")
    import schedulers.fault_scheduler
    print("   ✅ schedulers.fault_scheduler 导入成功")

    print("\n3️⃣ 验证类是否存在...")
    assert hasattr(schedulers.leg_scheduler, 'LegScheduler')
    print("   ✅ LegScheduler 类存在")

    assert hasattr(schedulers.fault_scheduler, 'FaultScheduler')
    print("   ✅ FaultScheduler 类存在")

    print("\n" + "="*60)
    print("✅ 所有导入测试通过！")
    print("="*60)

except ImportError as e:
    print(f"❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

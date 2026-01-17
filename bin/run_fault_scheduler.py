"""
故障数据监控启动器

解决相对导入问题，使用模块方式运行调度器
"""

import sys
from pathlib import Path

# 确保项目根目录在Python路径中
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    # 使用模块方式运行，避免相对导入问题
    import schedulers.fault_scheduler as fault_module

    fault_module.main()

# -*- coding: utf-8 -*-
"""
导航系统测试脚本
演示智能导航系统的各项功能
"""
from DrissionPage import ChromiumPage, ChromiumOptions
from navigator import (
    smart_navigate,
    ensure_page_state,
    PageState,
    get_current_module,
    check_login_status,
    ensure_home,
    ensure_integrated_monitor,
    ensure_capacity_statistics
)
import time
import sys
import os

# 添加父目录到路径,以便导入navigator模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_navigation_system():
    """测试导航系统的各项功能"""

    print("="*70)
    print("🧪 智能导航系统测试")
    print("="*70)

    # 连接浏览器
    print("\n📡 连接到浏览器(端口9222)...")
    co = ChromiumOptions()
    co.set_local_port(9222)

    try:
        page = ChromiumPage(co)
        print("✅ 浏览器连接成功")
    except Exception as e:
        print(f"❌ 浏览器连接失败: {e}")
        print("\n提示:")
        print("1. 确保Chrome浏览器已启动")
        print("2. 启动命令: chrome.exe --remote-debugging-port=9222")
        print("3. 或者先运行 automation_login.py")
        return

    print("\n" + "="*70)
    print("测试1: 获取当前模块信息")
    print("="*70)
    module = get_current_module(page)
    print(f"📍 当前模块: {module}")

    print("\n" + "="*70)
    print("测试2: 检查登录状态")
    print("="*70)
    is_logged_in = check_login_status(page)
    print(f"🔐 登录状态: {'✅ 已登录' if is_logged_in else '❌ 未登录'}")

    print("\n" + "="*70)
    print("测试3: 智能导航到首页")
    print("="*70)
    success = ensure_home(page)
    if success:
        print("✅ 成功导航到首页")
        time.sleep(2)
        # 再次检查模块
        module = get_current_module(page)
        print(f"📍 当前模块: {module}")
    else:
        print("❌ 导航失败(可能需要登录)")

    print("\n" + "="*70)
    print("测试4: 页面状态详细检测")
    print("="*70)

    test_cases = [
        ("首页", None),
        ("综合监控", "integratedMonitor"),
        ("运力统计", "lineLogNewController"),
    ]

    for desc, keyword in test_cases:
        print(f"\n🔍 检测目标: {desc}")
        state = ensure_page_state(page, target_url_keyword=keyword)
        state_names = {
            PageState.NEED_LOGIN: "需要登录",
            PageState.ALREADY_TARGET: "已在目标页",
            PageState.IN_SYSTEM: "在系统内",
            PageState.OUT_SYSTEM: "在系统外",
            PageState.UNKNOWN: "未知状态"
        }
        print(f"   状态: {state_names.get(state, state)}")

    print("\n" + "="*70)
    print("✅ 测试完成")
    print("="*70)

    print("\n💡 提示:")
    print("- 导航系统已就绪")
    print("- 可以直接运行 faults_data_get.py 或 flight_data_get.py")
    print("- 脚本会自动处理登录和导航")

if __name__ == "__main__":
    test_navigation_system()

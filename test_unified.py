# -*- coding: utf-8 -*-
"""
测试脚本 - 验证统一调度器的基本功能

测试内容：
1. 浏览器连接
2. 标签页分配（基于URL匹配）
3. 智能登录
4. LegFetcher 数据抓取
5. FaultFetcher 页面检查
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from fetchers.leg_fetcher import LegFetcher
from fetchers.fault_fetcher import FaultFetcher


def test_basic_functionality():
    """测试基本功能"""
    print("\n" + "="*60)
    print("🧪 测试：基本功能验证")
    print("="*60)

    # ========== 步骤1: 创建 Fetcher ==========
    print("\n📍 步骤1: 创建 Fetcher 实例...")
    leg_fetcher = LegFetcher()
    fault_fetcher = FaultFetcher()
    print("✅ Fetcher 创建完成")

    # ========== 步骤2: 测试 get_target_url_keyword ==========
    print("\n📍 步骤2: 测试 get_target_url_keyword()...")

    leg_keyword = leg_fetcher.get_target_url_keyword()
    fault_keyword = fault_fetcher.get_target_url_keyword()

    print(f"   LegFetcher URL关键词: {leg_keyword}")
    print(f"   FaultFetcher URL关键词: {fault_keyword}")

    assert leg_keyword == "lineLogController", "LegFetcher URL关键词不正确"
    assert fault_keyword == "integratedMonitorController", "FaultFetcher URL关键词不正确"

    print("✅ URL关键词测试通过")

    # ========== 步骤3: 连接浏览器 ==========
    print("\n📍 步骤3: 连接浏览器...")

    leg_page = leg_fetcher.connect_browser()
    if not leg_page:
        print("❌ LegFetcher 连接失败")
        return False

    print("✅ LegFetcher 已连接")

    fault_page = fault_fetcher.connect_browser()
    if not fault_page:
        print("❌ FaultFetcher 连接失败")
        return False

    print("✅ FaultFetcher 已连接")

    # ========== 步骤4: 验证标签页隔离 ==========
    print("\n📍 步骤4: 验证标签页隔离...")

    print(f"   LegFetcher tab_id: {leg_page.tab_id}")
    print(f"   FaultFetcher tab_id: {fault_page.tab_id}")

    assert leg_page.tab_id != fault_page.tab_id, "两个 Fetcher 应该使用不同的标签页"

    print("✅ 标签页隔离验证通过")

    # ========== 步骤5: 测试智能登录 ==========
    print("\n📍 步骤5: 测试智能登录...")

    if not leg_fetcher.smart_login(leg_page):
        print("❌ 智能登录失败")
        return False

    print("✅ 智能登录成功")

    # ========== 步骤6: 测试标签页切换 ==========
    print("\n📍 步骤6: 测试标签页切换...")

    # 切换到 FaultFetcher 标签页
    if not fault_fetcher.ensure_assigned_tab(fault_page):
        print("❌ 切换到 FaultFetcher 标签页失败")
        return False

    print("✅ 已切换到 FaultFetcher 标签页")

    # 切换回 LegFetcher 标签页
    if not leg_fetcher.ensure_assigned_tab(leg_page):
        print("❌ 切换回 LegFetcher 标签页失败")
        return False

    print("✅ 已切换回 LegFetcher 标签页")

    print("\n" + "="*60)
    print("✅ 所有测试通过！")
    print("="*60)
    return True


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🧪 统一调度器测试脚本")
    print("="*60)

    try:
        success = test_basic_functionality()

        if success:
            print("\n🎉 测试成功！")
            print("\n💡 下一步：")
            print("   1. 运行 'python unified_scheduler.py --interactive' 进入交互模式")
            print("   2. 或运行 'python unified_scheduler.py' 启动自动调度")
        else:
            print("\n❌ 测试失败")
            print("\n💡 请检查：")
            print("   1. Chrome 浏览器是否在调试模式运行（端口9222）")
            print("   2. 网络连接是否正常")
            print("   3. 配置文件是否正确")

    except AssertionError as e:
        print(f"\n❌ 断言失败: {e}")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

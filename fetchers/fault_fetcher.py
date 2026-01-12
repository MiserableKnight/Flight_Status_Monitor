# -*- coding: utf-8 -*-
"""
故障数据监控模块

功能:
- 监控故障页面 https://cis.comac.cc:8004/caphm/integratedMonitorController/list.html?gzphFlag=1&faultType=1,2
- 支持与 leg_fetcher 并行运行，共享同一个浏览器实例
"""
import time
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from fetchers.base_fetcher import BaseFetcher


class FaultFetcher(BaseFetcher):
    """故障数据监控器"""

    def get_target_url_keyword(self):
        """
        返回用于标签页匹配的URL关键词

        Returns:
            str: 'integratedMonitorController'
        """
        return "integratedMonitorController"

    def get_data_prefix(self):
        """返回数据文件前缀"""
        return "fault_data"

    def navigate_to_target_page(self, page, target_date):
        """
        导航到故障监控页面（在分配的标签页打开）

        Args:
            page: ChromiumPage 对象
            target_date: 目标日期（暂不使用，保留接口兼容性）

        Returns:
            成功返回 True，失败返回 None
        """
        # 标签页隔离检查
        if not self.ensure_assigned_tab(page):
            print("⚠️  标签页检查失败")
            return None

        print("\n" + "="*60)
        print("🚀 故障监控页面启动")
        print(f"⏰ 启动时间: {time.strftime('%H:%M:%S')}")
        print(f"🏷️  标签页索引: {self.assigned_tab_index}")
        print("="*60)

        # 故障监控页面URL
        target_url = "https://cis.comac.cc:8004/caphm/integratedMonitorController/list.html?gzphFlag=1&faultType=1,2"

        # 检查当前是否已在目标页面
        current_url = page.url
        print(f"📍 当前URL: {current_url}")

        if "integratedMonitorController/list.html" in current_url:
            print("   ✅ 已在故障监控页面")
            print("="*60)
            return True

        # 在当前标签页中打开故障监控页面
        print(f"🎯 导航到故障监控页面...")
        print(f"   目标URL: {target_url}")

        try:
            # 直接在当前标签页导航（已通过ensure_assigned_tab确保在正确的标签页）
            page.get(target_url)
            print("   ✅ 已导航到故障监控页面")
            print("="*60)

            # 等待页面加载
            time.sleep(3)

            return True

        except Exception as e:
            print(f"   ❌ 打开出错: {e}")
            print("="*60)
            return None


def main():
    """
    主函数:启动故障监控页面

    说明:
    - 此脚本会连接到已运行的Chrome浏览器（端口9222）
    - 请确保先启动Chrome调试模式或让leg_fetcher先运行
    """
    print("🚀 启动故障监控页面...")

    fetcher = FaultFetcher()

    # 使用固定的target_date参数（保持接口兼容）
    target_date = fetcher.get_today_date()

    try:
        # 连接浏览器
        page = fetcher.connect_browser()
        if not page:
            print("\n❌ 无法连接到浏览器")
            print("💡 请确保:")
            print("   1. Chrome浏览器已启动调试模式（端口9222）")
            print("   2. 或者先运行 leg_fetcher 让它建立浏览器连接")
            return False

        # 智能登录
        if not fetcher.smart_login(page):
            print("\n❌ 登录失败")
            return False

        # 导航到故障监控页面
        result = fetcher.navigate_to_target_page(page, target_date)

        if result:
            print("\n✅ 故障监控页面已打开")
            print("💡 提示: 浏览器将保持打开状态，可以手动查看故障数据")
            print("💡 按Ctrl+C退出此脚本（浏览器不会关闭）")
            return True
        else:
            print("\n❌ 打开故障监控页面失败")
            return False

    except KeyboardInterrupt:
        print("\n\n⚠️ 收到中断信号，正在退出...")
        print("💡 浏览器仍然保持打开状态")
        return True
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
故障数据调度器

专门管理故障数据的监控：
- 连接端口 9333
- 每5分钟检查一次
- 独立循环运行
- 支持依赖注入
"""
from datetime import datetime, timedelta
from typing import Optional

from .base_scheduler import BaseScheduler
from fetchers.fault_fetcher import FaultFetcher
from interfaces.interfaces import IFetcher, ILogger, IConfigLoader


class FaultScheduler(BaseScheduler):
    """
    故障数据调度器

    继承自 BaseScheduler，专门负责故障数据的监控
    支持依赖注入，提高可测试性和可维护性

    使用依赖注入：
        scheduler = FaultScheduler(
            fetcher=MyFaultFetcher(),
            config_loader=my_config_loader,
            logger=my_logger
        )

    向后兼容（不传参数时自动创建）：
        scheduler = FaultScheduler()
    """

    def __init__(self,
                 fetcher: Optional[IFetcher] = None,
                 config_loader: Optional[IConfigLoader] = None,
                 logger: Optional[ILogger] = None):
        """
        初始化 Fault 调度器（支持依赖注入）

        Args:
            fetcher: 数据抓取器实例（可选，不传则自动创建 FaultFetcher）
            config_loader: 配置加载器实例（可选，传递给父类）
            logger: 日志记录器实例（可选，传递给父类）
        """
        # 调用父类初始化（传入配置加载器和日志记录器）
        super().__init__(config_loader=config_loader, logger=logger)

        # 设置调度器标识
        self.scheduler_name = "FaultScheduler"
        self.data_type = "故障数据"

        # 依赖注入：使用传入的 fetcher 或自动创建
        print("\n" + "="*60)
        print("🔧 初始化 Fault 调度器")
        print("="*60)

        if fetcher is not None:
            self.fault_fetcher = fetcher
            print("✅ 使用注入的 Fetcher")
        else:
            # 向后兼容：自动创建 FaultFetcher
            self.fault_fetcher = FaultFetcher()
            print("✅ FaultFetcher 已自动创建")

        self.fault_page = None
        print("💡 监控端口: 9333")
        print("="*60)

    def connect_browser(self):
        """
        连接到 Fault 浏览器（端口 9333）

        Returns:
            bool: 是否成功
        """
        print("\n🌐 连接浏览器 (端口 9333)...")

        try:
            self.fault_page = self.fault_fetcher.connect_browser()
            if not self.fault_page:
                print("❌ FaultFetcher 连接失败")
                return False
            print("✅ FaultFetcher 已连接")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            self.log(f"连接浏览器失败: {e}", "ERROR")
            return False

    def login(self):
        """
        执行登录

        Returns:
            bool: 是否成功
        """
        print("\n🔑 执行智能登录...")

        try:
            if not self.fault_fetcher.smart_login(self.fault_page):
                print("❌ FaultFetcher 登录失败")
                return False
            print("✅ FaultFetcher 登录成功")
            return True
        except Exception as e:
            print(f"❌ 登录失败: {e}")
            self.log(f"登录失败: {e}", "ERROR")
            return False

    def fetch_data(self):
        """
        抓取故障数据

        Returns:
            bool: 是否成功
        """
        try:
            # 确保在正确的标签页上操作
            if not self.fault_fetcher.ensure_assigned_tab(self.fault_page):
                print("⚠️  标签页切换失败")
                return False

            # 获取配置的飞机列表
            aircraft_list = self.config.get('aircraft_list', [])
            target_date = self.fault_fetcher.get_today_date()

            # 执行抓取
            data = self.fault_fetcher.navigate_to_target_page(
                self.fault_page,
                target_date,
                aircraft_list
            )

            if data:
                # 保存数据
                csv_file = self.fault_fetcher.save_to_csv(
                    data,
                    filename=f"fault_data_{target_date}.csv"
                )

                if csv_file:
                    print(f"✅ 故障数据抓取成功")
                    print(f"📄 文件路径: {csv_file}")
                    self.log(f"故障数据抓取成功: {csv_file}", "SUCCESS")
                    return True
                else:
                    print("❌ 保存失败")
                    self.log("保存故障数据失败", "ERROR")
                    return False
            else:
                print("❌ 未提取到数据")
                self.log("未提取到故障数据", "ERROR")
                return False

        except Exception as e:
            print(f"❌ 故障数据抓取出错: {e}")
            self.log(f"故障数据抓取出错: {e}", "ERROR")
            return False

    def get_check_interval(self) -> timedelta:
        """
        获取检查间隔（每5分钟）

        Returns:
            timedelta: 5分钟
        """
        return timedelta(minutes=5)


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🔧 故障数据调度器")
    print("="*60)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    scheduler = FaultScheduler()

    # 检查命令行参数
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        # 交互式模式（预留，暂不实现）
        print("⚠️ 交互式模式暂不支持")
    else:
        # 调度模式
        try:
            scheduler.run()
        except KeyboardInterrupt:
            print("\n\n⚠️ 收到中断信号，正在退出...")
        except Exception as e:
            print(f"\n❌ 系统错误: {e}")
            scheduler.log(f"系统错误: {e}", "ERROR")


if __name__ == "__main__":
    main()

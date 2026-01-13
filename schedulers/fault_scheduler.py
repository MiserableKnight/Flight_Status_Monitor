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
        抓取故障数据（优化版：先判断再写入）

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

            # 执行抓取（数据在内存中，尚未写入磁盘）
            data = self.fault_fetcher.navigate_to_target_page(
                self.fault_page,
                target_date,
                aircraft_list
            )

            if data is None:
                print("❌ 未提取到数据")
                self.log("未提取到故障数据", "ERROR")
                return False

            # 数据为空的情况
            if len(data) == 0:
                print("ℹ️ 当前无故障记录")

                # 检查之前是否有故障（避免重复写空文件）
                last_count = self._load_last_fault_count(target_date)
                if last_count == 0:
                    print("   ⏭️ 之前也无故障记录，跳过写入")
                    return True

                print(f"   📝 之前有 {last_count} 条故障，现在清空，需要更新")
                # 继续写入，记录清空状态

            current_count = len(data)

            # 🎯 优化核心：先在内存中对比数据量
            print(f"\n📊 数据量对比：")
            last_count = self._load_last_fault_count(target_date)
            print(f"   上次: {last_count} 条")
            print(f"   本次: {current_count} 条")

            if current_count == last_count:
                print(f"\n   ⏭️ 数据量无变化，跳过文件写入和邮件发送")
                self.log(f"故障数据量未变化 ({current_count}条)，跳过更新", "INFO")
                return True

            print(f"\n   ✅ 检测到数据变化，开始写入文件")

            # 只有数据变化时才写入CSV（减少磁盘写入）
            csv_file = self.fault_fetcher.save_to_csv(
                data,
                filename=f"fault_data_{target_date}.csv"
            )

            if csv_file:
                print(f"✅ 故障数据抓取成功")
                print(f"📄 文件路径: {csv_file}")
                self.log(f"故障数据抓取成功: {csv_file} ({current_count}条)", "SUCCESS")

                # 发送邮件通知（内部会更新哈希记录）
                self._send_status_notification(target_date)

                return True
            else:
                print("❌ 保存失败")
                self.log("保存故障数据失败", "ERROR")
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

    def _load_last_fault_count(self, target_date: str) -> int:
        """
        读取上次保存的故障数据量

        Args:
            target_date: 目标日期

        Returns:
            int: 上次的故障数量，无记录返回-1
        """
        try:
            from pathlib import Path
            import json

            status_file = Path(__file__).parent.parent / 'data' / 'last_fault_email_status.json'

            if not status_file.exists():
                return -1  # 无历史记录

            with open(status_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 如果日期不匹配，返回-1（新的一天）
            if data.get('date') != target_date:
                return -1

            return data.get('fault_count', -1)

        except Exception as e:
            self.log(f"读取历史故障数量失败: {e}", "ERROR")
            return -1

    def _send_status_notification(self, target_date: str):
        """
        发送故障状态邮件通知

        Args:
            target_date: 目标日期字符串 (YYYY-MM-DD)
        """
        try:
            # 动态导入，避免循环依赖
            import sys
            import os
            from pathlib import Path

            # 添加项目根目录到路径
            project_root = Path(__file__).parent.parent
            sys.path.insert(0, str(project_root))

            # 导入通知模块
            from processors.fault_status_monitor import monitor_fault_status

            print("\n📧 检查故障状态变化...")
            success = monitor_fault_status(target_date)

            if success:
                print("✅ 故障状态监控完成")
            else:
                print("⚠️ 故障状态监控失败")

        except Exception as e:
            self.log(f"发送故障状态通知失败: {e}", "ERROR")
            print(f"⚠️ 邮件通知执行失败: {e}")


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

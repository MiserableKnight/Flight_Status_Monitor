"""
航段数据调度器

专门管理航段数据的监控：
- 连接端口 9222
- 每分钟检查一次
- 航段状态变化通知
- 支持依赖注入
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.flight_tracker import FlightTracker
from exceptions.auth import LoginFailedError
from exceptions.connection import BrowserConnectionError
from exceptions.data import DataExtractionError, DataFileError
from exceptions.notification import EmailSendError
from fetchers.leg_fetcher import LegFetcher
from interfaces.interfaces import IConfigLoader, IFetcher, ILogger
from notifiers.task_notifier import TaskNotifier

from .base_scheduler import BaseScheduler


class LegScheduler(BaseScheduler):
    """
    航段数据调度器

    继承自 BaseScheduler，专门负责航段数据的监控
    支持依赖注入，提高可测试性和可维护性

    使用依赖注入：
        scheduler = LegScheduler(
            fetcher=MyLegFetcher(),
            config_loader=my_config_loader,
            logger=my_logger
        )

    向后兼容（不传参数时自动创建）：
        scheduler = LegScheduler()
    """

    def __init__(
        self,
        fetcher: Optional[IFetcher] = None,
        config_loader: Optional[IConfigLoader] = None,
        logger: Optional[ILogger] = None,
    ):
        """
        初始化 Leg 调度器（支持依赖注入）

        Args:
            fetcher: 数据抓取器实例（可选，不传则自动创建 LegFetcher）
            config_loader: 配置加载器实例（可选，传递给父类）
            logger: 日志记录器实例（可选，传递给父类）
        """
        # 调用父类初始化（传入配置加载器和日志记录器）
        super().__init__(config_loader=config_loader, logger=logger)

        # 设置调度器标识
        self.scheduler_name = "LegScheduler"
        self.data_type = "航段数据"

        # 初始化航班状态跟踪器
        aircraft_list = self.config.get("aircraft_list", [])
        self.flight_tracker = FlightTracker(monitored_aircraft=aircraft_list)

        # 初始化通知器（如果配置了Gmail）
        gmail_config = self.config.get("gmail", {})
        self.notifier = TaskNotifier(config=gmail_config) if gmail_config else None

        # 依赖注入：使用传入的 fetcher 或自动创建
        print("\n" + "=" * 60)
        print("🔧 初始化 Leg 调度器")
        print("=" * 60)

        if fetcher is not None:
            self.leg_fetcher = fetcher
            print("✅ 使用注入的 Fetcher")
        else:
            # 向后兼容：自动创建 LegFetcher
            self.leg_fetcher = LegFetcher()
            print("✅ LegFetcher 已自动创建")

        self.leg_page = None
        print("💡 监控端口: 9222")
        print("=" * 60)

    def connect_browser(self):
        """
        连接到 Leg 浏览器（端口 9222）

        Returns:
            bool: 是否成功
        """
        print("\n🌐 连接浏览器 (端口 9222)...")

        try:
            self.leg_page = self.leg_fetcher.connect_browser()
            if not self.leg_page:
                print("❌ LegFetcher 连接失败")
                return False
            print("✅ LegFetcher 已连接")
            return True
        except BrowserConnectionError as e:
            print(f"❌ 浏览器连接失败: {e}")
            self.log(f"浏览器连接失败: {e}", "ERROR")
            return False
        except (ConnectionError, OSError) as e:
            print(f"❌ 网络连接失败: {e}")
            self.log(f"网络连接失败: {e}", "ERROR")
            return False
        except Exception as e:
            print(f"❌ 连接失败: {type(e).__name__}: {e}")
            self.log(f"连接异常: {type(e).__name__}: {e}", "ERROR")
            return False

    def login(self):
        """
        执行登录

        Returns:
            bool: 是否成功
        """
        print("\n🔑 执行智能登录...")

        try:
            if not self.leg_fetcher.smart_login(self.leg_page):
                print("❌ LegFetcher 登录失败")
                return False
            print("✅ LegFetcher 登录成功")
            return True
        except LoginFailedError as e:
            print(f"❌ 登录失败: {e}")
            self.log(f"登录失败: {e}", "ERROR")
            return False
        except Exception as e:
            print(f"❌ 登录异常: {type(e).__name__}: {e}")
            self.log(f"登录异常: {type(e).__name__}: {e}", "ERROR")
            return False

    def get_page(self):
        """
        返回 Leg 调度器的页面对象

        实现基类的抽象方法，用于连接检测和自动重连

        Returns:
            ChromiumPage: self.leg_page
        """
        return self.leg_page

    def fetch_data(self):
        """
        抓取航段数据

        Returns:
            bool: 是否成功
        """
        try:
            # 获取配置的飞机列表
            aircraft_list = self.config.get("aircraft_list", [])
            target_date = self.leg_fetcher.get_today_date()

            # 执行抓取（传递飞机列表）
            data = self.leg_fetcher.navigate_to_target_page(
                self.leg_page, target_date, aircraft_list
            )

            if data:
                # 保存数据
                csv_file = self.leg_fetcher.save_to_csv(
                    data, filename=f"leg_data_{target_date}.csv"
                )

                if csv_file:
                    print("✅ 航段数据抓取成功")
                    print(f"📄 文件路径: {csv_file}")
                    self.log(f"航段数据抓取成功: {csv_file}", "SUCCESS")

                    # 更新数据时间戳（用于告警监控判断数据新鲜度）
                    self._update_data_timestamp()

                    # 更新 flight_tracker 状态
                    self._update_flight_tracker()

                    # 发送邮件通知
                    self._send_status_notification(target_date)

                    # 发送告警通知
                    self._send_alert_notification(target_date)

                    return True
                else:
                    print("❌ 保存失败")
                    self.log("保存航段数据失败", "ERROR")
                    return False
            else:
                print("❌ 未提取到数据")
                self.log("未提取到航段数据", "ERROR")
                return False

        except DataExtractionError as e:
            print(f"❌ 数据提取失败: {e}")
            self.log(f"数据提取失败: {e}", "ERROR")
            return False
        except DataFileError as e:
            print(f"❌ 文件操作失败: {e}")
            self.log(f"文件操作失败: {e}", "ERROR")
            return False
        except Exception as e:
            print(f"❌ 航段数据抓取出错: {type(e).__name__}: {e}")
            self.log(f"航段数据抓取出错: {type(e).__name__}: {e}", "ERROR")
            return False

    def get_check_interval(self) -> timedelta:
        """
        获取检查间隔（每分钟）

        Returns:
            timedelta: 1分钟
        """
        return timedelta(minutes=1)

    def _update_data_timestamp(self):
        """更新数据时间戳文件"""
        try:
            import json
            from pathlib import Path

            timestamp_file = Path("data/last_data_update.json")
            timestamp_file.parent.mkdir(parents=True, exist_ok=True)

            timestamp_data = {
                "last_update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "scheduler": "LegScheduler",
                "date": self.leg_fetcher.get_today_date(),
            }

            with open(timestamp_file, "w", encoding="utf-8") as f:
                json.dump(timestamp_data, f, ensure_ascii=False, indent=2)

            self.log(f"数据时间戳已更新: {timestamp_data['last_update_time']}")

        except OSError as e:
            self.log(f"更新数据时间戳失败: {e}", "ERROR")
        except Exception as e:
            self.log(f"更新数据时间戳异常: {type(e).__name__}: {e}", "ERROR")

    def _update_flight_tracker(self):
        """更新航班状态跟踪器"""
        try:
            import pandas as pd

            leg_data_file = Path("data/leg_data.csv")
            if leg_data_file.exists():
                df = pd.read_csv(leg_data_file)
                today = self.leg_fetcher.get_today_date()

                if "日期" in df.columns:
                    today_data = df[df["日期"] == today].to_dict("records")
                else:
                    self.log("CSV中缺少'日期'列", "ERROR")
                    today_data = []

                if today_data:
                    self.flight_tracker.update_from_latest_leg_data(today_data)
                    self.log(f"已更新flight_tracker状态，共{len(today_data)}条记录")

                    # 显示状态摘要
                    print(self.flight_tracker.get_status_summary())

        except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
            self.log(f"读取CSV失败: {e}", "ERROR")
        except OSError as e:
            self.log(f"文件操作失败: {e}", "ERROR")
        except Exception as e:
            self.log(f"更新flight_tracker异常: {type(e).__name__}: {e}", "ERROR")

    def _send_status_notification(self, target_date: str):
        """
        发送航段状态变化邮件通知

        Args:
            target_date: 目标日期字符串 (YYYY-MM-DD)
        """
        try:
            # 动态导入，避免循环依赖
            import sys
            from pathlib import Path

            # 添加项目根目录到路径
            project_root = Path(__file__).parent.parent
            sys.path.insert(0, str(project_root))

            # 导入通知模块
            from processors.leg_status_monitor import monitor_flight_status

            print("\n📧 检查状态变化...")
            success = monitor_flight_status(target_date)

            if success:
                print("✅ 状态监控完成")
            else:
                print("⚠️ 状态监控失败")

        except EmailSendError as e:
            self.log(f"邮件发送失败: {e}", "ERROR")
            print(f"⚠️ 邮件通知执行失败: {e}")
        except Exception as e:
            self.log(f"发送状态通知异常: {type(e).__name__}: {e}", "ERROR")
            print(f"⚠️ 邮件通知执行失败: {type(e).__name__}: {e}")

    def _send_alert_notification(self, target_date: str):
        """
        发送航段告警邮件通知

        Args:
            target_date: 目标日期字符串 (YYYY-MM-DD)
        """
        try:
            # 动态导入，避免循环依赖
            import sys
            from pathlib import Path

            # 添加项目根目录到路径
            project_root = Path(__file__).parent.parent
            sys.path.insert(0, str(project_root))

            # 导入告警监控模块
            from processors.leg_alert_monitor import monitor_leg_alerts

            print("\n⚠️ 检查告警条件...")
            success = monitor_leg_alerts(target_date)

            if success:
                print("✅ 告警监控完成")
            else:
                print("⚠️ 告警监控失败")

        except EmailSendError as e:
            self.log(f"告警邮件发送失败: {e}", "ERROR")
            print(f"⚠️ 告警通知执行失败: {e}")
        except Exception as e:
            self.log(f"发送告警通知异常: {type(e).__name__}: {e}", "ERROR")
            print(f"⚠️ 告警通知执行失败: {type(e).__name__}: {e}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🛫 航段数据调度器")
    print("=" * 60)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    scheduler = LegScheduler()

    # 检查命令行参数
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
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

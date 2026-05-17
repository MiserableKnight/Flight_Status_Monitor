"""
调度器基类

所有调度器的通用逻辑：
- 配置加载
- 时间解析
- 统计数据
- 日志记录
- 主循环框架
- 依赖注入支持
"""

import os
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from config.constants import RETRY_INTERVAL_SECONDS

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from DrissionPage.errors import PageDisconnectedError

from config.config_loader import load_config
from core.logger import get_logger
from exceptions.auth import LoginFailedError, SessionExpiredError
from exceptions.connection import BrowserConnectionError
from interfaces.interfaces import IConfigLoader, ILogger


class BaseScheduler(ABC):
    """
    调度器基类（抽象类）

    核心功能：
    1. 支持依赖注入配置加载器和日志记录器
    2. 提供时间解析等工具方法
    3. 定义子类必须实现的方法接口
    4. 提供主循环框架

    使用依赖注入：
        scheduler = MyScheduler(
            config_loader=my_config_loader,
            logger=my_logger
        )

    向后兼容（不传参数时自动创建）：
        scheduler = MyScheduler()
    """

    def __init__(
        self, config_loader: Optional[IConfigLoader] = None, logger: Optional[ILogger] = None
    ):
        """
        初始化调度器（支持依赖注入）

        Args:
            config_loader: 配置加载器实例（可选，不传则自动创建）
            logger: 日志记录器实例（可选，不传则自动创建）
        """
        # 依赖注入：使用传入的实例或自动创建
        if config_loader is not None:
            self.config_loader = config_loader
        else:
            # 向后兼容：自动创建配置加载器
            self.config_loader = load_config()

        # 获取配置
        self.config = self.config_loader.get_all_config()

        # 依赖注入：使用传入的日志记录器或自动创建
        if logger is not None:
            self.log = logger
        else:
            # 向后兼容：自动创建日志记录器
            self.log = get_logger()

        # 调度器名称（子类需要设置）
        self.scheduler_name = self.__class__.__name__
        self.data_type = "Unknown"

        # 统计数据（子类可以扩展）
        self.stats = {
            "fetch_count": 0,
            "success_count": 0,
            "failure_count": 0,
        }

        self.log(f"{self.scheduler_name} 初始化完成")

    # ========== 抽象方法（子类必须实现） ==========

    @abstractmethod
    def connect_browser(self):
        """
        连接到浏览器

        子类需要实现具体的连接逻辑：
        - LegScheduler: 连接端口 9222
        - FaultScheduler: 连接端口 9333
        """
        pass

    @abstractmethod
    def login(self):
        """
        执行登录

        子类需要实现具体的登录逻辑
        """
        pass

    @abstractmethod
    def fetch_data(self):
        """
        抓取数据

        子类需要实现具体的数据抓取逻辑

        Returns:
            bool: 是否成功
        """
        pass

    @abstractmethod
    def get_check_interval(self) -> timedelta:
        """
        获取检查间隔

        Returns:
            timedelta: 检查间隔时间
        """
        pass

    @abstractmethod
    def get_page(self):
        """
        获取当前调度器的页面对象

        子类需要实现，返回各自的 page 对象：
        - LegScheduler: return self.leg_page
        - FaultScheduler: return self.fault_page

        Returns:
            ChromiumPage: 页面对象
        """
        pass

    # ========== 容错方法 ==========

    def _is_page_alive(self, page):
        """
        检测页面连接是否存活

        Args:
            page: ChromiumPage 对象

        Returns:
            bool: True=连接正常, False=连接断开
        """
        if page is None:
            return False
        try:
            # 尝试获取页面URL（轻量级检测）
            _ = page.url
            return True
        except (AttributeError, ConnectionError, OSError, PageDisconnectedError) as e:
            # 具体捕获页面连接相关的异常（含 DrissionPage 页面断连）
            self.log(f"页面连接检测失败: {type(e).__name__}", "DEBUG")
            return False

    def _reconnect_browser(self, max_retries=3):
        """
        重新连接浏览器

        利用子类实现的 connect_browser() 和 login() 抽象方法

        优化：
        - 重连前先清理旧的浏览器连接对象
        - 适用于电脑休眠后唤醒的场景（Chrome进程还在，但连接已断开）

        Args:
            max_retries: 最大重试次数（默认3次）

        Returns:
            bool: True=重连成功, False=重连失败
        """
        # 第一步：清理旧的浏览器连接
        print("\n🧹 清理旧的浏览器连接...")
        try:
            # 导入BaseFetcher来访问类级别的_browsers字典
            from fetchers.base_fetcher import BaseFetcher

            # 清空所有旧的浏览器连接
            if BaseFetcher._browsers:
                cleared_ports = list(BaseFetcher._browsers.keys())
                BaseFetcher._browsers.clear()
                print(f"   ✅ 已清理端口: {cleared_ports}")
            else:
                print("   ℹ️ 无旧连接需要清理")
        except (ImportError, AttributeError) as e:
            print(f"   ⚠️ 清理旧连接时出错: {e}")
            self.log(f"清理旧连接失败: {e}", "WARNING")

        for attempt in range(max_retries):
            try:
                print("\n" + "=" * 60)
                print(f"🔄 尝试重连浏览器... ({attempt + 1}/{max_retries})")
                print("=" * 60)

                # 重新连接
                if not self.connect_browser():
                    print(f"❌ 连接失败 ({attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(RETRY_INTERVAL_SECONDS)
                        continue
                    return False

                # 重新登录
                if not self.login():
                    print(f"❌ 登录失败 ({attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(RETRY_INTERVAL_SECONDS)
                        continue
                    return False

                print("✅ 重连成功")
                print("=" * 60)
                return True

            except BrowserConnectionError as e:
                # 浏览器连接异常
                print(f"❌ 浏览器连接异常 ({attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(RETRY_INTERVAL_SECONDS)
                else:
                    print("❌ 重连失败，已达最大重试次数")
                    self.log(f"重连失败: {e}", "ERROR")
                    return False
            except LoginFailedError as e:
                # 登录失败异常
                print(f"❌ 登录失败 ({attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(RETRY_INTERVAL_SECONDS)
                else:
                    print("❌ 重连失败（登录），已达最大重试次数")
                    self.log(f"登录失败: {e}", "ERROR")
                    return False
            except SessionExpiredError as e:
                # 会话过期异常
                print(f"❌ 会话过期 ({attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(RETRY_INTERVAL_SECONDS)
                else:
                    print("❌ 重连失败（会话过期），已达最大重试次数")
                    self.log(f"会话过期: {e}", "ERROR")
                    return False
            except (ConnectionError, OSError) as e:
                # 网络连接异常
                print(f"❌ 网络连接异常 ({attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(RETRY_INTERVAL_SECONDS)
                else:
                    print("❌ 重连失败（网络），已达最大重试次数")
                    self.log(f"网络连接失败: {e}", "ERROR")
                    return False
            except Exception as e:
                # 其他未预期的异常
                print(f"❌ 未知异常 ({attempt + 1}/{max_retries}): {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(RETRY_INTERVAL_SECONDS)
                else:
                    print("❌ 重连失败，已达最大重试次数")
                    self.log(f"重连失败(未知错误): {e}", "ERROR")
                    import traceback

                    traceback.print_exc()
                    return False

        return False

    def _fetch_with_reconnect(self):
        """
        带重连容错的数据抓取

        自动检测连接状态，断开时自动重连

        Returns:
            bool: True=抓取成功, False=抓取失败
        """
        # 获取当前页面对象
        page = self.get_page()

        # 检测连接状态
        if not self._is_page_alive(page):
            print("\n⚠️ 检测到连接断开")
            print("🔄 触发自动重连...")

            # 尝试重连
            if not self._reconnect_browser():
                print("❌ 自动重连失败，本次抓取跳过")
                self.log("自动重连失败", "ERROR")
                return False

            print("✅ 重连成功，继续本次抓取\n")

        # 执行实际的抓取逻辑（由子类实现）
        return self.fetch_data()

    # ========== 工具方法 ==========

    def parse_time(self, time_str: str) -> datetime:
        """
        解析时间字符串为今天的datetime对象

        Args:
            time_str: 时间字符串，格式 "HH:MM"

        Returns:
            datetime: 今天的datetime对象
        """
        today = datetime.now().date()
        hour, minute = map(int, time_str.split(":"))
        return datetime.combine(today, datetime.min.time()) + timedelta(hours=hour, minutes=minute)

    def update_stats(self, success: bool):
        """
        更新统计数据

        Args:
            success: 是否成功
        """
        self.stats["fetch_count"] += 1
        if success:
            self.stats["success_count"] += 1
        else:
            self.stats["failure_count"] += 1

    def print_stats(self):
        """打印统计信息"""
        print(f"\n📊 {self.data_type} 监控统计:")
        print(f"   - 总检查次数: {self.stats['fetch_count']}")
        print(f"   - 成功次数: {self.stats['success_count']}")
        print(f"   - 失败次数: {self.stats['failure_count']}")
        if self.stats["fetch_count"] > 0:
            success_rate = (self.stats["success_count"] / self.stats["fetch_count"]) * 100
            print(f"   - 成功率: {success_rate:.1f}%")

    # ========== 主循环框架 ==========

    def run(self):
        """
        主运行循环（模板方法模式）

        核心流程：
        1. 初始化（连接、登录）
        2. 等待到启动时间
        3. 循环监控
        4. 定期抓取数据
        """
        scheduler_config = self.config.get("scheduler", {})

        # 解析时间配置
        start_time = self.parse_time(scheduler_config.get("start_time", "06:00"))
        end_time = self.parse_time(scheduler_config.get("end_time", "23:59"))

        # 显示启动信息
        self._print_startup_info(scheduler_config, start_time, end_time)

        # ========== 初始化阶段 ==========
        if not self._initialize():
            print("❌ 初始化失败，退出")
            return

        # 等待到启动时间
        now = datetime.now()
        if start_time > now:
            print(f"\n⏰ 等待至 {start_time.strftime('%Y-%m-%d %H:%M:%S')}...")
            time.sleep((start_time - now).total_seconds())

        # ========== 主监控循环 ==========
        print(f"\n🚀 开始 {self.data_type} 智能监控...")

        last_check = None
        check_interval = self.get_check_interval()

        try:
            while True:
                now = datetime.now()

                # 检查是否超过结束时间
                if now > end_time:
                    print("\n🌙 已到达结束时间，停止运行")
                    self.log("到达结束时间，停止运行")
                    break

                # 检查是否需要执行抓取
                if last_check is None or (now - last_check) >= check_interval:
                    print(f"\n{'=' * 60}")
                    print(f"🔍 [{now.strftime('%H:%M:%S')}] 检查 {self.data_type} 状态...")
                    print("=" * 60)

                    # 执行抓取（带自动重连）
                    success = self._fetch_with_reconnect()
                    self.update_stats(success)

                    last_check = now

                    # 打印统计
                    self.print_stats()

                # 短暂休眠避免CPU占用过高
                time.sleep(10)

        except KeyboardInterrupt:
            print("\n\n⚠️ 收到中断信号，正在退出...")
            self.print_stats()
        except BrowserConnectionError as e:
            print(f"\n❌ 浏览器连接错误: {e}")
            self.log(f"浏览器连接错误: {e}", "ERROR")
            self.print_stats()
        except LoginFailedError as e:
            print(f"\n❌ 登录失败: {e}")
            self.log(f"登录失败: {e}", "ERROR")
            self.print_stats()
        except (ConnectionError, OSError) as e:
            print(f"\n❌ 网络连接错误: {e}")
            self.log(f"网络连接错误: {e}", "ERROR")
            self.print_stats()
        except Exception as e:
            print(f"\n❌ 系统错误: {type(e).__name__}: {e}")
            self.log(f"系统错误: {type(e).__name__}: {e}", "ERROR")
            self.print_stats()
            import traceback

            traceback.print_exc()

    def _initialize(self) -> bool:
        """
        初始化阶段（连接和登录）

        Returns:
            bool: 是否成功
        """
        print("\n🔧 初始化阶段...")

        # 连接浏览器
        if not self.connect_browser():
            print("❌ 浏览器连接失败")
            return False
        print("✅ 浏览器连接成功")

        # 登录
        if not self.login():
            print("❌ 登录失败")
            return False
        print("✅ 登录成功")

        return True

    def _print_startup_info(
        self, scheduler_config: Dict[str, Any], start_time: datetime, end_time: datetime
    ):
        """
        打印启动信息

        Args:
            scheduler_config: 调度器配置
            start_time: 开始时间
            end_time: 结束时间
        """
        print("\n" + "=" * 60)
        print(f"📋 {self.scheduler_name} 启动")
        print("=" * 60)
        print(
            f"⏰ 运行时间: {scheduler_config.get('start_time', '06:00')} - {scheduler_config.get('end_time', '23:59')}"
        )
        print(f"🎯 监控模式: {self.data_type} 智能监控")
        print(f"⏱️  检查间隔: {self.get_check_interval()}")
        print("=" * 60)

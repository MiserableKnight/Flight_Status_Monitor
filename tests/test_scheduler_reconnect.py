"""
BaseScheduler 重连机制单元测试

测试网络中断后的自动重连功能
"""

import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, PropertyMock, patch

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from interfaces.interfaces import IConfigLoader, ILogger
from schedulers.base_scheduler import BaseScheduler


class MockConfigLoader(IConfigLoader):
    """Mock 配置加载器"""

    def __init__(self):
        self.config = {
            "scheduler": {"start_time": "06:00", "end_time": "23:59"},
            "aircraft_list": ["B-1234", "B-5678"],
        }

    def get_all_config(self):
        return self.config

    def get_config(self, section):
        return self.config.get(section, {})


class MockLogger(ILogger):
    """Mock 日志记录器"""

    def __init__(self):
        self.logs = []

    def __call__(self, message, level="INFO"):
        self.logs.append({"message": message, "level": level})


class ConcreteScheduler(BaseScheduler):
    """具体的调度器实现（用于测试）"""

    def __init__(self, config_loader=None, logger=None):
        super().__init__(config_loader, logger)
        self.page = None  # 模拟的页面对象
        self.connect_count = 0
        self.login_count = 0
        self.fetch_count = 0

    def connect_browser(self):
        """模拟连接浏览器"""
        self.connect_count += 1
        self.page = Mock()
        self.page.url = "http://test.com"
        return True

    def login(self):
        """模拟登录"""
        self.login_count += 1
        return True

    def fetch_data(self):
        """模拟抓取数据"""
        self.fetch_count += 1
        return True

    def get_check_interval(self) -> timedelta:
        return timedelta(minutes=1)

    def get_page(self):
        """获取页面对象"""
        return self.page


class TestBaseSchedulerReconnect(unittest.TestCase):
    """测试 BaseScheduler 的重连机制"""

    def setUp(self):
        """每个测试前的设置"""
        self.mock_logger = MockLogger()
        self.mock_config = MockConfigLoader()

    def test_is_page_alive_with_valid_page(self):
        """测试检测页面存活（有效页面）"""
        scheduler = ConcreteScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 创建一个有效的页面 Mock
        mock_page = Mock()
        mock_page.url = "http://test.com"

        # 测试
        result = scheduler._is_page_alive(mock_page)

        # 验证
        self.assertTrue(result)

    def test_is_page_alive_with_none_page(self):
        """测试检测页面存活（None 页面）"""
        scheduler = ConcreteScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 测试 None 页面
        result = scheduler._is_page_alive(None)

        # 验证
        self.assertFalse(result)

    def test_is_page_alive_with_disconnected_page(self):
        """测试检测页面存活（断开连接的页面）"""
        scheduler = ConcreteScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 创建一个访问 url 时抛出异常的页面 Mock
        # 使用 PropertyMock 来正确模拟属性访问异常
        mock_page = Mock()
        type(mock_page).url = PropertyMock(side_effect=Exception("Connection lost"))

        # 测试
        result = scheduler._is_page_alive(mock_page)

        # 验证
        self.assertFalse(result)

    @patch("builtins.print")
    def test_reconnect_browser_success(self, mock_print):
        """测试重连浏览器成功"""
        scheduler = ConcreteScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 测试重连
        result = scheduler._reconnect_browser(max_retries=1)

        # 验证
        self.assertTrue(result)
        self.assertEqual(scheduler.connect_count, 1)
        self.assertEqual(scheduler.login_count, 1)

    def test_reconnect_browser_failure(self):
        """测试重连浏览器失败"""

        class FailingScheduler(BaseScheduler):
            """连接失败的调度器"""

            def __init__(self, config_loader=None, logger=None):
                super().__init__(config_loader, logger)
                self.attempt_count = 0

            def connect_browser(self):
                self.attempt_count += 1
                return False  # 总是失败

            def login(self):
                return False

            def fetch_data(self):
                return False

            def get_check_interval(self) -> timedelta:
                return timedelta(minutes=1)

            def get_page(self):
                return None

        scheduler = FailingScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 测试重连（3次重试）
        result = scheduler._reconnect_browser(max_retries=3)

        # 验证
        self.assertFalse(result)
        self.assertEqual(scheduler.attempt_count, 3)

    @patch("builtins.print")
    @patch("time.sleep")
    def test_reconnect_browser_with_retry(self, mock_sleep, mock_print):
        """测试重连浏览器（带重试）"""

        class RetryScheduler(BaseScheduler):
            """前两次失败，第三次成功的调度器"""

            def __init__(self, config_loader=None, logger=None):
                super().__init__(config_loader, logger)
                self.attempt_count = 0

            def connect_browser(self):
                self.attempt_count += 1
                return self.attempt_count >= 3  # 第三次成功

            def login(self):
                return True

            def fetch_data(self):
                return False

            def get_check_interval(self) -> timedelta:
                return timedelta(minutes=1)

            def get_page(self):
                return None

        scheduler = RetryScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 测试重连
        result = scheduler._reconnect_browser(max_retries=3)

        # 验证
        self.assertTrue(result)
        self.assertEqual(scheduler.attempt_count, 3)
        # 验证调用了 sleep（重试间隔）
        self.assertGreaterEqual(mock_sleep.call_count, 2)

    @patch("builtins.print")
    def test_fetch_with_reconnect_when_page_alive(self, mock_print):
        """测试带重连的抓取（页面存活）"""
        scheduler = ConcreteScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 设置页面为存活状态
        mock_page = Mock()
        mock_page.url = "http://test.com"
        scheduler.page = mock_page

        # 测试抓取
        result = scheduler._fetch_with_reconnect()

        # 验证
        self.assertTrue(result)
        self.assertEqual(scheduler.fetch_count, 1)
        self.assertEqual(scheduler.connect_count, 0)  # 没有重连

    @patch("builtins.print")
    def test_fetch_with_reconnect_when_page_dead(self, mock_print):
        """测试带重连的抓取（页面断开）"""
        scheduler = ConcreteScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 设置页面为断开状态
        scheduler.page = None

        # 测试抓取
        result = scheduler._fetch_with_reconnect()

        # 验证
        self.assertTrue(result)
        self.assertEqual(scheduler.fetch_count, 1)
        self.assertEqual(scheduler.connect_count, 1)  # 重连了一次
        self.assertEqual(scheduler.login_count, 1)  # 重新登录了一次

    @patch("builtins.print")
    def test_fetch_with_reconnect_failure(self, mock_print):
        """测试带重连的抓取（重连失败）"""

        class FailingScheduler(BaseScheduler):
            """重连失败的调度器"""

            def __init__(self, config_loader=None, logger=None):
                super().__init__(config_loader, logger)

            def connect_browser(self):
                return False

            def login(self):
                return False

            def fetch_data(self):
                return False

            def get_check_interval(self) -> timedelta:
                return timedelta(minutes=1)

            def get_page(self):
                return None  # 页面断开

        scheduler = FailingScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 测试抓取
        result = scheduler._fetch_with_reconnect()

        # 验证
        self.assertFalse(result)

    @patch("builtins.print")
    @patch("fetchers.base_fetcher.BaseFetcher", autospec=True)
    def test_reconnect_clears_browser_cache(self, mock_base_fetcher, mock_print):
        """测试重连前清理浏览器缓存"""
        # 创建一个模拟的 _browsers 字典
        mock_browsers = {9222: "browser1", 9333: "browser2"}
        mock_base_fetcher._browsers = mock_browsers

        scheduler = ConcreteScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 测试重连
        result = scheduler._reconnect_browser(max_retries=1)

        # 验证浏览器缓存被清空
        self.assertEqual(len(mock_base_fetcher._browsers), 0)
        self.assertTrue(result)

    @patch("builtins.print")
    @patch("time.sleep", return_value=None)
    def test_reconnect_with_login_failure(self, mock_sleep, mock_print):
        """测试重连时登录失败"""

        class LoginFailureScheduler(BaseScheduler):
            """登录失败的调度器"""

            def __init__(self, config_loader=None, logger=None):
                super().__init__(config_loader, logger)
                self.connect_count = 0
                self.login_count = 0

            def connect_browser(self):
                self.connect_count += 1
                return True  # 连接成功

            def login(self):
                self.login_count += 1
                return False  # 登录失败

            def fetch_data(self):
                return False

            def get_check_interval(self) -> timedelta:
                return timedelta(minutes=1)

            def get_page(self):
                return None

        scheduler = LoginFailureScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 测试重连
        result = scheduler._reconnect_browser(max_retries=2)

        # 验证
        self.assertFalse(result)
        self.assertEqual(scheduler.connect_count, 2)  # 尝试连接2次
        self.assertEqual(scheduler.login_count, 2)  # 尝试登录2次


class TestBaseSchedulerUtilities(unittest.TestCase):
    """测试 BaseScheduler 的工具方法"""

    def setUp(self):
        """每个测试前的设置"""
        self.mock_logger = MockLogger()
        self.mock_config = MockConfigLoader()

    def test_parse_time(self):
        """测试时间解析"""
        scheduler = ConcreteScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 测试
        result = scheduler.parse_time("14:30")

        # 验证
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)
        self.assertEqual(result.second, 0)

    def test_update_stats_success(self):
        """测试更新统计数据（成功）"""
        scheduler = ConcreteScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 更新成功统计
        scheduler.update_stats(success=True)

        # 验证
        self.assertEqual(scheduler.stats["fetch_count"], 1)
        self.assertEqual(scheduler.stats["success_count"], 1)
        self.assertEqual(scheduler.stats["failure_count"], 0)

    def test_update_stats_failure(self):
        """测试更新统计数据（失败）"""
        scheduler = ConcreteScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 更新失败统计
        scheduler.update_stats(success=False)

        # 验证
        self.assertEqual(scheduler.stats["fetch_count"], 1)
        self.assertEqual(scheduler.stats["success_count"], 0)
        self.assertEqual(scheduler.stats["failure_count"], 1)

    def test_print_stats(self):
        """测试打印统计信息"""
        scheduler = ConcreteScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 设置一些统计数据
        scheduler.stats = {"fetch_count": 10, "success_count": 8, "failure_count": 2}

        # 测试打印（不会抛出异常即可）
        try:
            scheduler.print_stats()
        except Exception as e:
            self.fail(f"print_stats() raised an exception: {e}")


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)

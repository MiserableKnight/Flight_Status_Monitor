"""
网络弹性测试

测试网络中断、浏览器连接断开等异常场景的处理
"""

import os
import sys
import unittest
from datetime import timedelta
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


class ResilientScheduler(BaseScheduler):
    """用于测试的弹性调度器"""

    def __init__(
        self,
        config_loader=None,
        logger=None,
        connect_succeeds=True,
        login_succeeds=True,
        fetch_succeeds=True,
        page_alive=True,
    ):
        super().__init__(config_loader, logger)
        self.page = None
        self.connect_succeeds = connect_succeeds
        self.login_succeeds = login_succeeds
        self.fetch_succeeds = fetch_succeeds
        self.page_alive = page_alive
        self.connect_call_count = 0
        self.login_call_count = 0
        self.fetch_call_count = 0

    def connect_browser(self):
        """模拟连接浏览器"""
        self.connect_call_count += 1
        if self.connect_succeeds:
            self.page = Mock()
            self.page.url = "http://test.com"
            return self.page
        return None

    def login(self):
        """模拟登录"""
        self.login_call_count += 1
        return self.login_succeeds

    def fetch_data(self):
        """模拟抓取数据"""
        self.fetch_call_count += 1
        return self.fetch_succeeds

    def get_check_interval(self) -> timedelta:
        return timedelta(minutes=1)

    def get_page(self):
        """获取页面对象"""
        return self.page


class TestNetworkResilience(unittest.TestCase):
    """测试网络弹性场景"""

    def setUp(self):
        """每个测试前的设置"""
        self.mock_logger = MockLogger()
        self.mock_config = MockConfigLoader()

    @patch("builtins.print")
    def test_page_alive_then_disconnects(self, mock_print):
        """测试页面存活然后断开"""
        # 创建调度器
        scheduler = ResilientScheduler(
            config_loader=self.mock_config,
            logger=self.mock_logger,
            connect_succeeds=True,
            login_succeeds=True,
            fetch_succeeds=True,
        )

        # 初始状态：页面存活
        scheduler.page = Mock()
        scheduler.page.url = "http://test.com"

        # 测试页面存活
        self.assertTrue(scheduler._is_page_alive(scheduler.page))

        # 模拟断开：访问url时抛出异常
        # 使用 PropertyMock 来正确模拟属性访问异常
        type(scheduler.page).url = PropertyMock(side_effect=Exception("Connection lost"))

        # 测试页面断开
        self.assertFalse(scheduler._is_page_alive(scheduler.page))

    @patch("builtins.print")
    @patch("time.sleep", return_value=None)
    def test_automatic_reconnect_on_disconnect(self, mock_sleep, mock_print):
        """测试检测到断开时自动重连"""
        # 创建调度器（初始状态页面存活）
        scheduler = ResilientScheduler(
            config_loader=self.mock_config,
            logger=self.mock_logger,
            connect_succeeds=True,
            login_succeeds=True,
            fetch_succeeds=True,
        )

        # 初始连接
        scheduler.connect_browser()

        # 模拟页面断开
        type(scheduler.page).url = PropertyMock(side_effect=Exception("Connection lost"))

        # 执行带重连的抓取
        result = scheduler._fetch_with_reconnect()

        # 验证
        self.assertTrue(result)
        self.assertEqual(scheduler.connect_call_count, 2)  # 初始连接 + 重连
        self.assertEqual(scheduler.login_call_count, 1)  # 只在重连时登录

    @patch("builtins.print")
    @patch("time.sleep", return_value=None)
    def test_reconnect_fails_then_succeeds(self, mock_sleep, mock_print):
        """测试重连失败然后成功"""
        # 创建调度器（第一次连接失败，第二次成功）
        scheduler = ResilientScheduler(
            config_loader=self.mock_config,
            logger=self.mock_logger,
            connect_succeeds=True,
            login_succeeds=True,
            fetch_succeeds=True,
        )

        # 初始连接
        scheduler.connect_browser()

        # 模拟页面断开
        type(scheduler.page).url = PropertyMock(side_effect=Exception("Connection lost"))

        # 执行带重连的抓取
        result = scheduler._fetch_with_reconnect()

        # 验证
        self.assertTrue(result)

    @patch("builtins.print")
    @patch("time.sleep", return_value=None)
    def test_multiple_reconnect_attempts(self, mock_sleep, mock_print):
        """测试多次重连尝试"""

        # 创建一个连接间歇性失败的调度器
        class IntermittentScheduler(ResilientScheduler):
            """间歇性失败的调度器"""

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.attempt_number = 0

            def connect_browser(self):
                """前两次失败，第三次成功"""
                self.attempt_number += 1
                if self.attempt_number >= 3:
                    self.page = Mock()
                    self.page.url = "http://test.com"
                    return self.page
                return None

        scheduler = IntermittentScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 测试重连（需要3次尝试）
        result = scheduler._reconnect_browser(max_retries=3)

        # 验证
        self.assertTrue(result)
        self.assertEqual(scheduler.attempt_number, 3)

    @patch("builtins.print")
    @patch("time.sleep", return_value=None)
    def test_reconnect_exhausts_retries(self, mock_sleep, mock_print):
        """测试重连耗尽所有重试次数"""
        # 创建一个总是失败的调度器
        scheduler = ResilientScheduler(
            config_loader=self.mock_config,
            logger=self.mock_logger,
            connect_succeeds=False,
            login_succeeds=False,
        )

        # 测试重连（3次重试都失败）
        result = scheduler._reconnect_browser(max_retries=3)

        # 验证
        self.assertFalse(result)
        self.assertEqual(scheduler.connect_call_count, 3)

    @patch("builtins.print")
    def test_fetch_succeeds_without_reconnect(self, mock_print):
        """测试页面存活时直接抓取，无需重连"""
        scheduler = ResilientScheduler(
            config_loader=self.mock_config,
            logger=self.mock_logger,
            connect_succeeds=True,
            fetch_succeeds=True,
        )

        # 初始连接
        scheduler.connect_browser()

        # 执行带重连的抓取（页面存活，不应触发重连）
        result = scheduler._fetch_with_reconnect()

        # 验证
        self.assertTrue(result)
        self.assertEqual(scheduler.connect_call_count, 1)  # 只有初始连接
        self.assertEqual(scheduler.fetch_call_count, 1)  # 抓取了一次

    @patch("builtins.print")
    @patch("time.sleep", return_value=None)
    def test_login_failure_during_reconnect(self, mock_sleep, mock_print):
        """测试重连时登录失败"""
        # 创建一个登录失败的调度器
        scheduler = ResilientScheduler(
            config_loader=self.mock_config,
            logger=self.mock_logger,
            connect_succeeds=True,
            login_succeeds=False,  # 登录失败
        )

        # 模拟页面断开
        scheduler.page = None

        # 执行带重连的抓取
        result = scheduler._fetch_with_reconnect()

        # 验证
        self.assertFalse(result)

    @patch("builtins.print")
    @patch("time.sleep", return_value=None)
    @patch("fetchers.base_fetcher.BaseFetcher", autospec=True)
    def test_browser_cache_cleared_on_reconnect(self, mock_base_fetcher, mock_sleep, mock_print):
        """测试重连时清理浏览器缓存"""
        # 创建模拟的浏览器缓存
        mock_browsers = {9222: "browser1", 9333: "browser2"}
        mock_base_fetcher._browsers = mock_browsers

        scheduler = ResilientScheduler(
            config_loader=self.mock_config,
            logger=self.mock_logger,
            connect_succeeds=True,
            login_succeeds=True,
        )

        # 模拟页面断开
        scheduler.page = None

        # 执行重连
        result = scheduler._reconnect_browser(max_retries=1)

        # 验证浏览器缓存被清空
        self.assertEqual(len(mock_base_fetcher._browsers), 0)
        self.assertTrue(result)

    @patch("builtins.print")
    @patch("time.sleep", return_value=None)
    def test_fetch_failure_after_reconnect(self, mock_sleep, mock_print):
        """测试重连成功但抓取失败"""
        scheduler = ResilientScheduler(
            config_loader=self.mock_config,
            logger=self.mock_logger,
            connect_succeeds=True,
            login_succeeds=True,
            fetch_succeeds=False,  # 抓取失败
        )

        # 模拟页面断开
        scheduler.page = None

        # 执行带重连的抓取
        result = scheduler._fetch_with_reconnect()

        # 验证
        self.assertFalse(result)
        self.assertEqual(scheduler.connect_call_count, 1)  # 重连了
        self.assertEqual(scheduler.fetch_call_count, 1)  # 抓取失败


class TestErrorRecoveryScenarios(unittest.TestCase):
    """测试错误恢复场景"""

    def setUp(self):
        """每个测试前的设置"""
        self.mock_logger = MockLogger()
        self.mock_config = MockConfigLoader()

    @patch("builtins.print")
    def test_connection_timeout_simulation(self, mock_print):
        """模拟连接超时场景"""

        class TimeoutScheduler(ResilientScheduler):
            """连接超时的调度器"""

            def connect_browser(self):
                """模拟连接超时"""
                self.connect_call_count += 1
                if self.connect_call_count < 2:
                    # 第一次超时
                    raise TimeoutError("Connection timeout")
                # 第二次成功
                self.page = Mock()
                self.page.url = "http://test.com"
                return self.page

        scheduler = TimeoutScheduler(config_loader=self.mock_config, logger=self.mock_logger)

        # 测试重连
        result = scheduler._reconnect_browser(max_retries=3)

        # 验证
        self.assertTrue(result)
        self.assertEqual(scheduler.connect_call_count, 2)

    @patch("builtins.print")
    @patch("time.sleep", return_value=None)
    def test_page_becomes_unresponsive(self, mock_sleep, mock_print):
        """测试页面变得无响应"""
        scheduler = ResilientScheduler(
            config_loader=self.mock_config,
            logger=self.mock_logger,
            connect_succeeds=True,
            login_succeeds=True,
            fetch_succeeds=True,
        )

        # 初始连接
        scheduler.connect_browser()

        # 模拟页面无响应（访问url抛出异常）
        type(scheduler.page).url = PropertyMock(side_effect=Exception("Page not responding"))

        # 执行带重连的抓取
        result = scheduler._fetch_with_reconnect()

        # 验证：应该检测到页面断开并重连
        self.assertTrue(result)
        self.assertEqual(scheduler.connect_call_count, 2)  # 初始 + 重连

    @patch("builtins.print")
    @patch("time.sleep", return_value=None)
    def test_intermittent_network_issues(self, mock_sleep, mock_print):
        """测试间歇性网络问题"""

        class IntermittentNetworkScheduler(ResilientScheduler):
            """间歇性网络问题的调度器"""

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fetch_attempts = 0

            def fetch_data(self):
                """间歇性失败"""
                self.fetch_attempts += 1
                # 奇数次失败，偶数次成功
                return self.fetch_attempts % 2 == 0

        scheduler = IntermittentNetworkScheduler(
            config_loader=self.mock_config,
            logger=self.mock_logger,
            connect_succeeds=True,
            login_succeeds=True,
        )

        # 初始连接
        scheduler.connect_browser()

        # 第一次抓取（失败）
        result1 = scheduler._fetch_with_reconnect()
        self.assertFalse(result1)

        # 第二次抓取（成功）
        result2 = scheduler._fetch_with_reconnect()
        self.assertTrue(result2)

    @patch("builtins.print")
    def test_concurrent_access_simulation(self, mock_print):
        """测试模拟并发访问（多个调度器使用同一端口）"""
        # 创建两个调度器，使用相同端口
        scheduler1 = ResilientScheduler(
            config_loader=self.mock_config,
            logger=self.mock_logger,
            connect_succeeds=True,
        )

        scheduler2 = ResilientScheduler(
            config_loader=self.mock_config,
            logger=self.mock_logger,
            connect_succeeds=True,
        )

        # 两个调度器分别连接
        page1 = scheduler1.connect_browser()
        page2 = scheduler2.connect_browser()

        # 验证
        self.assertIsNotNone(page1)
        self.assertIsNotNone(page2)

        # 验证页面存活
        self.assertTrue(scheduler1._is_page_alive(page1))
        self.assertTrue(scheduler2._is_page_alive(page2))


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)

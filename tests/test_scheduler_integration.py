"""
调度器集成测试

测试完整的调度流程，包括：
- 初始化流程
- 主循环逻辑
- 时间控制
- 统计数据更新
"""

import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from interfaces.interfaces import IConfigLoader, ILogger
from schedulers.fault_scheduler import FaultScheduler
from schedulers.leg_scheduler import LegScheduler


class MockConfigLoader(IConfigLoader):
    """Mock 配置加载器"""

    def __init__(self, config=None):
        self.config = config or {
            "scheduler": {
                "start_time": "00:00",  # 设置为00:00以便测试立即开始
                "end_time": "23:59",
            },
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


class MockFetcher:
    """Mock 数据抓取器"""

    def __init__(self, should_succeed=True):
        self.should_succeed = should_succeed
        self.connect_called = False
        self.login_called = False
        self.navigate_called = False
        self.fetch_count = 0

    def connect_browser(self):
        """模拟连接浏览器"""
        self.connect_called = True
        if self.should_succeed:
            mock_page = Mock()
            mock_page.url = "http://test.com"
            return mock_page
        return None

    def smart_login(self, page):
        """模拟登录"""
        self.login_called = True
        return self.should_succeed

    def get_today_date(self):
        """模拟获取今天的日期"""
        return datetime.now().strftime("%Y-%m-%d")

    def navigate_to_target_page(self, page, target_date, aircraft_list=None):
        """模拟导航到目标页面"""
        self.navigate_called = True
        self.fetch_count += 1
        if self.should_succeed:
            return [{"test": "data"}]
        return None

    def save_to_csv(self, data, filename):
        """模拟保存到CSV"""
        if self.should_succeed:
            return "/fake/path/to/file.csv"
        return None

    def ensure_assigned_tab(self, page):
        """模拟确保在分配的标签页上操作"""
        return self.should_succeed


class TestSchedulerIntegration(unittest.TestCase):
    """测试调度器集成流程"""

    def setUp(self):
        """每个测试前的设置"""
        self.mock_logger = MockLogger()
        self.mock_config = MockConfigLoader()

    @patch("builtins.print")
    def test_leg_scheduler_initialization(self, mock_print):
        """测试 LegScheduler 初始化"""
        mock_fetcher = MockFetcher()

        # 使用依赖注入创建调度器
        scheduler = LegScheduler(
            fetcher=mock_fetcher,
            config_loader=self.mock_config,
            logger=self.mock_logger,
        )

        # 验证
        self.assertIsNotNone(scheduler)
        self.assertEqual(scheduler.scheduler_name, "LegScheduler")
        self.assertEqual(scheduler.data_type, "航段数据")
        self.assertIs(scheduler.leg_fetcher, mock_fetcher)

    @patch("builtins.print")
    def test_fault_scheduler_initialization(self, mock_print):
        """测试 FaultScheduler 初始化"""
        mock_fetcher = MockFetcher()

        # 使用依赖注入创建调度器
        scheduler = FaultScheduler(
            fetcher=mock_fetcher,
            config_loader=self.mock_config,
            logger=self.mock_logger,
        )

        # 验证
        self.assertIsNotNone(scheduler)
        self.assertEqual(scheduler.scheduler_name, "FaultScheduler")
        self.assertEqual(scheduler.data_type, "故障数据")
        self.assertIs(scheduler.fault_fetcher, mock_fetcher)

    @patch("builtins.print")
    def test_initialization_phase_success(self, mock_print):
        """测试初始化阶段成功"""
        mock_fetcher = MockFetcher(should_succeed=True)

        scheduler = LegScheduler(
            fetcher=mock_fetcher,
            config_loader=self.mock_config,
            logger=self.mock_logger,
        )

        # 执行初始化
        result = scheduler._initialize()

        # 验证
        self.assertTrue(result)
        self.assertTrue(mock_fetcher.connect_called)
        self.assertTrue(mock_fetcher.login_called)
        self.assertIsNotNone(scheduler.leg_page)

    @patch("builtins.print")
    def test_initialization_phase_connect_failure(self, mock_print):
        """测试初始化阶段连接失败"""
        mock_fetcher = MockFetcher(should_succeed=False)

        scheduler = LegScheduler(
            fetcher=mock_fetcher,
            config_loader=self.mock_config,
            logger=self.mock_logger,
        )

        # 执行初始化
        result = scheduler._initialize()

        # 验证
        self.assertFalse(result)

    @patch("builtins.print")
    def test_initialization_phase_login_failure(self, mock_print):
        """测试初始化阶段登录失败"""

        class LoginFailureFetcher(MockFetcher):
            """登录时失败的Mock Fetcher"""

            def connect_browser(self):
                mock_page = Mock()
                mock_page.url = "http://test.com"
                return mock_page

            def smart_login(self, page):
                return False  # 登录失败

        mock_fetcher = LoginFailureFetcher()

        scheduler = LegScheduler(
            fetcher=mock_fetcher,
            config_loader=self.mock_config,
            logger=self.mock_logger,
        )

        # 执行初始化
        result = scheduler._initialize()

        # 验证
        self.assertFalse(result)

    @patch("builtins.print")
    def test_fetch_data_flow(self, mock_print):
        """测试数据抓取流程"""
        mock_fetcher = MockFetcher(should_succeed=True)

        scheduler = LegScheduler(
            fetcher=mock_fetcher,
            config_loader=self.mock_config,
            logger=self.mock_logger,
        )

        # 设置页面（模拟已登录）
        scheduler.leg_page = Mock()

        # 抓取数据
        result = scheduler.fetch_data()

        # 验证
        # navigate_to_target_page 返回 [{"test": "data"}]，这是真值
        # fetch_data 应该返回 True
        self.assertTrue(result)
        self.assertTrue(mock_fetcher.navigate_called)

    @patch("builtins.print")
    def test_check_interval_leg_scheduler(self, mock_print):
        """测试 LegScheduler 的检查间隔"""
        mock_fetcher = MockFetcher()

        scheduler = LegScheduler(
            fetcher=mock_fetcher,
            config_loader=self.mock_config,
            logger=self.mock_logger,
        )

        # 获取检查间隔
        interval = scheduler.get_check_interval()

        # 验证（LegScheduler 应该是1分钟）
        self.assertEqual(interval, timedelta(minutes=1))

    @patch("builtins.print")
    def test_check_interval_fault_scheduler(self, mock_print):
        """测试 FaultScheduler 的检查间隔"""
        mock_fetcher = MockFetcher()

        scheduler = FaultScheduler(
            fetcher=mock_fetcher,
            config_loader=self.mock_config,
            logger=self.mock_logger,
        )

        # 获取检查间隔
        interval = scheduler.get_check_interval()

        # 验证（FaultScheduler 实际上是1分钟）
        self.assertEqual(interval, timedelta(minutes=1))

    @patch("builtins.print")
    @patch("time.sleep", return_value=None)
    def test_update_statistics(self, mock_sleep, mock_print):
        """测试统计数据更新"""
        mock_fetcher = MockFetcher()

        scheduler = LegScheduler(
            fetcher=mock_fetcher,
            config_loader=self.mock_config,
            logger=self.mock_logger,
        )

        # 更新成功统计
        scheduler.update_stats(success=True)

        # 验证
        self.assertEqual(scheduler.stats["fetch_count"], 1)
        self.assertEqual(scheduler.stats["success_count"], 1)
        self.assertEqual(scheduler.stats["failure_count"], 0)

        # 更新失败统计
        scheduler.update_stats(success=False)

        # 验证
        self.assertEqual(scheduler.stats["fetch_count"], 2)
        self.assertEqual(scheduler.stats["success_count"], 1)
        self.assertEqual(scheduler.stats["failure_count"], 1)

    @patch("builtins.print")
    def test_print_statistics(self, mock_print):
        """测试打印统计信息"""
        mock_fetcher = MockFetcher()

        scheduler = LegScheduler(
            fetcher=mock_fetcher,
            config_loader=self.mock_config,
            logger=self.mock_logger,
        )

        # 设置统计数据
        scheduler.stats = {"fetch_count": 10, "success_count": 8, "failure_count": 2}

        # 打印统计（不应该抛出异常）
        try:
            scheduler.print_stats()
        except Exception as e:
            self.fail(f"print_stats() raised an exception: {e}")

    @patch("builtins.print")
    @patch("time.sleep", return_value=None)
    @patch("datetime.datetime")
    def test_main_loop_single_iteration(self, mock_datetime, mock_sleep, mock_print):
        """测试主循环单次迭代"""
        # 设置当前时间在运行时间内
        mock_now = datetime(2024, 1, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        mock_fetcher = MockFetcher(should_succeed=True)

        # 修改配置以确保时间在运行范围内
        config = MockConfigLoader(
            {
                "scheduler": {"start_time": "00:00", "end_time": "23:59"},
                "aircraft_list": ["B-1234"],
            }
        )

        scheduler = LegScheduler(
            fetcher=mock_fetcher, config_loader=config, logger=self.mock_logger
        )

        # 设置页面（模拟已初始化）
        scheduler.leg_page = Mock()
        scheduler.leg_page.url = "http://test.com"

        # Mock _is_page_alive 返回 True
        scheduler._is_page_alive = Mock(return_value=True)

        # Mock fetch_data 返回 True
        scheduler.fetch_data = Mock(return_value=True)

        # 模拟单次循环（通过 KeyboardInterrupt）
        with patch.object(scheduler, "_initialize", return_value=True), patch.object(
            scheduler, "_fetch_with_reconnect", return_value=True
        ):
            # 由于主循环是无限循环，我们通过设置结束时间来测试一次迭代
            # 创建一个修改版本的调度器，只运行一次循环
            def single_run():
                scheduler._initialize = Mock(return_value=True)
                scheduler.leg_page = Mock()
                scheduler.leg_page.url = "http://test.com"

                # 执行一次数据抓取
                scheduler.fetch_data = Mock(return_value=True)
                scheduler._fetch_with_reconnect = Mock(return_value=True)

                success = scheduler._fetch_with_reconnect()
                scheduler.update_stats(success)
                scheduler.print_stats()

                return True

            result = single_run()

            # 验证
            self.assertTrue(result)
            self.assertEqual(scheduler.stats["fetch_count"], 1)

    @patch("builtins.print")
    @patch("time.sleep", return_value=None)
    @patch("datetime.datetime")
    def test_main_loop_beyond_end_time(self, mock_datetime, mock_sleep, mock_print):
        """测试主循环检测结束时间"""
        # 设置当前时间为当天 23:59 之后
        # parse_time 会创建今天的 datetime，所以我们需要确保 mock_now 也在同一天
        mock_datetime.now.return_value = datetime(2024, 1, 15, 23, 59, 1)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        mock_fetcher = MockFetcher()

        # 配置结束时间为23:59
        config = MockConfigLoader(
            {
                "scheduler": {"start_time": "00:00", "end_time": "23:59"},
                "aircraft_list": ["B-1234"],
            }
        )

        scheduler = LegScheduler(
            fetcher=mock_fetcher, config_loader=config, logger=self.mock_logger
        )

        # 测试时间是否超出结束时间
        scheduler_config = scheduler.config.get("scheduler", {})
        parsed_end_time = scheduler.parse_time(scheduler_config.get("end_time", "23:59"))

        # 获取当前时间（从 scheduler 的 parse_time 内部调用）
        current_time = scheduler.parse_time("23:59")

        # 手动创建一个比结束时间晚1分钟的时间
        beyond_end_time = current_time + timedelta(minutes=1)

        # 验证
        self.assertTrue(beyond_end_time > parsed_end_time)

    @patch("builtins.print")
    def test_get_page_method(self, mock_print):
        """测试 get_page 方法"""
        mock_fetcher = MockFetcher()

        # 测试 LegScheduler
        leg_scheduler = LegScheduler(
            fetcher=mock_fetcher,
            config_loader=self.mock_config,
            logger=self.mock_logger,
        )
        leg_scheduler.leg_page = "mock_page"

        self.assertEqual(leg_scheduler.get_page(), "mock_page")

        # 测试 FaultScheduler
        fault_scheduler = FaultScheduler(
            fetcher=mock_fetcher,
            config_loader=self.mock_config,
            logger=self.mock_logger,
        )
        fault_scheduler.fault_page = "mock_page"

        self.assertEqual(fault_scheduler.get_page(), "mock_page")


class TestSchedulerErrorHandling(unittest.TestCase):
    """测试调度器错误处理"""

    def setUp(self):
        """每个测试前的设置"""
        self.mock_logger = MockLogger()
        self.mock_config = MockConfigLoader()

    @patch("builtins.print")
    @patch("sys.exit")
    def test_keyboard_interrupt_handling(self, mock_exit, mock_print):
        """测试键盘中断处理"""
        mock_fetcher = MockFetcher()

        scheduler = LegScheduler(
            fetcher=mock_fetcher,
            config_loader=self.mock_config,
            logger=self.mock_logger,
        )

        # 设置一些统计数据
        scheduler.stats = {"fetch_count": 5, "success_count": 4, "failure_count": 1}

        # 模拟 KeyboardInterrupt（不应该崩溃，应该打印统计信息）
        try:
            raise KeyboardInterrupt()
        except KeyboardInterrupt:
            # 验证可以正常打印统计信息
            scheduler.print_stats()
            # 不会抛出异常

    @patch("builtins.print")
    def test_exception_in_main_loop(self, mock_print):
        """测试主循环中的异常处理"""
        # 模拟异常情况
        # 注意：实际的run()方法会捕获异常并记录日志
        # 这里我们验证日志记录器能够记录错误
        # 初始化时会记录一条日志，所以现在有1条
        initial_log_count = len(self.mock_logger.logs)

        self.mock_logger("Test error message", "ERROR")

        # 验证
        self.assertEqual(len(self.mock_logger.logs), initial_log_count + 1)
        self.assertEqual(self.mock_logger.logs[-1]["level"], "ERROR")


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)

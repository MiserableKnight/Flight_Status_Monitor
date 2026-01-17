"""
依赖注入单元测试示例

演示如何使用依赖注入进行单元测试
"""

import os
import sys
import unittest
from datetime import timedelta
from unittest.mock import Mock

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入接口
from interfaces.interfaces import IConfigLoader, IFetcher, ILogger

# 导入实际的调度器类
from schedulers.fault_scheduler import FaultScheduler
from schedulers.leg_scheduler import LegScheduler


class MockFetcher(IFetcher):
    """
    Mock 数据抓取器

    实现 IFetcher 接口，用于测试
    """

    def __init__(self, should_succeed=True):
        self.should_succeed = should_succeed
        self.connect_called = False
        self.login_called = False
        self.navigate_called = False

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
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d")

    def navigate_to_target_page(self, page, target_date, aircraft_list):
        """模拟导航到目标页面"""
        self.navigate_called = True
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


class MockLogger(ILogger):
    """
    Mock 日志记录器

    实现 ILogger 接口，用于测试
    """

    def __init__(self):
        self.logs = []

    def __call__(self, message, level="INFO"):
        """记录日志"""
        self.logs.append({"message": message, "level": level})

    def get_logs(self):
        """获取所有日志"""
        return self.logs

    def clear_logs(self):
        """清除日志"""
        self.logs.clear()


class MockConfigLoader(IConfigLoader):
    """
    Mock 配置加载器

    实现 IConfigLoader 接口，用于测试
    """

    def __init__(self, config=None):
        self.config = config or {
            "scheduler": {"start_time": "06:00", "end_time": "23:59"},
            "aircraft_list": ["B-1234", "B-5678"],
        }

    def get_all_config(self):
        """获取所有配置"""
        return self.config

    def get_config(self, section):
        """获取特定部分的配置"""
        return self.config.get(section, {})


class TestFaultSchedulerWithDI(unittest.TestCase):
    """
    测试 FaultScheduler 使用依赖注入

    演示如何通过依赖注入进行单元测试
    """

    def test_initialization_with_di(self):
        """测试使用依赖注入初始化"""
        # 创建 Mock 依赖
        mock_fetcher = MockFetcher()
        mock_logger = MockLogger()
        mock_config = MockConfigLoader()

        # 使用依赖注入创建调度器
        scheduler = FaultScheduler(
            fetcher=mock_fetcher, config_loader=mock_config, logger=mock_logger
        )

        # 验证
        self.assertIsNotNone(scheduler)
        self.assertEqual(scheduler.scheduler_name, "FaultScheduler")
        self.assertEqual(scheduler.data_type, "故障数据")
        self.assertIs(scheduler.fault_fetcher, mock_fetcher)
        self.assertIs(scheduler.log, mock_logger)

    def test_initialization_without_di(self):
        """测试不使用依赖注入（向后兼容）"""
        # 不传递任何参数
        scheduler = FaultScheduler()

        # 验证
        self.assertIsNotNone(scheduler)
        self.assertEqual(scheduler.scheduler_name, "FaultScheduler")
        self.assertIsNotNone(scheduler.fault_fetcher)

    def test_connect_browser_success(self):
        """测试成功连接浏览器"""
        # 创建 Mock 依赖
        mock_fetcher = MockFetcher(should_succeed=True)
        mock_logger = MockLogger()
        mock_config = MockConfigLoader()

        # 创建调度器
        scheduler = FaultScheduler(
            fetcher=mock_fetcher, config_loader=mock_config, logger=mock_logger
        )

        # 测试连接
        result = scheduler.connect_browser()

        # 验证
        self.assertTrue(result)
        self.assertTrue(mock_fetcher.connect_called)
        self.assertIsNotNone(scheduler.fault_page)

    def test_connect_browser_failure(self):
        """测试连接浏览器失败"""
        # 创建会失败的 Mock
        mock_fetcher = MockFetcher(should_succeed=False)
        mock_logger = MockLogger()
        mock_config = MockConfigLoader()

        # 创建调度器
        scheduler = FaultScheduler(
            fetcher=mock_fetcher, config_loader=mock_config, logger=mock_logger
        )

        # 测试连接
        result = scheduler.connect_browser()

        # 验证
        self.assertFalse(result)

    def test_login_success(self):
        """测试成功登录"""
        # 创建 Mock 依赖
        mock_fetcher = MockFetcher(should_succeed=True)
        mock_logger = MockLogger()
        mock_config = MockConfigLoader()

        # 创建调度器
        scheduler = FaultScheduler(
            fetcher=mock_fetcher, config_loader=mock_config, logger=mock_logger
        )

        # 设置页面
        scheduler.fault_page = Mock()

        # 测试登录
        result = scheduler.login()

        # 验证
        self.assertTrue(result)
        self.assertTrue(mock_fetcher.login_called)

    def test_fetch_data_success(self):
        """测试成功抓取数据"""
        # 创建 Mock 依赖
        mock_fetcher = MockFetcher(should_succeed=True)
        mock_logger = MockLogger()
        mock_config = MockConfigLoader()

        # 创建调度器
        scheduler = FaultScheduler(
            fetcher=mock_fetcher, config_loader=mock_config, logger=mock_logger
        )

        # 设置页面
        scheduler.fault_page = Mock()

        # 测试抓取
        result = scheduler.fetch_data()

        # 验证
        self.assertTrue(result)
        self.assertTrue(mock_fetcher.navigate_called)

    def test_get_check_interval(self):
        """测试获取检查间隔"""
        mock_fetcher = MockFetcher()
        mock_logger = MockLogger()
        mock_config = MockConfigLoader()

        scheduler = FaultScheduler(
            fetcher=mock_fetcher, config_loader=mock_config, logger=mock_logger
        )

        interval = scheduler.get_check_interval()

        # 验证间隔是5分钟
        self.assertEqual(interval, timedelta(minutes=5))


class TestLegSchedulerWithDI(unittest.TestCase):
    """
    测试 LegScheduler 使用依赖注入
    """

    def test_initialization_with_di(self):
        """测试使用依赖注入初始化"""
        # 创建 Mock 依赖
        mock_fetcher = MockFetcher()
        mock_logger = MockLogger()
        mock_config = MockConfigLoader()

        # 使用依赖注入创建调度器
        scheduler = LegScheduler(
            fetcher=mock_fetcher, config_loader=mock_config, logger=mock_logger
        )

        # 验证
        self.assertIsNotNone(scheduler)
        self.assertEqual(scheduler.scheduler_name, "LegScheduler")
        self.assertEqual(scheduler.data_type, "航段数据")
        self.assertIs(scheduler.leg_fetcher, mock_fetcher)

    def test_get_check_interval(self):
        """测试获取检查间隔"""
        mock_fetcher = MockFetcher()
        mock_logger = MockLogger()
        mock_config = MockConfigLoader()

        scheduler = LegScheduler(
            fetcher=mock_fetcher, config_loader=mock_config, logger=mock_logger
        )

        interval = scheduler.get_check_interval()

        # 验证间隔是1分钟
        self.assertEqual(interval, timedelta(minutes=1))


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)

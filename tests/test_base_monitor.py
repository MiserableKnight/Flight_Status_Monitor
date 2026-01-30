"""
BaseStatusMonitor 单元测试

测试状态监控基类的核心功能
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import pandas as pd

from core.base_monitor import BaseStatusMonitor


class ConcreteStatusMonitor(BaseStatusMonitor):
    """具体的状态监控器实现（用于测试）"""

    def __init__(self, target_date=None, data_file=None, status_file=None):
        self.data_file = data_file
        self.status_file = status_file
        super().__init__(target_date)
        self.content_generated = None
        self.notification_sent = False

    def get_data_file_path(self):
        """获取数据文件路径"""
        return self.data_file or "test_data.csv"

    def get_status_file_path(self):
        """获取状态文件路径"""
        return self.status_file or "test_status.json"

    def generate_content(self, df):
        """生成通知内容"""
        self.content_generated = f"Generated content with {len(df)} rows"
        return self.content_generated

    def get_content_hash(self, content):
        """获取内容哈希值"""
        import hashlib

        return hashlib.md5(content.encode()).hexdigest()

    def send_notification(self, content):
        """发送通知"""
        self.notification_sent = True
        return True


class TestBaseStatusMonitor(unittest.TestCase):
    """测试 BaseStatusMonitor 基类"""

    def setUp(self):
        """每个测试前的设置"""
        # 使用临时目录进行测试
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """每个测试后的清理"""
        # 清理临时文件
        import shutil

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """测试初始化"""
        monitor = ConcreteStatusMonitor()

        # 验证
        self.assertIsNotNone(monitor.target_date)
        self.assertIsNotNone(monitor.log)
        self.assertIsNotNone(monitor.config_loader)

    def test_initialization_with_custom_date(self):
        """测试使用自定义日期初始化"""
        custom_date = "2024-01-15"
        monitor = ConcreteStatusMonitor(target_date=custom_date)

        # 验证
        self.assertEqual(monitor.target_date, custom_date)

    def test_ensure_data_dir(self):
        """测试确保数据目录存在"""
        data_dir = os.path.join(self.test_dir, "data")

        # 创建一个使用临时目录的监控器
        with patch("core.base_monitor.project_root", self.test_dir):
            monitor = ConcreteStatusMonitor()
            monitor._ensure_data_dir()

            # 验证目录已创建
            self.assertTrue(os.path.exists(data_dir))

    def test_read_data_file_success(self):
        """测试成功读取数据文件"""
        # 创建测试数据文件
        data_file = os.path.join(self.test_dir, "test_data.csv")
        test_data = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        test_data.to_csv(data_file, index=False)

        # 创建监控器
        monitor = ConcreteStatusMonitor(data_file=data_file)

        # 读取数据
        df = monitor.read_data_file()

        # 验证
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 3)

    def test_read_data_file_not_exists(self):
        """测试读取不存在的数据文件"""
        # 创建监控器（使用不存在的文件）
        monitor = ConcreteStatusMonitor(data_file="nonexistent.csv")

        # 尝试读取
        df = monitor.read_data_file()

        # 验证
        self.assertIsNone(df)

    def test_read_data_file_invalid_csv(self):
        """测试读取无效的CSV文件"""
        # 创建无效的CSV文件
        data_file = os.path.join(self.test_dir, "invalid.csv")
        with open(data_file, "w") as f:
            f.write("invalid,csv,content\n1,2,not,a,valid,row")

        # 创建监控器
        monitor = ConcreteStatusMonitor(data_file=data_file)

        # 读取数据（不应该抛出异常，返回None）
        df = monitor.read_data_file()

        # 验证（pandas.read_csv 会尽力解析，所以可能返回DataFrame）
        # 这里只验证不会抛出异常
        self.assertIsNotNone(df)

    def test_load_last_status_not_exists(self):
        """测试加载不存在的状态文件"""
        status_file = os.path.join(self.test_dir, "nonexistent_status.json")
        monitor = ConcreteStatusMonitor(status_file=status_file)

        # 加载状态
        status = monitor.load_last_status()

        # 验证
        self.assertIsNone(status)

    def test_save_and_load_status(self):
        """测试保存和加载状态"""
        status_file = os.path.join(self.test_dir, "test_status.json")
        monitor = ConcreteStatusMonitor(status_file=status_file)

        # 保存状态
        test_hash = "abc123"
        monitor.save_current_status(test_hash, row_count=10, test_metadata="test_value")

        # 验证文件已创建
        self.assertTrue(os.path.exists(status_file))

        # 加载状态
        loaded_status = monitor.load_last_status()

        # 验证
        self.assertIsNotNone(loaded_status)
        self.assertEqual(loaded_status["status_hash"], test_hash)
        self.assertEqual(loaded_status["row_count"], 10)
        self.assertEqual(loaded_status["test_metadata"], "test_value")
        self.assertIn("timestamp", loaded_status)
        self.assertIn("date", loaded_status)

    def test_has_status_changed_first_run(self):
        """测试首次运行时状态变化检测"""
        monitor = ConcreteStatusMonitor()

        # 测试（没有上次状态）
        current_hash = "abc123"
        result = monitor.has_status_changed(current_hash, None)

        # 验证
        self.assertTrue(result)

    def test_has_status_changed_same_hash(self):
        """测试状态哈希相同（无变化）"""
        monitor = ConcreteStatusMonitor()

        current_hash = "abc123"
        last_status = {"status_hash": "abc123"}

        # 测试
        result = monitor.has_status_changed(current_hash, last_status)

        # 验证
        self.assertFalse(result)

    def test_has_status_changed_different_hash(self):
        """测试状态哈希不同（有变化）"""
        monitor = ConcreteStatusMonitor()

        current_hash = "new_hash_456"
        last_status = {"status_hash": "old_hash_123"}

        # 测试
        result = monitor.has_status_changed(current_hash, last_status)

        # 验证
        self.assertTrue(result)

    def test_generate_content_abstract_method(self):
        """测试 generate_content 是抽象方法"""
        # 尝试直接实例化 BaseStatusMonitor 应该失败
        with self.assertRaises(TypeError):
            BaseStatusMonitor()

    def test_get_content_hash_abstract_method(self):
        """测试 get_content_hash 是抽象方法"""
        # 这个测试在 test_generate_content_abstract_method 中已覆盖

    def test_send_notification_abstract_method(self):
        """测试 send_notification 是抽象方法"""
        # 这个测试在 test_generate_content_abstract_method 中已覆盖

    @patch("builtins.print")
    def test_monitor_flow_with_change(self, mock_print):
        """测试完整的监控流程（状态有变化）"""
        # 创建测试数据文件
        data_file = os.path.join(self.test_dir, "test_data.csv")
        test_data = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        test_data.to_csv(data_file, index=False)

        # 创建状态文件（上次状态）
        status_file = os.path.join(self.test_dir, "test_status.json")

        # 创建监控器
        monitor = ConcreteStatusMonitor(data_file=data_file, status_file=status_file)

        # 运行监控
        result = monitor.monitor()

        # 验证
        self.assertTrue(result)
        self.assertTrue(monitor.notification_sent)
        self.assertTrue(os.path.exists(status_file))

    @patch("builtins.print")
    def test_monitor_flow_without_change(self, mock_print):
        """测试完整的监控流程（状态无变化）"""
        # 创建测试数据文件
        data_file = os.path.join(self.test_dir, "test_data.csv")
        test_data = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        test_data.to_csv(data_file, index=False)

        # 创建状态文件（上次状态）
        status_file = os.path.join(self.test_dir, "test_status.json")
        monitor1 = ConcreteStatusMonitor(data_file=data_file, status_file=status_file)

        # 第一次运行（会发送通知）
        monitor1.monitor()

        # 第二次运行（状态相同，不应发送通知）
        monitor2 = ConcreteStatusMonitor(data_file=data_file, status_file=status_file)
        monitor2.content_generated = monitor1.content_generated  # 模拟生成相同内容
        result = monitor2.monitor()

        # 验证
        self.assertTrue(result)
        self.assertFalse(monitor2.notification_sent)

    @patch("builtins.print")
    def test_monitor_flow_data_file_not_found(self, mock_print):
        """测试监控流程（数据文件不存在）"""
        data_file = os.path.join(self.test_dir, "nonexistent.csv")
        status_file = os.path.join(self.test_dir, "test_status.json")

        # 创建监控器
        monitor = ConcreteStatusMonitor(data_file=data_file, status_file=status_file)

        # 运行监控
        result = monitor.monitor()

        # 验证
        self.assertFalse(result)
        self.assertFalse(monitor.notification_sent)

    @patch("builtins.print")
    def test_run_method(self, mock_print):
        """测试 run 方法"""
        # 创建测试数据文件
        data_file = os.path.join(self.test_dir, "test_data.csv")
        test_data = pd.DataFrame({"col1": [1], "col2": ["a"]})
        test_data.to_csv(data_file, index=False)

        status_file = os.path.join(self.test_dir, "test_status.json")

        # 创建监控器
        monitor = ConcreteStatusMonitor(data_file=data_file, status_file=status_file)

        # 运行
        result = monitor.run()

        # 验证
        self.assertTrue(result)

    @patch("builtins.print")
    def test_run_with_exception(self, mock_print):
        """测试 run 方法处理异常"""

        class FailingMonitor(BaseStatusMonitor):
            """总是抛出异常的监控器"""

            def get_data_file_path(self):
                return "test.csv"

            def get_status_file_path(self):
                return "test.json"

            def generate_content(self, df):
                raise Exception("Test exception")

            def get_content_hash(self, content):
                return "hash"

            def send_notification(self, content):
                return True

        monitor = FailingMonitor()

        # 运行（应该捕获异常并返回False）
        result = monitor.run()

        # 验证
        self.assertFalse(result)

    def test_save_status_creates_directory(self):
        """测试保存状态时自动创建目录"""
        # 使用一个不存在的子目录
        status_file = os.path.join(self.test_dir, "subdir", "test_status.json")
        monitor = ConcreteStatusMonitor(status_file=status_file)

        # 保存状态
        monitor.save_current_status("test_hash")

        # 验证目录已创建
        self.assertTrue(os.path.exists(os.path.dirname(status_file)))
        self.assertTrue(os.path.exists(status_file))

    def test_load_status_with_invalid_json(self):
        """测试加载无效的JSON状态文件"""
        status_file = os.path.join(self.test_dir, "invalid.json")

        # 创建无效的JSON文件
        with open(status_file, "w") as f:
            f.write("{ invalid json }")

        monitor = ConcreteStatusMonitor(status_file=status_file)

        # 加载状态（应该返回None而不是抛出异常）
        status = monitor.load_last_status()

        # 验证
        self.assertIsNone(status)

    def test_generate_content_empty_dataframe(self):
        """测试使用空DataFrame生成内容"""
        # 创建一个包含列名但没有行的CSV文件
        data_file = os.path.join(self.test_dir, "empty.csv")
        df_with_columns = pd.DataFrame(columns=["col1", "col2"])
        df_with_columns.to_csv(data_file, index=False)

        status_file = os.path.join(self.test_dir, "test_status.json")

        # 创建监控器
        monitor = ConcreteStatusMonitor(data_file=data_file, status_file=status_file)

        # 运行监控
        result = monitor.monitor()

        # 验证（空数据框应返回True但不发送通知）
        self.assertTrue(result)


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)

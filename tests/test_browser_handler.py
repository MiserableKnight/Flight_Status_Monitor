"""
BrowserHandler 单元测试

测试浏览器连接管理功能
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.browser_handler import BrowserHandler


class TestBrowserHandler(unittest.TestCase):
    """测试 BrowserHandler 类"""

    def setUp(self):
        """每个测试前的设置"""
        self.user_data_path = "test_user_data"
        self.local_port = 9222

    def tearDown(self):
        """每个测试后的清理"""
        # 清理任何创建的测试文件
        pass

    @patch("core.browser_handler.ChromiumPage")
    @patch("core.browser_handler.ChromiumOptions")
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_connect_success(self, mock_makedirs, mock_exists, mock_co_class, mock_page_class):
        """测试成功连接到浏览器"""
        # 设置 Mock
        mock_exists.return_value = True  # 模拟 user_data_path 存在

        mock_co = Mock()
        mock_co_class.return_value = mock_co

        mock_page = Mock()
        mock_page_class.return_value = mock_page

        # 创建 handler 并连接
        handler = BrowserHandler(user_data_path=self.user_data_path, local_port=self.local_port)
        result = handler.connect()

        # 验证
        self.assertTrue(result)
        self.assertIs(handler.page, mock_page)

        # 验证 ChromiumOptions 配置
        mock_co.set_user_data_path.assert_called_once_with(self.user_data_path)
        mock_co.set_local_port.assert_called_once_with(self.local_port)

        # 验证 ChromiumPage 创建
        mock_page_class.assert_called_once_with(mock_co)

    @patch("core.browser_handler.ChromiumPage")
    @patch("core.browser_handler.ChromiumOptions")
    @patch("os.makedirs")
    def test_connect_with_exception(self, mock_makedirs, mock_co_class, mock_page_class):
        """测试连接时发生异常"""
        # 设置 Mock 抛出异常
        mock_page_class.side_effect = Exception("Connection failed")

        # 创建 handler 并尝试连接
        handler = BrowserHandler(user_data_path=self.user_data_path, local_port=self.local_port)
        result = handler.connect()

        # 验证
        self.assertFalse(result)
        self.assertIsNone(handler.page)

    @patch("core.browser_handler.ChromiumPage")
    @patch("core.browser_handler.ChromiumOptions")
    @patch("os.makedirs")
    def test_connect_without_user_data_path(self, mock_makedirs, mock_co_class, mock_page_class):
        """测试不提供 user_data_path 时的连接"""
        # 设置 Mock
        mock_co = Mock()
        mock_co_class.return_value = mock_co

        mock_page = Mock()
        mock_page_class.return_value = mock_page

        # 创建 handler（不提供 user_data_path）
        handler = BrowserHandler(local_port=self.local_port)
        result = handler.connect()

        # 验证
        self.assertTrue(result)
        # 验证没有调用 set_user_data_path（因为路径不存在或未提供）
        mock_co.set_user_data_path.assert_not_called()

    def test_get_page_when_connected(self):
        """测试获取页面对象（已连接状态）"""
        handler = BrowserHandler(local_port=self.local_port)
        mock_page = Mock()

        handler.page = mock_page

        # 获取页面
        result = handler.get_page()

        # 验证
        self.assertIs(result, mock_page)

    def test_get_page_when_not_connected(self):
        """测试获取页面对象（未连接状态）"""
        handler = BrowserHandler(local_port=self.local_port)

        # 获取页面（未连接）
        result = handler.get_page()

        # 验证
        self.assertIsNone(result)

    def test_is_connected_true(self):
        """测试检查连接状态（已连接）"""
        handler = BrowserHandler(local_port=self.local_port)
        handler.page = Mock()

        # 检查连接
        result = handler.is_connected()

        # 验证
        self.assertTrue(result)

    def test_is_connected_false(self):
        """测试检查连接状态（未连接）"""
        handler = BrowserHandler(local_port=self.local_port)

        # 检查连接
        result = handler.is_connected()

        # 验证
        self.assertFalse(result)

    def test_disconnect_when_connected(self):
        """测试断开连接（已连接状态）"""
        handler = BrowserHandler(local_port=self.local_port)
        handler.page = Mock()

        # 断开连接
        handler.disconnect()

        # 验证
        self.assertIsNone(handler.page)

    def test_disconnect_when_not_connected(self):
        """测试断开连接（未连接状态）"""
        handler = BrowserHandler(local_port=self.local_port)

        # 断开连接（不会有任何操作）
        handler.disconnect()

        # 验证
        self.assertIsNone(handler.page)

    @patch("core.browser_handler.ChromiumPage")
    @patch("core.browser_handler.ChromiumOptions")
    @patch("os.makedirs")
    def test_multiple_connections_same_port(self, mock_makedirs, mock_co_class, mock_page_class):
        """测试同一端口的多次连接"""
        # 设置 Mock
        mock_co = Mock()
        mock_co_class.return_value = mock_co

        mock_page1 = Mock()
        mock_page2 = Mock()
        mock_page_class.side_effect = [mock_page1, mock_page2]

        # 创建第一个 handler 并连接
        handler1 = BrowserHandler(local_port=self.local_port)
        result1 = handler1.connect()

        # 创建第二个 handler 并连接同一端口
        handler2 = BrowserHandler(local_port=self.local_port)
        result2 = handler2.connect()

        # 验证
        self.assertTrue(result1)
        self.assertTrue(result2)
        self.assertIs(handler1.page, mock_page1)
        self.assertIs(handler2.page, mock_page2)

    @patch("core.browser_handler.ChromiumPage")
    @patch("core.browser_handler.ChromiumOptions")
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_connect_with_nonexistent_path(
        self, mock_makedirs, mock_exists, mock_co_class, mock_page_class
    ):
        """测试使用不存在的路径连接"""

        # 设置 Mock - 让 user_data_path 返回 False（不存在）
        def exists_side_effect(path):
            if "nonexistent" in path:
                return False
            return True

        mock_exists.side_effect = exists_side_effect

        mock_co = Mock()
        mock_co_class.return_value = mock_co

        mock_page = Mock()
        mock_page_class.return_value = mock_page

        # 创建 handler 并连接
        handler = BrowserHandler(user_data_path="/nonexistent/path", local_port=self.local_port)
        result = handler.connect()

        # 验证
        self.assertTrue(result)
        # 验证没有调用 set_user_data_path（因为路径不存在）
        mock_co.set_user_data_path.assert_not_called()


class TestBrowserHandlerIntegration(unittest.TestCase):
    """BrowserHandler 集成测试（需要真实 Chrome 环境）"""

    def test_real_connection(self):
        """测试真实浏览器连接（需要 Chrome 在 debug 模式运行）

        注意：此测试需要 Chrome 以调试模式运行：
        chrome.exe --remote-debugging-port=9222 --user-data-dir="test_user_data"

        如果 Chrome 未运行，此测试将被跳过。
        """
        handler = BrowserHandler(local_port=9222)

        try:
            result = handler.connect()
            if result:
                self.assertTrue(handler.is_connected())
                self.assertIsNotNone(handler.get_page())
                handler.disconnect()
                self.assertFalse(handler.is_connected())
            else:
                self.skipTest("Chrome debug mode not available on port 9222")
        except Exception as e:
            self.skipTest(f"Chrome connection failed: {e}")


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)

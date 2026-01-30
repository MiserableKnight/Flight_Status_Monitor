"""
异常处理测试

测试自定义异常类的基本功能和上下文信息。
"""

import pytest

from exceptions.auth import (
    LoginFailedError,
    SessionExpiredError,
)
from exceptions.base import (
    AuthenticationException,
    ConnectionException,
    DataException,
    FlightMonitorException,
    NotificationException,
)
from exceptions.connection import (
    BrowserConnectionError,
    NetworkTimeoutError,
    PageLoadError,
    ReconnectionFailedError,
)
from exceptions.data import (
    DataExtractionError,
    DataFileError,
    DataParseError,
    DataValidationError,
)
from exceptions.notification import (
    AlertTriggerError,
    EmailSendError,
)


class TestBaseExceptions:
    """测试基础异常类"""

    def test_flight_monitor_exception_basic(self):
        """测试基础异常类"""
        exc = FlightMonitorException("测试错误")
        assert str(exc) == "测试错误"
        assert exc.message == "测试错误"
        assert exc.context == {}

    def test_flight_monitor_exception_with_context(self):
        """测试带上下文的异常"""
        context = {"aircraft": "B-220V", "flight": "VJ105"}
        exc = FlightMonitorException("测试错误", context=context)
        assert "aircraft=B-220V" in str(exc)
        assert exc.context == context

    def test_connection_exception(self):
        """测试连接异常"""
        exc = ConnectionException("连接失败", port=9222)
        assert "port=9222" in str(exc)
        assert exc.context["port"] == 9222

    def test_authentication_exception(self):
        """测试认证异常"""
        exc = AuthenticationException("登录失败", username="test_user")
        assert "username=test_user" in str(exc)
        assert exc.context["username"] == "test_user"

    def test_data_exception(self):
        """测试数据异常"""
        exc = DataException("数据错误", aircraft="B-220V", flight="VJ105")
        assert "aircraft=B-220V" in str(exc)
        assert "flight=VJ105" in str(exc)

    def test_notification_exception(self):
        """测试通知异常"""
        exc = NotificationException("通知失败", recipient="test@example.com")
        assert "recipient=test@example.com" in str(exc)

    def test_exception_to_dict(self):
        """测试异常转换为字典"""
        context = {"aircraft": "B-220V"}
        exc = FlightMonitorException("测试错误", context=context)
        exc_dict = exc.to_dict()
        assert exc_dict["exception_type"] == "FlightMonitorException"
        assert exc_dict["message"] == "测试错误"
        assert exc_dict["context"] == context


class TestConnectionExceptions:
    """测试连接相关异常"""

    def test_browser_connection_error(self):
        """测试浏览器连接错误"""
        exc = BrowserConnectionError(port=9222, message="无法连接")
        assert "端口: 9222" in str(exc)
        assert exc.context["port"] == 9222

    def test_browser_connection_error_with_retry(self):
        """测试带重试次数的浏览器连接错误"""
        exc = BrowserConnectionError(port=9222, message="连接失败", retry_count=3)
        assert "retry_count=3" in str(exc)
        assert exc.context["retry_count"] == 3

    def test_network_timeout_error(self):
        """测试网络超时错误"""
        exc = NetworkTimeoutError("加载数据", timeout=30)
        assert "加载数据" in str(exc)
        assert "30 秒" in str(exc)
        assert exc.context["timeout_seconds"] == 30

    def test_network_timeout_error_with_url(self):
        """测试带URL的网络超时错误"""
        exc = NetworkTimeoutError("访问页面", timeout=10, url="https://example.com")
        assert exc.context["url"] == "https://example.com"

    def test_page_load_error(self):
        """测试页面加载错误"""
        exc = PageLoadError("https://example.com", "超时")
        assert "https://example.com" in str(exc)
        assert "超时" in str(exc)
        assert exc.context["url"] == "https://example.com"

    def test_page_load_error_with_load_time(self):
        """测试带加载时间的页面加载错误"""
        exc = PageLoadError("https://example.com", "失败", load_time=5.2)
        assert exc.context["load_time_seconds"] == 5.2

    def test_reconnection_failed_error(self):
        """测试重连失败错误"""
        exc = ReconnectionFailedError(port=9222, max_attempts=3, last_error="连接被拒绝")
        assert "端口: 9222" in str(exc)
        assert "已尝试 3 次" in str(exc)
        assert "连接被拒绝" in str(exc)


class TestDataExceptions:
    """测试数据相关异常"""

    def test_data_extraction_error(self):
        """测试数据提取错误"""
        exc = DataExtractionError(aircraft="B-220V", reason="元素未找到", flight="VJ105")
        assert "B-220V" in str(exc)
        assert "VJ105" in str(exc)
        assert "元素未找到" in str(exc)

    def test_data_extraction_error_with_selector(self):
        """测试带选择器的数据提取错误"""
        exc = DataExtractionError(
            aircraft="B-220V",
            reason="选择器无效",
            element_selector="tag:div@@class=test",
        )
        assert exc.context["element_selector"] == "tag:div@@class=test"

    def test_data_validation_error(self):
        """测试数据验证错误"""
        exc = DataValidationError(field="航班号", value="INVALID", reason="格式不正确")
        assert "航班号" in str(exc)
        assert "INVALID" in str(exc)
        assert "格式不正确" in str(exc)

    def test_data_validation_error_with_aircraft(self):
        """测试带飞机号的数据验证错误"""
        exc = DataValidationError(
            field="起飞时间",
            value="25:00",
            reason="无效时间",
            aircraft="B-220V",
            flight="VJ105",
        )
        assert "B-220V" in str(exc)
        assert "VJ105" in str(exc)

    def test_data_parse_error(self):
        """测试数据解析错误"""
        exc = DataParseError(source="data.csv", reason="格式错误")
        assert "data.csv" in str(exc)
        assert "格式错误" in str(exc)

    def test_data_parse_error_with_line_number(self):
        """测试带行号的数据解析错误"""
        exc = DataParseError(source="data.csv", reason="列数不匹配", line_number=42)
        assert "行 42" in str(exc)
        assert exc.context["line_number"] == 42

    def test_data_file_error(self):
        """测试数据文件错误"""
        exc = DataFileError(file_path="data/test.csv", operation="read", reason="权限拒绝")
        assert "data/test.csv" in str(exc)
        assert "read" in str(exc)
        assert "权限拒绝" in str(exc)

    def test_data_file_error_with_aircraft(self):
        """测试带飞机号的数据文件错误"""
        exc = DataFileError(
            file_path="data/leg_B-220V.csv",
            operation="write",
            reason="磁盘已满",
            aircraft="B-220V",
        )
        assert "B-220V" in str(exc)


class TestNotificationExceptions:
    """测试通知相关异常"""

    def test_email_send_error(self):
        """测试邮件发送错误"""
        exc = EmailSendError(recipient="test@example.com", reason="SMTP连接失败")
        assert "test@example.com" in str(exc)
        assert "SMTP连接失败" in str(exc)

    def test_email_send_error_with_subject(self):
        """测试带主题的邮件发送错误"""
        exc = EmailSendError(
            recipient="test@example.com",
            reason="发送超时",
            subject="测试邮件",
        )
        assert exc.context["subject"] == "测试邮件"

    def test_alert_trigger_error(self):
        """测试告警触发错误"""
        exc = AlertTriggerError(aircraft="B-220V", alert_type="延误告警", reason="通知失败")
        assert "B-220V" in str(exc)
        assert "延误告警" in str(exc)

    def test_alert_trigger_error_with_flight(self):
        """测试带航班号的告警触发错误"""
        exc = AlertTriggerError(
            aircraft="B-220V",
            alert_type="取消告警",
            reason="模板错误",
            flight="VJ105",
        )
        assert "VJ105" in str(exc)
        assert exc.context["flight"] == "VJ105"


class TestAuthExceptions:
    """测试认证相关异常"""

    def test_login_failed_error(self):
        """测试登录失败错误"""
        exc = LoginFailedError(username="test_user", reason="密码错误")
        assert "test_user" in str(exc)
        assert "密码错误" in str(exc)

    def test_login_failed_error_with_url(self):
        """测试带URL的登录失败错误"""
        exc = LoginFailedError(
            username="test_user",
            reason="验证码错误",
            url="https://example.com/login",
        )
        assert exc.context["login_url"] == "https://example.com/login"

    def test_session_expired_error(self):
        """测试会话过期错误"""
        exc = SessionExpiredError()
        assert "会话已过期" in str(exc)

    def test_session_expired_error_with_username(self):
        """测试带用户名的会话过期错误"""
        exc = SessionExpiredError(username="test_user", last_activity="2025-01-30 10:00:00")
        assert "test_user" in str(exc)
        assert exc.context["last_activity"] == "2025-01-30 10:00:00"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

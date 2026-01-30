"""
基础异常类定义

提供航班监控系统的根异常类和主要分类。
"""

from typing import Any, Dict, Optional


class FlightMonitorException(Exception):
    """
    航班监控系统基础异常类

    所有自定义异常的父类，提供统一的异常接口和上下文信息存储。
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        初始化异常

        Args:
            message: 错误消息
            context: 额外的上下文信息字典（如飞机号、航班号、时间等）
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        """提供包含上下文的详细错误信息"""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} [{context_str}]"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """将异常转换为字典，便于日志记录和监控"""
        return {
            "exception_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
        }


class ConnectionException(FlightMonitorException):
    """连接相关异常（浏览器连接、网络超时等）"""

    def __init__(
        self,
        message: str,
        port: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化连接异常

        Args:
            message: 错误消息
            port: 相关的端口号（如调试端口）
            context: 额外的上下文信息
        """
        ctx = context or {}
        if port is not None:
            ctx["port"] = port
        super().__init__(message, ctx)


class AuthenticationException(FlightMonitorException):
    """认证相关异常（登录失败、会话过期等）"""

    def __init__(
        self,
        message: str,
        username: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化认证异常

        Args:
            message: 错误消息
            username: 相关的用户名
            context: 额外的上下文信息
        """
        ctx = context or {}
        if username is not None:
            ctx["username"] = username
        super().__init__(message, ctx)


class DataException(FlightMonitorException):
    """数据处理相关异常（数据提取、解析、验证失败等）"""

    def __init__(
        self,
        message: str,
        aircraft: Optional[str] = None,
        flight: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化数据异常

        Args:
            message: 错误消息
            aircraft: 相关的飞机号
            flight: 相关的航班号
            context: 额外的上下文信息
        """
        ctx = context or {}
        if aircraft is not None:
            ctx["aircraft"] = aircraft
        if flight is not None:
            ctx["flight"] = flight
        super().__init__(message, ctx)


class NotificationException(FlightMonitorException):
    """通知发送相关异常（邮件发送失败、告警触发失败等）"""

    def __init__(
        self,
        message: str,
        recipient: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化通知异常

        Args:
            message: 错误消息
            recipient: 相关的收件人
            context: 额外的上下文信息
        """
        ctx = context or {}
        if recipient is not None:
            ctx["recipient"] = recipient
        super().__init__(message, ctx)


class ConfigurationException(FlightMonitorException):
    """配置相关异常（配置缺失、格式错误等）"""

    def __init__(
        self,
        message: str,
        config_section: Optional[str] = None,
        config_key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化配置异常

        Args:
            message: 错误消息
            config_section: 相关的配置节
            config_key: 相关的配置键
            context: 额外的上下文信息
        """
        ctx = context or {}
        if config_section is not None:
            ctx["config_section"] = config_section
        if config_key is not None:
            ctx["config_key"] = config_key
        super().__init__(message, ctx)

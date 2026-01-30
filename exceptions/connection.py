"""
连接相关异常类

处理浏览器连接、网络超时、页面加载等连接层异常。
"""

from typing import Optional

from .base import ConnectionException


class BrowserConnectionError(ConnectionException):
    """
    浏览器连接失败异常

    当无法连接到Chrome调试端口时抛出。
    """

    def __init__(
        self,
        port: int,
        message: str = "浏览器连接失败",
        retry_count: Optional[int] = None,
    ):
        """
        初始化浏览器连接异常

        Args:
            port: Chrome调试端口
            message: 错误消息
            retry_count: 已重试次数
        """
        context = {}
        if retry_count is not None:
            context["retry_count"] = retry_count

        full_message = f"{message} (端口: {port})"
        super().__init__(full_message, port=port, context=context)


class NetworkTimeoutError(ConnectionException):
    """
    网络超时异常

    当网络操作超时时抛出。
    """

    def __init__(
        self,
        operation: str,
        timeout: int,
        url: Optional[str] = None,
    ):
        """
        初始化网络超时异常

        Args:
            operation: 超时的操作描述
            timeout: 超时时间（秒）
            url: 相关的URL（如果有）
        """
        context = {"operation": operation, "timeout_seconds": timeout}
        if url is not None:
            context["url"] = url

        message = f"{operation} 超时 (超过 {timeout} 秒)"
        super().__init__(message, context=context)


class PageLoadError(ConnectionException):
    """
    页面加载失败异常

    当页面加载失败或超时时抛出。
    """

    def __init__(
        self,
        url: str,
        reason: str,
        load_time: Optional[float] = None,
    ):
        """
        初始化页面加载异常

        Args:
            url: 目标URL
            reason: 失败原因
            load_time: 加载耗时（秒）
        """
        context = {"url": url, "reason": reason}
        if load_time is not None:
            context["load_time_seconds"] = load_time

        message = f"页面加载失败: {reason} (URL: {url})"
        super().__init__(message, context=context)


class ReconnectionFailedError(ConnectionException):
    """
    重连失败异常

    当尝试重新连接浏览器多次均失败时抛出。
    """

    def __init__(
        self,
        port: int,
        max_attempts: int,
        last_error: str,
    ):
        """
        初始化重连失败异常

        Args:
            port: Chrome调试端口
            max_attempts: 最大重试次数
            last_error: 最后一次错误信息
        """
        message = f"重连失败 (端口: {port}, 已尝试 {max_attempts} 次): {last_error}"
        context = {"max_attempts": max_attempts, "last_error": last_error}
        super().__init__(message, port=port, context=context)

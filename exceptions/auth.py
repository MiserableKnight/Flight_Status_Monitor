"""
认证相关异常类

处理登录、会话管理等认证层异常。
"""

from typing import Optional

from .base import AuthenticationException


class LoginFailedError(AuthenticationException):
    """
    登录失败异常

    当用户登录失败时抛出。
    """

    def __init__(
        self,
        username: str,
        reason: str,
        url: Optional[str] = None,
    ):
        """
        初始化登录失败异常

        Args:
            username: 用户名
            reason: 失败原因
            url: 登录URL（可选）
        """
        context = {"reason": reason}
        if url is not None:
            context["login_url"] = url

        message = f"登录失败 ({username}): {reason}"

        super().__init__(message, username=username, context=context)


class SessionExpiredError(AuthenticationException):
    """
    会话过期异常

    当检测到会话已过期需要重新登录时抛出。
    """

    def __init__(
        self,
        username: Optional[str] = None,
        last_activity: Optional[str] = None,
    ):
        """
        初始化会话过期异常

        Args:
            username: 用户名（可选）
            last_activity: 最后活动时间（可选）
        """
        context = {}
        if last_activity is not None:
            context["last_activity"] = last_activity

        message = "会话已过期，需要重新登录"
        if username:
            message += f" ({username})"

        super().__init__(message, username=username, context=context)


class CredentialsError(AuthenticationException):
    """
    凭证异常

    当用户名密码配置错误或缺失时抛出。
    """

    def __init__(
        self,
        reason: str,
        missing_field: Optional[str] = None,
    ):
        """
        初始化凭证异常

        Args:
            reason: 错误原因
            missing_field: 缺失的配置字段（可选）
        """
        context = {"reason": reason}
        if missing_field is not None:
            context["missing_field"] = missing_field

        message = f"凭证错误: {reason}"
        if missing_field:
            message += f" (缺失字段: {missing_field})"

        super().__init__(message, context=context)

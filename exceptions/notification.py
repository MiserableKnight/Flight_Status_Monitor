"""
通知相关异常类

处理邮件发送、告警触发等通知层异常。
"""

from typing import Any, Dict, Optional

from .base import NotificationException


class EmailSendError(NotificationException):
    """
    邮件发送失败异常

    当邮件发送失败时抛出。
    """

    def __init__(
        self,
        recipient: str,
        reason: str,
        subject: Optional[str] = None,
        smtp_error: Optional[str] = None,
    ):
        """
        初始化邮件发送异常

        Args:
            recipient: 收件人邮箱
            reason: 失败原因
            subject: 邮件主题（可选）
            smtp_error: SMTP错误信息（可选）
        """
        context = {"recipient": recipient, "reason": reason}
        if subject is not None:
            context["subject"] = subject
        if smtp_error is not None:
            context["smtp_error"] = smtp_error

        message = f"邮件发送失败 (收件人: {recipient}): {reason}"

        super().__init__(message, recipient=recipient, context=context)


class AlertTriggerError(NotificationException):
    """
    告警触发失败异常

    当告警条件满足但触发通知失败时抛出。
    """

    def __init__(
        self,
        aircraft: str,
        alert_type: str,
        reason: str,
        flight: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化告警触发异常

        Args:
            aircraft: 飞机号
            alert_type: 告警类型
            reason: 失败原因
            flight: 航班号（可选）
            context_data: 额外的上下文数据
        """
        ctx = context_data or {}
        ctx["alert_type"] = alert_type
        if flight is not None:
            ctx["flight"] = flight

        message = f"告警触发失败 - {aircraft} ({alert_type})"
        if flight:
            message += f" 航班: {flight}"
        message += f": {reason}"

        # Note: recipient is optional for alerts, so we don't pass it to parent
        super().__init__(message, context=ctx)


class NotificationConfigError(NotificationException):
    """
    通知配置异常

    当通知配置不正确或缺失时抛出。
    """

    def __init__(
        self,
        config_key: str,
        reason: str,
    ):
        """
        初始化通知配置异常

        Args:
            config_key: 配置键名
            reason: 失败原因
        """
        context = {
            "config_key": config_key,
            "reason": reason,
        }

        message = f"通知配置错误 - {config_key}: {reason}"

        super().__init__(message, context=context)

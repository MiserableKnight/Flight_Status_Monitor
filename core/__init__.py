"""
核心系统模块
提供浏览器管理、通知和日志功能
"""

# 延迟导入，避免依赖问题
__all__ = ["BrowserHandler", "get_logger"]


def __getattr__(name):
    """延迟导入，只在需要时加载模块"""
    if name == "BrowserHandler":
        from .browser_handler import BrowserHandler

        return BrowserHandler
    elif name == "get_logger":
        from .logger import get_logger

        return get_logger
    raise AttributeError(f"module {__name__} has no attribute {name}")

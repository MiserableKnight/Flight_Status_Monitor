"""
接口层定义

提供清晰的接口契约，实现依赖注入和解耦
"""

from .interfaces import IConfigLoader, IFetcher, ILogger, IScheduler

__all__ = ["IFetcher", "IScheduler", "ILogger", "IConfigLoader"]

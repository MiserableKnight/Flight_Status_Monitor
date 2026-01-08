# -*- coding: utf-8 -*-
"""
核心系统模块
提供浏览器管理、导航、通知和日志功能
"""
from .browser_handler import BrowserHandler
from .navigator import Navigator, PageState
from .logger import get_logger

__all__ = ['BrowserHandler', 'Navigator', 'PageState', 'get_logger']

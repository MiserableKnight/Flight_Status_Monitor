# -*- coding: utf-8 -*-
"""
接口定义

定义系统中关键组件的接口契约，实现依赖注入和松耦合
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from DrissionPage import ChromiumPage


class IFetcher(ABC):
    """
    数据抓取器接口

    定义所有数据抓取器必须实现的方法
    """

    @abstractmethod
    def connect_browser(self) -> Optional[ChromiumPage]:
        """
        连接到浏览器

        Returns:
            ChromiumPage: 浏览器页面对象，失败返回 None
        """
        pass

    @abstractmethod
    def smart_login(self, page: ChromiumPage) -> bool:
        """
        执行智能登录

        Args:
            page: 浏览器页面对象

        Returns:
            bool: 是否登录成功
        """
        pass

    @abstractmethod
    def get_today_date(self) -> str:
        """
        获取今天的日期字符串

        Returns:
            str: 格式为 YYYY-MM-DD 的日期字符串
        """
        pass

    @abstractmethod
    def navigate_to_target_page(self, page: ChromiumPage, target_date: str,
                                aircraft_list: List[str]) -> Optional[List[Dict[str, Any]]]:
        """
        导航到目标页面并提取数据

        Args:
            page: 浏览器页面对象
            target_date: 目标日期字符串
            aircraft_list: 飞机列表

        Returns:
            提取的数据列表，失败返回 None
        """
        pass

    @abstractmethod
    def save_to_csv(self, data: List[Dict[str, Any]], filename: str) -> Optional[str]:
        """
        保存数据到CSV文件

        Args:
            data: 要保存的数据
            filename: 文件名

        Returns:
            str: 保存的文件路径，失败返回 None
        """
        pass



class ILogger(ABC):
    """
    日志记录器接口

    定义日志记录器必须实现的方法
    """

    @abstractmethod
    def __call__(self, message: str, level: str = "INFO"):
        """
        记录日志

        Args:
            message: 日志消息
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, SUCCESS)
        """
        pass


class IConfigLoader(ABC):
    """
    配置加载器接口

    定义配置加载器必须实现的方法
    """

    @abstractmethod
    def get_all_config(self) -> Dict[str, Any]:
        """
        获取所有配置

        Returns:
            Dict: 配置字典
        """
        pass

    @abstractmethod
    def get_config(self, section: str) -> Dict[str, Any]:
        """
        获取特定部分的配置

        Args:
            section: 配置部分名称

        Returns:
            Dict: 配置字典
        """
        pass


class IScheduler(ABC):
    """
    调度器接口

    定义调度器必须实现的方法
    """

    @abstractmethod
    def connect_browser(self) -> bool:
        """
        连接到浏览器

        Returns:
            bool: 是否成功
        """
        pass

    @abstractmethod
    def login(self) -> bool:
        """
        执行登录

        Returns:
            bool: 是否成功
        """
        pass

    @abstractmethod
    def fetch_data(self) -> bool:
        """
        抓取数据

        Returns:
            bool: 是否成功
        """
        pass

    @abstractmethod
    def get_check_interval(self) -> timedelta:
        """
        获取检查间隔

        Returns:
            timedelta: 检查间隔时间
        """
        pass

    @abstractmethod
    def run(self):
        """
        运行调度器主循环
        """
        pass

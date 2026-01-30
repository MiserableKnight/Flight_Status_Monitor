"""
数据抓取基类

轻量级协调器 - 组合各个专业组件
"""

import os
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime

from DrissionPage import ChromiumOptions, ChromiumPage

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.config_loader import ConfigLoader
from config.constants import DEFAULT_BROWSER_PORT
from core.data_saver import DataSaver
from core.logger import get_logger
from core.login_manager import LoginManager


class BaseFetcher(ABC):
    """数据抓取基类 - 轻量级协调器"""

    # 类级别的浏览器实例管理（支持多端口）
    _browsers = {}  # 按端口存储浏览器实例 {port: ChromiumPage}

    def get_browser_port(self):
        """
        获取浏览器端口（子类可重写）

        Returns:
            int: 浏览器调试端口，默认 9222
        """
        return DEFAULT_BROWSER_PORT

    def get_browser_user_data_path(self):
        """
        获取浏览器用户数据路径（子类可重写）

        Returns:
            str: 用户数据路径
        """
        return self.user_data_path

    def __init__(self, config_file=None):
        """
        初始化

        :param config_file: 配置文件路径,默认为 config/config.ini
        """
        self.config_file = config_file or os.path.join(project_root, "config/config.ini")
        self.cfg = None
        self.user_data_path = None
        self.aircraft_list = []
        self.log = get_logger()

        # 初始化状态标记（避免重复设置机号和日期）
        self._initialized = False
        self._initialized_date = None  # 记录已初始化的日期
        self.fetcher_name = self.__class__.__name__  # 记录fetcher类型名称

        # 加载配置
        self._load_config()

        # 初始化组件（依赖注入）
        credentials = {
            "username": self.cfg["username"],
            "password": self.cfg["password"],
        }
        self.login_manager = LoginManager(credentials, self.log)
        self.data_saver = DataSaver(project_root, self.log)

    def _load_config(self):
        """加载配置文件（优先从环境变量读取敏感配置）"""
        # 使用统一的配置加载器（自动从环境变量和 config.ini 加载）
        config_loader = ConfigLoader(self.config_file)

        try:
            self.cfg = {
                "username": config_loader.get_credentials()["username"],
                "password": config_loader.get_credentials()["password"],
                "user_data_path": config_loader.get_paths()["user_data_path"],
                "target_url": config_loader.get_target_url(),
            }
            self.user_data_path = self.cfg["user_data_path"]
        except Exception as e:
            raise ValueError(f"配置文件缺失: {e}")

        # 读取飞机号列表
        self.aircraft_list = config_loader.get_aircraft_list()
        if self.aircraft_list:
            print(f"✅ 读取到 {len(self.aircraft_list)} 架飞机: {', '.join(self.aircraft_list)}")
        else:
            print("⚠️ 配置文件中未找到飞机号列表")

    @staticmethod
    def get_today_date():
        """获取当天日期,格式: YYYY-MM-DD"""
        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def wait_and_click(page, selector, timeout=10, desc="元素"):
        """等待元素出现并点击"""
        for i in range(timeout):
            ele = page.ele(selector)
            if ele and ele.states.is_displayed:
                print(f"   ✅ 找到 {desc}")
                ele.click(by_js=True)
                time.sleep(1)
                return True
            time.sleep(1)
            print(f"   ⏳ 等待 {desc}... ({i + 1}/{timeout})")
        print(f"   ❌ 超时: 未找到 {desc}")
        return False

    def connect_browser(self):
        """
        连接到浏览器

        核心改进：
        - 支持多端口浏览器实例管理
        - 子类通过重写 get_browser_port() 指定端口
        - 每个端口使用独立的浏览器实例

        :return: ChromiumPage 对象,失败返回 None
        """
        # 获取子类指定的端口配置
        port = self.get_browser_port()
        user_data_path = self.get_browser_user_data_path()

        # 按端口管理浏览器实例
        if port not in BaseFetcher._browsers:
            co = ChromiumOptions()
            co.set_user_data_path(user_data_path)
            co.set_local_port(port)

            try:
                print(f"\n{'=' * 60}")
                print("🌐 初始化浏览器连接...")
                print(f"📍 端口: {port}")
                print(f"📍 用户数据: {user_data_path}")
                print(f"{'=' * 60}")
                BaseFetcher._browsers[port] = ChromiumPage(co)
                print("✅ 浏览器连接成功!")
                self.log(f"Browser connected successfully (port: {port})", "INFO")
            except Exception as e:
                print(f"❌ 浏览器连接失败: {e}")
                print(f"请确保Chrome调试模式已启动 (端口{port})")
                self.log(f"Browser connection failed: {e}", "ERROR")
                return None

        # 返回浏览器对象
        return BaseFetcher._browsers[port]

    def smart_login(self, page, target_url=None):
        """
        智能登录系统 - 委托给 LoginManager

        :param page: ChromiumPage 对象
        :param target_url: 目标URL（可选），登录成功后直接跳转
        :return: 成功返回 True,失败返回 False
        """
        return self.login_manager.login(page, target_url)

    def save_to_csv(self, data, filename=None, subdir="data/daily_raw"):
        """
        保存数据到CSV文件 - 委托给 DataSaver

        :param data: 要保存的数据(二维列表)
        :param filename: 文件名,不指定则自动生成
        :param subdir: 子目录名,默认为 'data/daily_raw'
        :return: 保存成功返回文件路径,失败返回 None
        """
        if not data:
            print("   ❌ 没有数据可保存")
            return None

        # 生成文件名
        if not filename:
            today = self.get_today_date()
            filename = f"{self.get_data_prefix()}_{today}.csv"

        # 判断是否需要备份（只备份 data/leg_data.csv 总表）
        needs_backup = subdir == "data" and filename == "leg_data.csv"

        return self.data_saver.save_csv(data, filename, subdir, needs_backup)

    @abstractmethod
    def get_data_prefix(self):
        """返回数据文件前缀,子类必须实现"""
        pass

    @abstractmethod
    def navigate_to_target_page(self, page, target_date):
        """
        导航到目标页面并执行抓取逻辑
        子类必须实现

        :param page: ChromiumPage 对象
        :param target_date: 目标日期
        :return: 成功返回数据,失败返回 None
        """
        pass

    def main(self, target_date=None):
        """
        主函数模板方法

        :param target_date: 目标日期,不指定则使用今天
        :return: 成功返回 True,失败返回 False
        """
        # 确定要抓取的日期
        if target_date:
            target = target_date
            print(f"🎯 目标日期:{target}")
            self.log(f"Fetching data for: {target}")
        else:
            target = self.get_today_date()
            print(f"🎯 默认抓取今天的数据:{target}")
            self.log(f"Fetching today's data: {target}")

        # 连接浏览器
        page = self.connect_browser()
        if not page:
            return False

        # 智能登录
        if not self.smart_login(page):
            return False

        time.sleep(0.5)

        # 导航到目标页面并执行抓取(子类实现)
        print("\n🎯 开始执行抓取流程...")
        data = self.navigate_to_target_page(page, target)

        # 保存数据(子类可以选择是否在 navigate_to_target_page 中保存)
        if data:
            csv_file = self.save_to_csv(data, filename=f"{self.get_data_prefix()}_{target}.csv")
            if csv_file:
                print("\n🎉 数据抓取完成!")
                print(f"📄 文件路径: {csv_file}")
                print(f"📊 总记录数: {len(data) - 1 if len(data) > 1 else 0}")
                self.log(f"Data saved successfully: {csv_file}", "SUCCESS")
            else:
                print("\n❌ 保存失败")
                self.log("Failed to save data", "ERROR")
                return False
        else:
            print("\n❌ 未提取到数据")
            self.log("No data extracted", "ERROR")
            return False

        print("\n✨ 任务完成")
        self.log(f"Task completed for {target}", "SUCCESS")
        return True

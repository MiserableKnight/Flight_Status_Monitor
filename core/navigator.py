# -*- coding: utf-8 -*-
"""
智能导航模块
提供URL状态检测、智能导航和自动恢复功能
"""
from DrissionPage import ChromiumPage
import time
from enum import Enum
from typing import Optional, Callable
from .logger import get_logger


class PageState(Enum):
    """页面状态枚举"""
    NEED_LOGIN = "NEED_LOGIN"           # 需要登录
    ALREADY_TARGET = "ALREADY_TARGET"   # 已在目标页
    IN_SYSTEM = "IN_SYSTEM"             # 在系统内但非目标页
    OUT_SYSTEM = "OUT_SYSTEM"           # 在系统外
    UNKNOWN = "UNKNOWN"                 # 未知状态


class Navigator:
    """智能导航器类"""

    def __init__(self, config: dict = None):
        """
        初始化导航器

        Args:
            config: 配置字典，包含URL等信息
        """
        self.config = config or {}
        self.urls = self.config.get('urls', {})
        self.target_url = self.config.get('target_url', '')
        self.log = get_logger()

    def detect_page_state(self, page: ChromiumPage, target_url_keyword: str = None) -> PageState:
        """
        检测当前页面状态

        Args:
            page: 浏览器页面对象
            target_url_keyword: 目标URL关键词

        Returns:
            PageState: 当前页面状态
        """
        try:
            current_url = page.url
            print(f"🔍 当前网址检测: {current_url}")
        except Exception as e:
            print(f"⚠️ 无法获取当前URL: {e}")
            return PageState.UNKNOWN

        # 1. 检查是否在登录页或鉴权页
        login_keywords = self.urls.get('login_keywords', 'login,rbacUsersController,auth')
        login_indicators = [k.strip() for k in login_keywords.split(',')]

        if any(indicator in current_url.lower() for indicator in login_indicators):
            print("⚠️ 检测到处于登录或鉴权页，需要重新登录")
            return PageState.NEED_LOGIN

        # 2. 检查是否已经在目标业务页
        if target_url_keyword and target_url_keyword in current_url:
            print(f"✅ 已在目标页面 ({target_url_keyword})")
            return PageState.ALREADY_TARGET

        # 3. 检查是否在系统首页
        home_keyword = self.urls.get('home', 'mainController/index.html')
        if home_keyword in current_url:
            if target_url_keyword:
                print(f"📍 已在系统首页，准备跳转至目标模块 ({target_url_keyword})...")
            else:
                print("📍 已在系统首页")
            return PageState.IN_SYSTEM

        # 4. 检查是否在系统内（通过域名判断）
        if "cis.comac.cc:8004" in current_url:
            print(f"📍 在系统内但非首页，当前URL: {current_url}")
            return PageState.IN_SYSTEM

        # 5. 其他情况 - 在系统外
        print(f"🌐 在系统外，准备进入系统...")
        return PageState.OUT_SYSTEM

    def navigate_to_target(self, page: ChromiumPage, state: PageState) -> bool:
        """
        根据页面状态执行导航操作

        Args:
            page: 浏览器页面对象
            state: 当前页面状态

        Returns:
            bool: 导航是否成功
        """
        if state == PageState.ALREADY_TARGET:
            # 已在目标页，刷新确保数据最新
            print("🔄 刷新当前页面...")
            page.refresh()
            time.sleep(1)
            return True

        elif state == PageState.IN_SYSTEM:
            # 在系统内，无需额外跳转
            print("✅ 已在系统内")
            return True

        elif state == PageState.OUT_SYSTEM:
            # 在系统外，跳转到首页
            print(f"🔗 跳转至系统首页: {self.target_url}")
            page.get(self.target_url)
            time.sleep(2)
            return True

        elif state == PageState.NEED_LOGIN:
            # 需要登录，返回False让调用方处理
            print("❌ 需要重新登录，请调用 LoginManager 执行登录")
            return False

        else:
            # 未知状态，尝试跳转至首页
            print("⚠️ 未知页面状态，尝试跳转至首页...")
            page.get(self.target_url)
            time.sleep(2)
            return True

    def smart_navigate(self, page: ChromiumPage, target_module_keyword: str = None,
                      perform_login: Callable = None) -> bool:
        """
        智能导航到目标模块（一站式函数）

        Args:
            page: 浏览器页面对象
            target_module_keyword: 目标模块关键词 (例如: "integratedMonitor", "lineLogNewController")
            perform_login: 登录函数（当检测到需要登录时调用）

        Returns:
            bool: 导航是否成功
        """
        print("\n" + "="*60)
        print("🧭 智能导航系统启动")
        print("="*60)

        # 步骤1: 检测当前状态
        state = self.detect_page_state(page, target_module_keyword)

        # 步骤2: 如果需要登录，调用登录函数
        if state == PageState.NEED_LOGIN:
            if perform_login:
                print("\n🔑 调用自动登录函数...")
                try:
                    perform_login()
                    time.sleep(3)
                    # 登录后重新检测状态
                    state = self.detect_page_state(page, target_module_keyword)
                except Exception as e:
                    print(f"❌ 登录失败: {e}")
                    self.log(f"登录失败: {e}", "ERROR")
                    return False
            else:
                print("❌ 需要登录，但未提供登录函数")
                return False

        # 步骤3: 执行导航
        success = self.navigate_to_target(page, state)

        if success:
            print("✅ 导航完成")
        else:
            print("❌ 导航失败")

        print("="*60 + "\n")
        return success

    def get_current_module(self, page: ChromiumPage) -> str:
        """
        获取当前所在模块名称

        Args:
            page: 浏览器页面对象

        Returns:
            str: 模块名称
        """
        try:
            current_url = page.url

            if "mainController/index.html" in current_url:
                return "首页"
            elif "integratedMonitor" in current_url:
                return "综合监控"
            elif "lineLogNewController" in current_url:
                return "运力统计"
            elif any(kw in current_url.lower() for kw in ['login', 'rbacUsersController']):
                return "登录页"
            elif "cis.comac.cc:8004" in current_url:
                return "其他系统页"
            else:
                return "系统外"
        except:
            return "未知"

    def check_login_status(self, page: ChromiumPage) -> bool:
        """
        检查登录状态

        Args:
            page: 浏览器页面对象

        Returns:
            bool: True=已登录, False=未登录
        """
        state = self.detect_page_state(page)
        return state != PageState.NEED_LOGIN


# 便捷函数（向后兼容）
def ensure_page_state(page, target_url_keyword=None, home_keyword="mainController/index.html"):
    """
    智能检测并确保浏览器处于正确状态（向后兼容函数）

    Args:
        page: ChromiumPage 实例
        target_url_keyword: 目标URL关键词
        home_keyword: 系统首页关键词

    Returns:
        PageState: 当前页面状态
    """
    nav = Navigator()
    return nav.detect_page_state(page, target_url_keyword)


def navigate_to_target(page, state, target_url=None):
    """
    根据页面状态执行导航操作（向后兼容函数）

    Args:
        page: ChromiumPage 实例
        state: 页面状态 (PageState)
        target_url: 目标URL (可选)

    Returns:
        bool: 导航是否成功
    """
    config = {'target_url': target_url} if target_url else {}
    nav = Navigator(config=config)
    return nav.navigate_to_target(page, state)


def smart_navigate(page, target_module_keyword=None, perform_login=None):
    """
    智能导航到目标模块（向后兼容函数）

    Args:
        page: ChromiumPage 实例
        target_module_keyword: 目标模块关键词
        perform_login: 登录函数

    Returns:
        bool: 导航是否成功
    """
    nav = Navigator()
    return nav.smart_navigate(page, target_module_keyword, perform_login)


if __name__ == "__main__":
    # 测试代码
    print("🧪 导航模块测试")
    print("="*60)

    from .browser_handler import BrowserHandler
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.config_loader import load_config

    config_loader = load_config()
    config = config_loader.get_all_config()

    handler = BrowserHandler(user_data_path=config['paths']['user_data_path'])

    if handler.connect():
        page = handler.get_page()
        navigator = Navigator(config)

        # 测试1: 获取当前模块
        module = navigator.get_current_module(page)
        print(f"📍 当前模块: {module}")

        # 测试2: 检查登录状态
        is_logged_in = navigator.check_login_status(page)
        print(f"🔐 登录状态: {'已登录' if is_logged_in else '未登录'}")

        # 测试3: 智能导航到首页
        success = navigator.smart_navigate(page)
        print(f"🎯 导航结果: {'成功' if success else '失败'}")
    else:
        print("❌ 无法连接到浏览器")

    print("\n✅ 测试完成")

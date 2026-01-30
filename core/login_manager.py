"""
登录管理器

专门处理页面状态检测和登录流程
职责：
- 检测当前页面状态（登录页、首页、中间页等）
- 处理登录表单填写
- 处理页面跳转逻辑
"""

import time
from typing import Optional

from DrissionPage import ChromiumPage

from config.constants import (
    LOGIN_CHECK_INTERVAL,
    MAX_LOGIN_WAIT_SECONDS,
    TARGET_PAGE_LOAD_TIMEOUT,
)


class LoginManager:
    """登录管理器 - 处理所有登录相关逻辑"""

    def __init__(self, credentials: dict, logger):
        """
        初始化登录管理器

        Args:
            credentials: 登录凭证 {"username": "...", "password": "..."}
            logger: 日志记录器
        """
        self.credentials = credentials
        self.log = logger

    def login(self, page: ChromiumPage, target_url: Optional[str] = None) -> bool:
        """
        智能登录主入口

        Args:
            page: ChromiumPage 对象
            target_url: 目标URL（可选），登录成功后直接跳转

        Returns:
            bool: 成功返回 True，失败返回 False
        """
        print("\n🔍 检查当前页面状态...")
        current_url = page.url
        print(f"📍 当前URL: {current_url}")

        # 优先级1: 检查是否在系统首页
        if "mainController/index.html" in current_url:
            print("✅ 已在系统首页: mainController/index.html")
            self.log("Already at main page", "INFO")
            return True

        # 优先级2: 处理空白页
        if self._is_blank_page(current_url):
            print("🌐 检测到空白页,导航到登录页面...")
            page.get("https://cis2.comac.cc:8040/portal/")
            time.sleep(2)
            current_url = page.url

        # 判断页面状态
        is_login_page = self._is_login_page(current_url, page)
        is_in_system = self._is_in_system(current_url)

        # 如果已在系统内但不在首页，也认为就绪
        if is_in_system:
            print("✅ 已在系统内")
            self.log("Already in system", "INFO")
            return True

        # 如果不在登录流程中，导航到首页
        if not self._is_blank_page(current_url) and not is_login_page:
            print("🚀 不在登录流程中,导航到系统首页...")
            page.get("https://cis.comac.cc:8004/caphm/mainController/index.html")
            time.sleep(2)
            current_url = page.url

        # 智能等待: 监控所有可能的页面状态
        return self._wait_and_navigate(page, target_url)

    def _is_blank_page(self, url: str) -> bool:
        """判断是否为空白页"""
        return "chrome://" in url or url == "about:blank" or "newtab" in url

    def _is_login_page(self, url: str, page: ChromiumPage) -> bool:
        """判断是否为登录页"""
        is_portal = "portal" in url and "login" in url
        is_rbac = "rbacUsersController/login.html" in url
        is_cis_login = "cis.comac.cc" in url and page.ele("#loginPwd")
        return is_portal or is_rbac or is_cis_login

    def _is_in_system(self, url: str) -> bool:
        """判断是否已在系统内"""
        return "cis.comac.cc:8004" in url or "cis.comac.cc:8010" in url

    def _wait_and_navigate(self, page: ChromiumPage, target_url: Optional[str]) -> bool:
        """
        等待并处理页面跳转

        Args:
            page: ChromiumPage 对象
            target_url: 目标URL

        Returns:
            bool: 是否成功
        """
        print("\n⏳ 智能监控页面跳转...")
        login_executed = False

        for i in range(MAX_LOGIN_WAIT_SECONDS):
            current_url = page.url

            # 每5秒打印一次URL
            if i % 10 == 0:
                print(f"   📍 [{i // 2}s] 当前URL: {current_url}")

            # 情况1: 已在目标首页
            if "mainController/index.html" in current_url:
                print("   ✅ 已在首页!")
                break

            # 情况2: 在登录页 - 需要填充账号密码
            if self._is_login_page(current_url, page) and not login_executed:
                if self._handle_login(page):
                    login_executed = True

            # 情况3: 在rbac中间页 - 需要点击WEB
            elif "rbacUsersController/login.html" in current_url:
                self._handle_rbac_intermediate(page)

            # 情况4: 已在系统内其他页面
            elif self._is_in_system(current_url):
                print("   ✅ 已在系统内")
                break

            # 每5秒打印一次进度
            if i % 10 == 0 and i > 0:
                print(f"   ⏳ 等待中... {i // 2}秒", end="\r")

            # 快速检测
            time.sleep(LOGIN_CHECK_INTERVAL)

        print()  # 换行

        # 最终验证
        success = "mainController/index.html" in page.url or self._is_in_system(page.url)
        if success:
            print(f"🎉 准备完成!当前页面: {page.title}")
            self.log("系统就绪", "SUCCESS")

            # 如果提供了目标URL，直接跳转
            if target_url:
                return self._navigate_to_target(page, target_url)

            return True
        else:
            print(f"❌ 超时或异常,当前页面: {page.url}")
            self.log("页面状态异常", "ERROR")
            return False

    def _handle_login(self, page: ChromiumPage) -> bool:
        """
        处理登录表单填写

        Args:
            page: ChromiumPage 对象

        Returns:
            bool: 是否成功
        """
        pwd_ele = page.ele("#loginPwd")
        if not pwd_ele:
            return False

        print("   🔒 检测到登录页,开始登录...")
        try:
            # 填账号
            user_ele = (
                page.ele("tag:input@@placeholder=请输入账号")
                or page.ele("tag:input@@type=text")
                or page.ele("tag:input@@name=username")
            )

            if user_ele:
                print("   ✅ 找到账号输入框")
                user_ele.clear()
                user_ele.input(self.credentials["username"])
                print("   📝 账号已填写")
                try:
                    page.ele("text:FLYWIN").click(by_js=True)
                except:
                    pass

            # 填密码并提交
            pwd_ele.clear()
            pwd_ele.input(self.credentials["password"])
            print("   📝 密码已填写")
            print("   ⚡ 提交登录...")
            pwd_ele.input("\n")
            return True

        except Exception as e:
            print(f"   ❌ 登录出错: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _handle_rbac_intermediate(self, page: ChromiumPage):
        """
        处理rbac中间页

        Args:
            page: ChromiumPage 对象
        """
        web_btn = page.ele("text:WEB")
        if web_btn and web_btn.states.is_displayed:
            print("   👀 检测到中间页,点击 'WEB' 按钮...")
            web_btn.click(by_js=True)

    def _navigate_to_target(self, page: ChromiumPage, target_url: str) -> bool:
        """
        跳转到目标页面

        Args:
            page: ChromiumPage 对象
            target_url: 目标URL

        Returns:
            bool: 是否成功
        """
        print("🎯 登录成功，直接跳转到目标页面...")
        print(f"   📍 目标URL: {target_url}")
        try:
            before_url = page.url
            print(f"   📍 跳转前URL: {before_url}")

            page.get(target_url)

            # 等待页面加载完成
            print("   ⏳ 等待目标页面加载...")
            for i in range(TARGET_PAGE_LOAD_TIMEOUT):
                current_url = page.url
                if (
                    "integratedMonitorController" in current_url
                    or "lineLogController" in current_url
                ):
                    print(f"   ✅ 已到达目标页面 (耗时: {i + 1}秒)")
                    print(f"   📍 最终URL: {current_url}")
                    return True
                print(
                    f"   ⏳ 加载中... URL: {current_url[:80]}... ({i + 1}/{TARGET_PAGE_LOAD_TIMEOUT}秒)"
                )
                time.sleep(1)

            print("   ⚠️ 页面加载超时，可能被重定向")
            print(f"   📍 最终URL: {page.url}")
            print("   💡 将在后续流程中尝试重新跳转")
            return True  # 不返回False，让流程继续

        except Exception as e:
            print(f"   ❌ 跳转失败: {e}")
            import traceback

            traceback.print_exc()
            print("   💡 将在后续流程中重试")
            return True  # 不返回False，让流程继续

# -*- coding: utf-8 -*-
"""
登录管理模块
封装系统登录逻辑
"""
from DrissionPage import ChromiumPage
import time
from typing import Dict
from ..core.logger import get_logger


class LoginManager:
    """登录管理器类"""

    def __init__(self, credentials: Dict[str, str] = None):
        """
        初始化登录管理器

        Args:
            credentials: 登录凭证字典 {'username': 'xxx', 'password': 'xxx'}
        """
        self.username = credentials.get('username', '') if credentials else ''
        self.password = credentials.get('password', '') if credentials else ''
        self.log = get_logger()

    def perform_login(self, page: ChromiumPage) -> bool:
        """
        执行登录操作

        Args:
            page: 浏览器页面对象

        Returns:
            bool: 登录是否成功
        """
        if not self.username or not self.password:
            self.log("登录凭证不完整", "ERROR")
            return False

        try:
            print("🔒 开始登录流程...")

            # A. 填账号
            user_ele = page.ele('tag:input@@placeholder=请输入账号')
            if not user_ele:
                user_ele = page.ele('tag:input@@type=text')

            if user_ele:
                user_ele.clear()
                user_ele.input(self.username)
                # 点击空白处消除干扰
                try:
                    page.ele('text:FLYWIN').click(by_js=True)
                except:
                    pass

            # B. 填密码
            pwd_ele = page.ele('#loginPwd')
            if pwd_ele:
                pwd_ele.clear()
                pwd_ele.input(self.password)
                time.sleep(0.5)

                # C. 提交（使用回车键）
                print("   ⚡ 发送【回车键】提交登录...")
                pwd_ele.input('\n')
            else:
                print("❌ 找不到密码框")
                return False

            # D. 智能等待：监控登录跳转与中间页
            print("\n⏳ 正在等待系统响应 (最长等待 60秒)...")
            max_wait = 60
            found_target = False

            for i in range(max_wait):
                # 情况 A: 出现中间页的 "WEB" 按钮
                web_btn = page.ele('text:WEB')

                if web_btn and web_btn.states.is_displayed:
                    print(f"   👀 第 {i+1}秒: 检测到中间页 'WEB' 按钮！")
                    print("   👉 正在点击 'WEB' 进入系统...")
                    web_btn.click(by_js=True)
                    time.sleep(1)
                    continue

                # 情况 B: 已经成功到达首页 (index.html)
                if "mainController/index.html" in page.url:
                    print(f"   ✅ 第 {i+1}秒: 成功抵达首页！")
                    found_target = True
                    break

                # 情况 C: 还在登录页（可能卡住了）
                if page.ele('#loginPwd') and i > 10:
                    print("   ⚠️ 似乎还停留在登录页，尝试补按一次回车...")
                    page.ele('#loginPwd').input('\n')

                # 还没刷出来，打印个点，等1秒
                print(".", end="", flush=True)
                time.sleep(1)

            print("\n")

            # E. 最终验证
            if found_target or "index.html" in page.url:
                print(f"🎉 登录成功！当前页面标题: {page.title}")
                self.log("登录成功", "SUCCESS")
                return True
            else:
                print("❌ 登录超时！")
                self.log("登录超时", "ERROR")
                return False

        except Exception as e:
            print(f"❌ 登录操作出错: {e}")
            self.log(f"登录失败: {e}", "ERROR")
            return False

    def check_login_required(self, page: ChromiumPage) -> bool:
        """
        检查是否需要登录

        Args:
            page: 浏览器页面对象

        Returns:
            bool: 是否需要登录
        """
        return page.ele('#loginPwd') is not None


if __name__ == "__main__":
    # 测试代码
    print("🧪 登录管理器测试")
    print("="*60)

    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.config_loader import load_config
    from ..core.browser_handler import BrowserHandler

    config_loader = load_config()
    credentials = config_loader.get_credentials()
    paths = config_loader.get_paths()

    login_manager = LoginManager(credentials)
    browser = BrowserHandler(user_data_path=paths['user_data_path'])

    if browser.connect():
        page = browser.get_page()

        if login_manager.check_login_required(page):
            print("检测到需要登录")
            success = login_manager.perform_login(page)
            print(f"登录结果: {'成功' if success else '失败'}")
        else:
            print("已经登录，无需重复登录")
    else:
        print("❌ 无法连接到浏览器")

    print("\n✅ 测试完成")

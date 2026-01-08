# -*- coding: utf-8 -*-
"""
浏览器处理模块
统一管理浏览器的初始化、连接和会话管理
"""
from DrissionPage import ChromiumPage, ChromiumOptions
import os
from typing import Optional
from .logger import get_logger


class BrowserHandler:
    """浏览器处理器类"""

    def __init__(self, user_data_path: str = None, local_port: int = 9222):
        """
        初始化浏览器处理器

        Args:
            user_data_path: 用户数据目录路径（用于保持登录状态）
            local_port: Chrome调试端口（默认9222）
        """
        self.user_data_path = user_data_path
        self.local_port = local_port
        self.page: Optional[ChromiumPage] = None
        self.log = get_logger()

    def connect(self) -> bool:
        """
        连接到浏览器会话

        Returns:
            bool: 连接是否成功
        """
        try:
            co = ChromiumOptions()

            if self.user_data_path and os.path.exists(self.user_data_path):
                co.set_user_data_path(self.user_data_path)

            co.set_local_port(self.local_port)

            self.page = ChromiumPage(co)
            self.log("浏览器连接成功", "SUCCESS")
            return True

        except Exception as e:
            self.log(f"浏览器连接失败: {e}", "ERROR")
            print(f"❌ 浏览器连接失败: {e}")
            return False

    def get_page(self) -> Optional[ChromiumPage]:
        """
        获取浏览器页面对象

        Returns:
            ChromiumPage: 页面对象，如果未连接则返回None
        """
        return self.page

    def is_connected(self) -> bool:
        """
        检查是否已连接到浏览器

        Returns:
            bool: 是否已连接
        """
        return self.page is not None

    def disconnect(self):
        """断开浏览器连接"""
        if self.page:
            try:
                # DrissionPage 不需要显式关闭，但可以重置引用
                self.page = None
                self.log("浏览器连接已断开")
            except Exception as e:
                self.log(f"断开浏览器时出错: {e}", "ERROR")


if __name__ == "__main__":
    # 测试代码
    print("🧪 浏览器处理器测试")
    print("="*60)

    # 从配置加载路径
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.config_loader import load_config

    config = load_config()
    paths = config.get_paths()

    handler = BrowserHandler(user_data_path=paths['user_data_path'])

    print("\n🔌 尝试连接浏览器...")
    if handler.connect():
        print("✅ 连接成功")
        page = handler.get_page()
        print(f"📍 当前URL: {page.url if page else 'None'}")
        print(f"📄 当前标题: {page.title if page else 'None'}")
    else:
        print("❌ 连接失败")

    print("\n✅ 测试完成")

# -*- coding: utf-8 -*-
"""
任务邮件通知模块
用于数据抓取任务的成功/失败通知和汇总报告
"""
import os
import sys
from typing import List

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.base_notifier import BaseNotifier


class TaskNotifier(BaseNotifier):
    """任务邮件通知器

    专门用于数据抓取任务的通知：
    - 任务成功/失败通知
    - 数据抓取汇总报告
    """

    def __init__(self, sender_email: str = None, app_password: str = None,
                 recipients: List[str] = None, config: dict = None):
        """
        初始化任务通知器

        Args:
            sender_email: 发件人邮箱地址
            app_password: Gmail应用专用密码
            recipients: 收件人邮箱列表
            config: 配置字典（如果提供，将从配置中读取上述参数）
        """
        # 如果提供了 config，直接使用
        if config:
            config_dict = config
        elif sender_email or app_password or recipients:
            # 从单独参数构建配置字典
            config_dict = {
                'sender_email': sender_email,
                'app_password': app_password,
                'recipients': recipients or [],
                'sender_name': '航班监控系统'
            }
        else:
            config_dict = None

        # 调用父类初始化
        super().__init__(config_dict=config_dict)


if __name__ == "__main__":
    # 测试代码
    print("🧪 任务通知器测试")
    print("=" * 60)

    # 从配置加载
    from config.config_loader import load_config

    config_loader = load_config()
    gmail_config = config_loader.get_gmail_config()

    notifier = TaskNotifier(config=gmail_config)

    if notifier.is_enabled():
        print("✅ 任务通知器已启用")
        print(f"📧 发件人: {notifier.config['smtp_user']}")
        print(f"📮 收件人: {notifier.config['receiver_email']}")

        # 测试发送邮件（取消注释以测试）
        # success = notifier.send_success_notification(
        #     task_name="数据抓取测试",
        #     data_file=None
        # )
        # print(f"📤 发送结果: {'成功' if success else '失败'}")
    else:
        print("⚠️ 任务通知器未启用")
        print("请在 config.ini 中配置 Gmail 信息")

    print("\n✅ 测试完成")

# -*- coding: utf-8 -*-
"""
航段状态邮件通知模块
专门用于航段(leg)数据的状态变化通知
"""
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.base_notifier import BaseNotifier


class LegStatusNotifier(BaseNotifier):
    """航段状态邮件通知器

    专门用于航段(leg)数据的状态变化通知
    优先从 config.ini 读取配置，兼容旧的 email_config.yaml
    """

    def send_leg_status_notification(self, status_changes: list, date_str: str) -> bool:
        """
        发送航段状态变化通知

        Args:
            status_changes: 状态变化列表，每个元素是状态描述字符串
            date_str: 日期字符串

        Returns:
            bool: 发送是否成功
        """
        if not status_changes:
            return True

        subject = f"航段状态 - {date_str}"
        body = '\n'.join(status_changes)

        return self.send_email(subject, body)


if __name__ == "__main__":
    # 测试代码
    print("🧪 航段状态邮件通知器测试")
    print("=" * 60)

    notifier = LegStatusNotifier()

    if notifier.is_enabled():
        print("✅ 航段状态邮件通知器已启用")
        print(f"📧 发件人: {notifier.config['smtp_user']}")
        print(f"📮 收件人: {notifier.config['receiver_email']}")

        # 测试发送状态通知
        test_changes = [
            "VJ105（河内-昆岛）已滑出",
            "VJ107（河内-昆岛）已起飞，预计1小时55分钟后落地"
        ]

        success = notifier.send_leg_status_notification(test_changes, "2026-01-09")
        print(f"📤 发送结果: {'成功' if success else '失败'}")
    else:
        print("⚠️ 邮件通知器未启用")

    print("\n✅ 测试完成")

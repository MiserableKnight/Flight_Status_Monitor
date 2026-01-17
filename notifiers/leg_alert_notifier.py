"""
航段告警邮件通知模块
专门用于航段(leg)数据的异常状态告警通知
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.base_notifier import BaseNotifier


class LegAlertNotifier(BaseNotifier):
    """航段告警邮件通知器

    专门用于航段(leg)数据的异常状态告警通知
    优先从 config.ini 读取配置，兼容旧的 email_config.yaml
    """

    def send_alert_notification(self, alerts: list, date_str: str) -> bool:
        """
        发送航段告警通知

        Args:
            alerts: 告警列表，每个元素是告警描述字符串
            date_str: 日期字符串

        Returns:
            bool: 发送是否成功
        """
        if not alerts:
            return True

        subject = f"⚠️ 航段告警 - {date_str}"
        body = "\n".join(alerts)

        return self.send_email(subject, body)


if __name__ == "__main__":
    # 测试代码
    print("🧪 航段告警邮件通知器测试")
    print("=" * 60)

    # 从配置加载器获取Gmail配置
    from config.config_loader import load_config

    config_loader = load_config()
    gmail_config = config_loader.get_gmail_config()

    notifier = LegAlertNotifier(config_dict=gmail_config)

    if notifier.is_enabled():
        print("✅ 航段告警邮件通知器已启用")
        print(f"📧 发件人: {notifier.config['smtp_user']}")
        print(f"📮 收件人: {notifier.config['receiver_email']}")

        # 测试发送告警通知
        test_alerts = [
            "B-656E (VJ105) 滑出30分钟仍未起飞。请确认飞机状态。",
            "B-652G (VJ106) 起飞140分钟（计划航程110分钟）仍未落地。请确认飞机状态。",
            "B-656E (VJ118) 落地30分钟仍未停靠。请确认飞机状态。",
        ]

        success = notifier.send_alert_notification(test_alerts, "2026-01-15")
        print(f"📤 发送结果: {'成功' if success else '失败'}")
    else:
        print("⚠️ 邮件通知器未启用")
        print("   请检查环境变量配置：")
        print("   - GMAIL_SENDER_EMAIL")
        print("   - GMAIL_APP_PASSWORD")
        print("   - GMAIL_RECIPIENTS")

    print("\n✅ 测试完成")

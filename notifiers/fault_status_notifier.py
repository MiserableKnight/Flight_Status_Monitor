# -*- coding: utf-8 -*-
"""
故障邮件通知模块
专门用于故障数据的状态变化通知
"""
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.base_notifier import BaseNotifier


class FaultStatusNotifier(BaseNotifier):
    """故障邮件通知器

    专门用于故障数据的状态变化通知
    优先从 config.ini 读取配置，兼容旧的 email_config.yaml
    """

    def send_fault_status_notification(self, fault_summary: str, date_str: str,
                                      attachment: str = None, subject_prefix: str = "") -> bool:
        """
        发送故障状态通知

        Args:
            fault_summary: 故障汇总信息
            date_str: 日期字符串
            attachment: 附件文件路径（可选）
            subject_prefix: 主题前缀（可选），用于标记测试邮件等

        Returns:
            bool: 发送是否成功
        """
        subject = f"{subject_prefix}故障信息报送 - {date_str}" if subject_prefix else f"故障信息报送 - {date_str}"

        attachments = [attachment] if attachment else None

        return self.send_email(subject, fault_summary, attachments)


if __name__ == "__main__":
    # 测试代码
    print("🧪 故障邮件通知器测试")
    print("=" * 60)

    notifier = FaultStatusNotifier()

    if notifier.is_enabled():
        print("✅ 故障邮件通知器已启用")
        print(f"📧 发件人: {notifier.config['smtp_user']}")
        print(f"📮 收件人: {notifier.config['receiver_email']}")

        # 测试发送故障通知
        test_summary = """
故障信息报送 - 2026-01-12
========================

B-656E (VJ108):
  - [324 201 48]AUTOBRAKE DISARM[CAUTION] (17:07:37)
  - ADC1:INTERNAL FAULT (15:00:16)
  - APU FADEC:APU LOW FUEL SUPPLY (14:59:57)

B-652G (VJ106):
  - [324 201 48]AUTOBRAKE DISARM[CAUTION] (15:35:33)
  - TW:TAWS TERR FAULT (15:23:27)

共计: 5条故障记录
        """

        success = notifier.send_fault_status_notification(test_summary, "2026-01-12")
        print(f"📤 发送结果: {'成功' if success else '失败'}")
    else:
        print("⚠️ 邮件通知器未启用")

    print("\n✅ 测试完成")

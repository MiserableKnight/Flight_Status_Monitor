# -*- coding: utf-8 -*-
"""
航班状态邮件通知模块
基于 YAML 配置文件的邮件发送器
"""
import smtplib
import os
import yaml
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.logger import get_logger


class FlightStatusNotifier:
    """航班状态邮件通知器"""

    def __init__(self, config_file=None):
        """
        初始化通知器

        Args:
            config_file: 配置文件路径，默认为项目根目录下的 email_config.yaml
        """
        self.log = get_logger()

        # 确定配置文件路径
        if config_file is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_file = os.path.join(project_root, 'email_config.yaml')

        # 加载配置
        self.config = self._load_config(config_file)

        if self.config:
            self.enabled = True
            self.log("邮件通知器初始化成功")
        else:
            self.enabled = False
            self.log("邮件通知器初始化失败", "WARNING")

    def _load_config(self, config_file):
        """加载 YAML 配置文件"""
        if not os.path.exists(config_file):
            self.log(f"配置文件不存在: {config_file}", "ERROR")
            return None

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 验证必需的配置项
            email_config = config.get('email', {})
            required_fields = ['smtp_server', 'smtp_port', 'smtp_user', 'smtp_password', 'receiver_email']

            for field in required_fields:
                if not email_config.get(field):
                    self.log(f"配置文件缺少必需字段: {field}", "ERROR")
                    return None

            return email_config

        except Exception as e:
            self.log(f"加载配置文件失败: {e}", "ERROR")
            return None

    def is_enabled(self) -> bool:
        """检查邮件通知功能是否启用"""
        return self.enabled

    def send_email(self, subject: str, body: str, attachments: List[str] = None) -> bool:
        """
        发送邮件

        Args:
            subject: 邮件主题
            body: 邮件正文
            attachments: 附件文件路径列表

        Returns:
            bool: 发送是否成功
        """
        if not self.is_enabled():
            self.log("邮件通知功能未启用，跳过发送", "WARNING")
            return False

        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = f"{self.config.get('sender_name', '航班状态监控系统')} <{self.config['smtp_user']}>"
            msg['To'] = self.config['receiver_email']
            msg['Subject'] = subject

            # 添加邮件正文
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # 添加附件
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                        msg.attach(part)
                    else:
                        self.log(f"附件不存在: {file_path}", "WARNING")

            # 连接到SMTP服务器
            smtp_server = self.config['smtp_server']
            smtp_port = self.config['smtp_port']

            if self.config.get('use_ssl', False):
                # SSL连接
                with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                    server.login(self.config['smtp_user'], self.config['smtp_password'])
                    server.send_message(msg)
            else:
                # TLS连接
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(self.config['smtp_user'], self.config['smtp_password'])
                    server.send_message(msg)

            self.log(f"邮件发送成功: {subject}", "SUCCESS")
            return True

        except Exception as e:
            self.log(f"邮件发送失败: {e}", "ERROR")
            print(f"❌ 邮件发送失败: {e}")
            return False

    def send_flight_status_notification(self, status_changes: list, date_str: str) -> bool:
        """
        发送航班状态变化通知

        Args:
            status_changes: 状态变化列表，每个元素是状态描述字符串
            date_str: 日期字符串

        Returns:
            bool: 发送是否成功
        """
        if not status_changes:
            return True

        subject = f"航班状态 - {date_str}"
        body = '\n'.join(status_changes)

        return self.send_email(subject, body)


if __name__ == "__main__":
    # 测试代码
    print("🧪 邮件通知器测试")
    print("=" * 60)

    notifier = FlightStatusNotifier()

    if notifier.is_enabled():
        print("✅ 邮件通知器已启用")
        print(f"📧 发件人: {notifier.config['smtp_user']}")
        print(f"📮 收件人: {notifier.config['receiver_email']}")

        # 测试发送状态通知
        test_changes = [
            "VJ105（河内-昆岛）已滑出",
            "VJ107（河内-昆岛）已起飞，预计1小时55分钟后落地"
        ]

        success = notifier.send_flight_status_notification(test_changes, "2026-01-09")
        print(f"📤 发送结果: {'成功' if success else '失败'}")
    else:
        print("⚠️ 邮件通知器未启用")

    print("\n✅ 测试完成")

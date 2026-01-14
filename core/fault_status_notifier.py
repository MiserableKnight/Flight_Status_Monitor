# -*- coding: utf-8 -*-
"""
故障邮件通知模块
基于 YAML 配置文件的邮件发送器
专门用于故障数据的状态变化通知
"""
import smtplib
import os
import yaml
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.logger import get_logger


class FaultStatusNotifier:
    """故障邮件通知器
    专门用于故障数据的状态变化通知
    优先从 config.ini 读取配置，兼容旧的 email_config.yaml
    """

    def __init__(self, config_file=None, config_dict=None):
        """
        初始化通知器

        Args:
            config_file: 旧的 YAML 配置文件路径（已弃用，仅为向后兼容）
            config_dict: 配置字典（从 config.ini 的 [gmail] 段读取）
        """
        self.log = get_logger()

        # 优先使用 config_dict（新方式：从 config.ini 读取）
        if config_dict:
            self.config = self._load_from_dict(config_dict)
            self.config_source = "config.ini"
        else:
            # 回退到 YAML 文件（旧方式：向后兼容）
            self.config = self._load_from_yaml(config_file)
            self.config_source = "email_config.yaml"

        if self.config:
            self.enabled = True
            self.log(f"邮件通知器初始化成功（配置来源: {self.config_source}）")
        else:
            self.enabled = False
            self.log("邮件通知器初始化失败", "WARNING")

        # 邮件发送频率控制
        self.last_send_time = 0
        self.min_send_interval = 30  # 最小发送间隔(秒),避免Gmail限流

    def _load_from_dict(self, config_dict: dict) -> dict:
        """从配置字典加载（新方式）"""
        if not config_dict:
            return None

        # 映射 config.ini 的字段名到内部格式
        mapped_config = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_user': config_dict.get('sender_email', ''),
            'smtp_password': config_dict.get('app_password', ''),
            'receiver_email': ', '.join(config_dict.get('recipients', [])),
            'sender_name': config_dict.get('sender_name', '航班监控系统'),
            'use_ssl': False,
            'use_tls': True
        }

        # 验证必需字段
        if not mapped_config['smtp_user'] or not mapped_config['smtp_password']:
            self.log("配置缺少必需字段: sender_email 或 app_password", "ERROR")
            return None

        return mapped_config

    def _load_from_yaml(self, config_file):
        """从 YAML 配置文件加载（旧方式，向后兼容）"""
        if config_file is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_file = os.path.join(project_root, 'email_config.yaml')

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

            print(f"📧 正在连接SMTP服务器: {smtp_server}:{smtp_port}")
            print(f"📤 发件人: {self.config['smtp_user']}")
            print(f"📥 收件人: {self.config['receiver_email']}")

            if self.config.get('use_ssl', False):
                # SSL连接
                with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                    server.login(self.config['smtp_user'], self.config['smtp_password'])
                    server.send_message(msg)
                    print(f"✅ 邮件已通过SSL发送")
            else:
                # TLS连接
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(self.config['smtp_user'], self.config['smtp_password'])
                    server.send_message(msg)
                    print(f"✅ 邮件已通过TLS发送")

            self.log(f"邮件发送成功: {subject}", "SUCCESS")
            return True

        except Exception as e:
            self.log(f"邮件发送失败: {e}", "ERROR")
            print(f"❌ 邮件发送失败: {e}")
            return False

    def send_fault_status_notification(self, fault_summary: str, date_str: str, attachment: str = None, subject_prefix: str = "") -> bool:
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

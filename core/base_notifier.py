# -*- coding: utf-8 -*-
"""
邮件通知器基类

提供通用的邮件发送功能：
- 配置管理（支持 config.ini 和 YAML）
- 邮件发送（支持 SSL/TLS）
- 附件处理
- 频率控制

子类只需实现：
- 专用的通知方法（如 send_leg_status_notification）
"""
import smtplib
import os
import yaml
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from .logger import get_logger


class BaseNotifier(ABC):
    """
    邮件通知器基类

    提供通用的邮件发送功能，子类实现具体的业务通知方法
    """

    def __init__(self, config_file=None, config_dict=None):
        """
        初始化通知器

        Args:
            config_file: YAML 配置文件路径（向后兼容）
            config_dict: 配置字典（从 config.ini 读取）
        """
        self.log = get_logger()
        self.last_send_time = 0
        self.min_send_interval = 30  # 最小发送间隔(秒),避免Gmail限流

        # 加载配置
        if config_dict:
            self.config = self._load_from_dict(config_dict)
            self.config_source = "config.ini"
        else:
            self.config = self._load_from_yaml(config_file)
            self.config_source = "email_config.yaml"

        # 检查配置
        if self.config:
            self.enabled = True
            self.log(f"邮件通知器初始化成功（配置来源: {self.config_source}）")
        else:
            self.enabled = False
            self.log("邮件通知器初始化失败", "WARNING")

    def _load_from_dict(self, config_dict: dict) -> dict:
        """
        从配置字典加载（新方式：从 config.ini 读取）

        Args:
            config_dict: 配置字典

        Returns:
            dict: 映射后的配置
        """
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
        """
        从 YAML 配置文件加载（旧方式：向后兼容）

        Args:
            config_file: YAML 配置文件路径

        Returns:
            dict: 邮件配置
        """
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
        """
        检查邮件通知功能是否启用

        Returns:
            bool: 是否启用
        """
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

    def _get_current_time(self) -> str:
        """
        获取当前时间字符串

        Returns:
            str: 格式化的时间字符串
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def send_success_notification(self, task_name: str, data_file: str = None) -> bool:
        """
        发送任务成功通知

        Args:
            task_name: 任务名称
            data_file: 数据文件路径（可选）

        Returns:
            bool: 发送是否成功
        """
        subject = f"✅ {task_name} 执行成功"
        body = f"""
任务名称: {task_name}
执行时间: {self._get_current_time()}

数据抓取任务已成功完成。

"""

        if data_file and os.path.exists(data_file):
            body += f"数据文件: {os.path.basename(data_file)}\n"
            body += f"文件路径: {data_file}\n"
            return self.send_email(subject, body, attachments=[data_file])
        else:
            return self.send_email(subject, body)

    def send_error_notification(self, task_name: str, error_message: str) -> bool:
        """
        发送任务失败通知

        Args:
            task_name: 任务名称
            error_message: 错误信息

        Returns:
            bool: 发送是否成功
        """
        subject = f"❌ {task_name} 执行失败"
        body = f"""
任务名称: {task_name}
执行时间: {self._get_current_time()}

任务执行过程中发生错误:

{error_message}

请检查系统日志获取详细信息。
"""

        return self.send_email(subject, body)

    def send_summary_report(self, report_data: dict) -> bool:
        """
        发送汇总报告

        Args:
            report_data: 报告数据字典

        Returns:
            bool: 发送是否成功
        """
        subject = f"📊 数据抓取汇总报告 - {report_data.get('date', '')}"

        body_lines = [
            f"数据抓取汇总报告",
            f"报告日期: {report_data.get('date', '')}",
            f"",
            f"【航班数据】",
            f"  抓取次数: {report_data.get('flight_fetch_count', 0)}",
            f"  成功次数: {report_data.get('flight_success_count', 0)}",
            f"  失败次数: {report_data.get('flight_failure_count', 0)}",
            f"",
            f"【故障数据】",
            f"  抓取次数: {report_data.get('faults_fetch_count', 0)}",
            f"  成功次数: {report_data.get('faults_success_count', 0)}",
            f"  失败次数: {report_data.get('faults_failure_count', 0)}",
            f"",
            f"【累计数据】",
            f"  航班累计飞行时间: {report_data.get('total_air_time', 'N/A')} 小时",
            f"  航班累计轮挡时间: {report_data.get('total_block_time', 'N/A')} 小时",
            f"  故障累计记录数: {report_data.get('total_faults_count', 'N/A')} 条",
        ]

        body = '\n'.join(body_lines)

        # 添加附件
        attachments = []
        for key in ['flight_data_file', 'faults_data_file']:
            file_path = report_data.get(key)
            if file_path and os.path.exists(file_path):
                attachments.append(file_path)

        return self.send_email(subject, body, attachments=attachments)

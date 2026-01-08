# -*- coding: utf-8 -*-
"""
Gmail邮件通知模块
基于用户提供的邮件发送器优化
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional
from .logger import get_logger


class GmailNotifier:
    """Gmail邮件通知器类"""

    def __init__(self, sender_email: str = None, app_password: str = None,
                 recipients: List[str] = None, config: dict = None):
        """
        初始化Gmail通知器

        Args:
            sender_email: 发件人邮箱地址
            app_password: Gmail应用专用密码
            recipients: 收件人邮箱列表
            config: 配置字典（如果提供，将从配置中读取上述参数）
        """
        self.log = get_logger()

        if config:
            self.sender_email = config.get('sender_email', '')
            self.app_password = config.get('app_password', '')
            self.recipients = config.get('recipients', [])
        else:
            self.sender_email = sender_email or ''
            self.app_password = app_password or ''
            self.recipients = recipients or []

        # 检查配置完整性
        if not self.sender_email or not self.app_password:
            self.log("Gmail配置不完整，邮件通知功能将被禁用", "WARNING")
            self.enabled = False
        else:
            self.enabled = True

    def is_enabled(self) -> bool:
        """
        检查邮件通知功能是否启用

        Returns:
            bool: 是否启用
        """
        return self.enabled and bool(self.sender_email and self.app_password)

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
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipients) if self.recipients else self.sender_email
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

            # 连接到Gmail SMTP服务器
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()  # 启用TLS
                server.login(self.sender_email, self.app_password)
                server.send_message(msg)

            self.log(f"邮件发送成功: {subject}", "SUCCESS")
            return True

        except Exception as e:
            self.log(f"邮件发送失败: {e}", "ERROR")
            print(f"❌ 邮件发送失败: {e}")
            return False

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

    def _get_current_time(self) -> str:
        """
        获取当前时间字符串

        Returns:
            str: 格式化的时间字符串
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    # 测试代码
    print("🧪 Gmail通知器测试")
    print("="*60)

    # 从配置加载
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.config_loader import load_config

    config_loader = load_config()
    gmail_config = config_loader.get_gmail_config()

    notifier = GmailNotifier(config=gmail_config)

    if notifier.is_enabled():
        print("✅ Gmail通知器已启用")
        print(f"📧 发件人: {notifier.sender_email}")
        print(f"📮 收件人: {', '.join(notifier.recipients)}")

        # 测试发送邮件（取消注释以测试）
        # success = notifier.send_email(
        #     subject="测试邮件",
        #     body="这是一封测试邮件，请忽略。"
        # )
        # print(f"📤 发送结果: {'成功' if success else '失败'}")
    else:
        print("⚠️ Gmail通知器未启用")
        print("请在 config.ini 中配置 Gmail 信息")

    print("\n✅ 测试完成")

# -*- coding: utf-8 -*-
"""
状态监控基类

提供通用的状态监控功能，包括：
- 状态文件管理（读取/保存）
- 哈希对比机制
- 邮件通知流程
- 数据文件读取

子类需要实现：
- get_data_file_path(): 获取数据文件路径
- get_status_file_path(): 获取状态文件路径
- generate_content(): 生成通知内容
- get_content_hash(): 获取内容哈希值
- send_notification(): 发送通知
"""
import os
import sys
import json
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
import pandas as pd

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.logger import get_logger
from config.config_loader import load_config


class BaseStatusMonitor(ABC):
    """
    状态监控基类

    实现了通用的监控流程：
    1. 读取数据文件
    2. 生成通知内容
    3. 对比状态哈希
    4. 发送通知（如果状态变化）
    5. 保存当前状态
    """

    def __init__(self, target_date=None):
        """
        初始化监控器

        Args:
            target_date: 目标日期（YYYY-MM-DD格式），默认为今天
        """
        self.target_date = target_date or datetime.now().strftime('%Y-%m-%d')
        self.log = get_logger()
        self.config_loader = load_config()
        self.gmail_config = self.config_loader.get_gmail_config()

        # 确保数据目录存在
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """确保数据目录存在"""
        data_dir = os.path.join(project_root, 'data')
        os.makedirs(data_dir, exist_ok=True)

    @abstractmethod
    def get_data_file_path(self):
        """
        获取数据文件路径

        子类必须实现此方法，返回要监控的数据文件路径

        Returns:
            str: 数据文件的完整路径
        """
        pass

    @abstractmethod
    def get_status_file_path(self):
        """
        获取状态文件路径

        子类必须实现此方法，返回用于存储上次状态的状态文件路径

        Returns:
            str: 状态文件的完整路径
        """
        pass

    @abstractmethod
    def generate_content(self, df):
        """
        生成通知内容

        子类必须实现此方法，根据数据生成通知内容

        Args:
            df: 数据DataFrame

        Returns:
            通知内容（格式由子类定义）
        """
        pass

    @abstractmethod
    def get_content_hash(self, content):
        """
        获取内容的哈希值

        子类必须实现此方法，生成内容的唯一标识

        Args:
            content: generate_content() 返回的内容

        Returns:
            str: MD5 哈希值
        """
        pass

    @abstractmethod
    def send_notification(self, content):
        """
        发送通知

        子类必须实现此方法，发送通知

        Args:
            content: 通知内容

        Returns:
            bool: 发送成功返回 True，否则返回 False
        """
        pass

    def read_data_file(self):
        """
        读取数据文件

        Returns:
            pd.DataFrame: 数据DataFrame，读取失败返回 None
        """
        data_file = self.get_data_file_path()

        if not os.path.exists(data_file):
            self.log(f"数据文件不存在: {data_file}", "ERROR")
            print(f"❌ 错误：找不到数据文件 {data_file}")
            return None

        try:
            df = pd.read_csv(data_file)
            print(f"   ✅ 读取到 {len(df)} 行数据")
            return df
        except Exception as e:
            self.log(f"读取数据文件失败: {e}", "ERROR")
            print(f"❌ 读取数据文件失败：{e}")
            return None

    def load_last_status(self):
        """
        加载上次保存的状态

        Returns:
            dict: 状态字典，如果文件不存在或读取失败返回 None
        """
        status_file = self.get_status_file_path()

        if not os.path.exists(status_file):
            return None

        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
                print(f"   📋 上次状态已加载")
                return status_data
        except Exception as e:
            print(f"   ⚠️ 读取上次状态失败: {e}")
            self.log(f"读取状态文件失败: {e}", "WARNING")
            return None

    def save_current_status(self, status_hash, **metadata):
        """
        保存当前状态

        Args:
            status_hash: 当前状态的哈希值
            **metadata: 额外的元数据（如通知内容、数据量等）
        """
        status_file = self.get_status_file_path()

        try:
            os.makedirs(os.path.dirname(status_file), exist_ok=True)

            status_data = {
                'status_hash': status_hash,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'date': self.target_date,
                **metadata
            }

            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)

            print(f"   💾 已保存当前状态")
            self.log(f"状态已保存: {status_file}")
        except Exception as e:
            print(f"   ⚠️ 保存状态失败: {e}")
            self.log(f"保存状态文件失败: {e}", "WARNING")

    def has_status_changed(self, current_hash, last_status):
        """
        检查状态是否发生变化

        Args:
            current_hash: 当前状态的哈希值
            last_status: 上次的状态字典

        Returns:
            bool: 状态变化返回 True，否则返回 False
        """
        if last_status is None:
            print(f"   ✅ 首次运行，需要发送通知")
            return True

        last_hash = last_status.get('status_hash')
        print(f"   📊 上次状态哈希: {last_hash}")
        print(f"   📊 当前状态哈希: {current_hash}")

        if current_hash == last_hash:
            print(f"\n   ℹ️ 状态无变化，跳过通知")
            self.log("状态无变化，跳过通知")
            return False

        print(f"\n   ✅ 检测到状态变化")
        return True

    def monitor(self):
        """
        执行监控流程

        这是模板方法，定义了完整的监控流程：
        1. 读取数据文件
        2. 生成通知内容
        3. 加载上次状态
        4. 对比哈希值
        5. 发送通知（如果状态变化）
        6. 保存当前状态

        Returns:
            bool: 监控成功返回 True，否则返回 False
        """
        print(f"📅 监控日期：{self.target_date}")

        # 1. 读取数据文件
        print("\n📂 读取数据文件...")
        df = self.read_data_file()
        if df is None:
            return False

        # 2. 生成通知内容
        print("\n📊 生成通知内容...")
        try:
            content = self.generate_content(df)
            if not content:
                print("   ℹ️ 无通知内容")
                return True
        except Exception as e:
            print(f"❌ 生成通知内容失败：{e}")
            self.log(f"生成通知内容失败: {e}", "ERROR")
            return False

        # 3. 计算当前状态哈希
        current_hash = self.get_content_hash(content)
        print(f"   🔐 当前状态哈希: {current_hash}")

        # 4. 加载上次状态
        print("\n📋 加载上次状态...")
        last_status = self.load_last_status()

        # 5. 对比状态，检查是否需要发送通知
        if not self.has_status_changed(current_hash, last_status):
            return True

        # 6. 发送通知
        print("\n📧 发送通知...")
        try:
            success = self.send_notification(content)
            if success:
                print(f"   ✅ 通知发送成功")

                # 7. 保存当前状态
                self.save_current_status(
                    current_hash,
                    content=content if isinstance(content, str) else None
                )
                return True
            else:
                print(f"   ⚠️ 通知发送失败")
                return False
        except Exception as e:
            print(f"❌ 发送通知失败：{e}")
            self.log(f"发送通知失败: {e}", "ERROR")
            return False

    def run(self):
        """
        运行监控（供外部调用的入口方法）

        Returns:
            bool: 成功返回 True，失败返回 False
        """
        try:
            return self.monitor()
        except Exception as e:
            print(f"❌ 监控执行失败：{e}")
            self.log(f"监控执行失败: {e}", "ERROR")
            return False

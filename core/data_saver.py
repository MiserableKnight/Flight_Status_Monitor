"""
数据保存器

专门处理数据持久化和备份管理
职责：
- CSV文件保存
- 备份文件管理
- 旧备份清理
"""

import csv
import os
import shutil
from datetime import datetime

from config.constants import DEFAULT_BACKUP_KEEP_COUNT


class DataSaver:
    """数据保存器 - 处理CSV保存和备份管理"""

    def __init__(self, base_dir: str, logger):
        """
        初始化数据保存器

        Args:
            base_dir: 项目根目录
            logger: 日志记录器
        """
        self.base_dir = base_dir
        self.backup_dir = os.path.join(base_dir, "data", "backup")
        self.log = logger

    def save_csv(
        self, data: list, filename: str, subdir: str = "data/daily_raw", needs_backup: bool = False
    ) -> str:
        """
        保存数据到CSV文件

        Args:
            data: 要保存的数据（二维列表）
            filename: 文件名
            subdir: 子目录名
            needs_backup: 是否需要备份（仅对总表文件）

        Returns:
            str: 保存成功返回文件路径，失败返回 None
        """
        if not data:
            print("   ❌ 没有数据可保存")
            return None

        # 确保目录存在
        data_dir = os.path.join(self.base_dir, subdir)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            print(f"   📁 创建文件夹: {data_dir}")

        filepath = os.path.join(data_dir, filename)

        # 备份策略：只备份 data/leg_data.csv 总表
        if needs_backup and os.path.exists(filepath):
            self._create_backup(filepath, filename)

        try:
            # 使用 'w' 模式覆盖写入
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerows(data)
            print(f"\n✅ 数据已保存到: {filepath}")
            return filepath
        except Exception as e:
            print(f"   ❌ 保存CSV失败: {e}")
            return None

    def _create_backup(self, filepath: str, filename: str):
        """
        创建备份文件

        Args:
            filepath: 原文件路径
            filename: 文件名
        """
        # 确保备份目录存在
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

        # 生成带时间戳的备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(filename)
        backup_filename = f"{name}_{timestamp}{ext}"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        try:
            # 先备份当前文件
            shutil.copy2(filepath, backup_path)
            print(f"   💾 已备份总表: {backup_path}")

            # 清理旧备份，只保留最新的N个
            self._cleanup_old_backups(name, ext, DEFAULT_BACKUP_KEEP_COUNT)

        except Exception as e:
            print(f"   ⚠️ 备份失败: {e}")

    def _cleanup_old_backups(self, base_name: str, extension: str, keep_count: int):
        """
        清理旧备份文件，只保留最新的几个

        Args:
            base_name: 文件基础名称（如 'leg_data'）
            extension: 文件扩展名（如 '.csv'）
            keep_count: 保留的备份数量
        """
        try:
            # 获取所有匹配的备份文件
            backup_files = []

            for filename in os.listdir(self.backup_dir):
                if filename.startswith(f"{base_name}_") and filename.endswith(extension):
                    filepath = os.path.join(self.backup_dir, filename)
                    # 获取文件修改时间
                    mtime = os.path.getmtime(filepath)
                    backup_files.append((filepath, mtime, filename))

            # 按修改时间排序（最新的在前）
            backup_files.sort(key=lambda x: x[1], reverse=True)

            # 如果文件数量超过保留数量，删除旧的
            if len(backup_files) > keep_count:
                files_to_delete = backup_files[keep_count:]
                for filepath, _, filename in files_to_delete:
                    os.remove(filepath)
                    print(f"   🗑️  删除旧备份: {filename}")

        except Exception as e:
            print(f"   ⚠️ 清理旧备份失败: {e}")

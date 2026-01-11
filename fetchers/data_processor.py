# -*- coding: utf-8 -*-
"""
数据处理模块
负责CSV文件的更新、累计值计算和备份
"""
import csv
import os
import shutil
from datetime import datetime
from typing import List, Dict, Optional
from ..core.logger import get_logger


class DataProcessor:
    """数据处理器类"""

    def __init__(self, data_dir: str = "data", backup_dir: str = "data/backup",
                 daily_raw_dir: str = "data/daily_raw"):
        """
        初始化数据处理器

        Args:
            data_dir: 主数据目录
            backup_dir: 备份目录
            daily_raw_dir: 每日原始数据目录
        """
        self.data_dir = data_dir
        self.backup_dir = backup_dir
        self.daily_raw_dir = daily_raw_dir
        self.log = get_logger()

        # 确保目录存在
        self._ensure_directories()

    def _ensure_directories(self):
        """确保所有必需的目录都存在"""
        for directory in [self.data_dir, self.backup_dir, self.daily_raw_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                self.log(f"创建目录: {directory}")

    def save_daily_raw_data(self, data: List[List[str]], filename: str) -> Optional[str]:
        """
        保存每日原始数据

        Args:
            data: CSV数据（包含表头）
            filename: 文件名

        Returns:
            str: 保存的文件路径，失败返回None
        """
        if not data:
            self.log("没有数据可保存", "WARNING")
            return None

        filepath = os.path.join(self.daily_raw_dir, filename)

        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerows(data)

            self.log(f"原始数据已保存: {filepath}", "SUCCESS")
            return filepath

        except Exception as e:
            self.log(f"保存原始数据失败: {e}", "ERROR")
            return None

    def load_csv_data(self, filepath: str) -> Optional[List[List[str]]]:
        """
        加载CSV数据

        Args:
            filepath: CSV文件路径

        Returns:
            List[List[str]]: CSV数据，失败返回None
        """
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                data = list(reader)
            return data
        except Exception as e:
            self.log(f"加载CSV失败: {e}", "ERROR")
            return None

    def append_to_master_file(self, data: List[str], master_filename: str) -> bool:
        """
        将数据追加到主文件

        Args:
            data: 单行数据（不包含表头）
            master_filename: 主文件名

        Returns:
            bool: 是否成功
        """
        master_path = os.path.join(self.data_dir, master_filename)

        try:
            # 检查文件是否存在，不存在则创建并写入表头
            file_exists = os.path.exists(master_path)

            with open(master_path, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)

                # 如果文件不存在，写入表头（假设data第一行是表头）
                if not file_exists and len(data) > 0:
                    # 这里假设调用者会处理表头
                    pass

                writer.writerow(data)

            self.log(f"数据已追加到主文件: {master_path}")
            return True

        except Exception as e:
            self.log(f"追加数据失败: {e}", "ERROR")
            return False

    def calculate_cumulative_values(self, master_filename: str,
                                    air_time_col: int = 0, block_time_col: int = 1) -> Dict[str, float]:
        """
        计算累计值（例如累计飞行时间）

        Args:
            master_filename: 主文件名
            air_time_col: 飞行时间列索引
            block_time_col: 轮挡时间列索引

        Returns:
            Dict[str, float]: {'total_air_time': x, 'total_block_time': y}
        """
        master_path = os.path.join(self.data_dir, master_filename)

        if not os.path.exists(master_path):
            return {'total_air_time': 0.0, 'total_block_time': 0.0}

        try:
            total_air_time = 0.0
            total_block_time = 0.0

            with open(master_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None)  # 跳过表头

                for row in reader:
                    if len(row) > max(air_time_col, block_time_col):
                        try:
                            if row[air_time_col]:
                                total_air_time += float(row[air_time_col])
                            if row[block_time_col]:
                                total_block_time += float(row[block_time_col])
                        except ValueError:
                            continue

            return {
                'total_air_time': round(total_air_time, 2),
                'total_block_time': round(total_block_time, 2)
            }

        except Exception as e:
            self.log(f"计算累计值失败: {e}", "ERROR")
            return {'total_air_time': 0.0, 'total_block_time': 0.0}

    def backup_file(self, filepath: str) -> Optional[str]:
        """
        备份文件

        Args:
            filepath: 要备份的文件路径

        Returns:
            str: 备份文件路径，失败返回None
        """
        if not os.path.exists(filepath):
            self.log(f"文件不存在，无法备份: {filepath}", "WARNING")
            return None

        try:
            # 生成备份文件名（添加时间戳）
            filename = os.path.basename(filepath)
            name, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{name}_{timestamp}{ext}"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            # 复制文件
            shutil.copy2(filepath, backup_path)

            self.log(f"文件已备份: {backup_path}", "SUCCESS")
            return backup_path

        except Exception as e:
            self.log(f"备份失败: {e}", "ERROR")
            return None

    def cleanup_old_daily_raw(self, days: int = 30):
        """
        清理过期的每日原始数据文件

        Args:
            days: 保留天数
        """
        if not os.path.exists(self.daily_raw_dir):
            return

        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)

        for filename in os.listdir(self.daily_raw_dir):
            if not filename.endswith(".csv"):
                continue

            filepath = os.path.join(self.daily_raw_dir, filename)

            if os.path.getmtime(filepath) < cutoff_time:
                try:
                    os.remove(filepath)
                    self.log(f"已删除过期原始数据: {filename}")
                except Exception as e:
                    self.log(f"删除文件失败 {filename}: {e}", "ERROR")

    def get_latest_file_info(self, pattern: str = "*.csv") -> Optional[Dict[str, str]]:
        """
        获取最新的文件信息

        Args:
            pattern: 文件匹配模式

        Returns:
            Dict[str, str]: {'filename': xxx, 'path': xxx, 'mtime': xxx}
        """
        import glob

        files = glob.glob(os.path.join(self.daily_raw_dir, pattern))

        if not files:
            return None

        # 按修改时间排序
        latest_file = max(files, key=os.path.getmtime)

        return {
            'filename': os.path.basename(latest_file),
            'path': latest_file,
            'mtime': datetime.fromtimestamp(os.path.getmtime(latest_file)).strftime("%Y-%m-%d %H:%M:%S")
        }


if __name__ == "__main__":
    # 测试代码
    print("🧪 数据处理器测试")
    print("="*60)

    processor = DataProcessor()

    # 测试数据
    test_data = [
        ['air_time', 'block_time', 'fc', 'flight_leg'],
        ['10.5', '12.3', 'C909', 'SHA-PEK'],
        ['8.2', '9.8', 'C909', 'PEK-SHA']
    ]

    # 保存原始数据
    print("\n📝 测试保存原始数据...")
    filepath = processor.save_daily_raw_data(test_data, "test_data.csv")
    print(f"保存路径: {filepath}")

    # 读取数据
    if filepath:
        print("\n📖 测试读取数据...")
        loaded_data = processor.load_csv_data(filepath)
        print(f"数据行数: {len(loaded_data) if loaded_data else 0}")

    # 备份文件
    if filepath:
        print("\n💾 测试备份文件...")
        backup_path = processor.backup_file(filepath)
        print(f"备份路径: {backup_path}")

    # 获取最新文件
    print("\n🔍 测试获取最新文件...")
    latest = processor.get_latest_file_info()
    if latest:
        print(f"最新文件: {latest['filename']}")
        print(f"修改时间: {latest['mtime']}")

    print("\n✅ 测试完成")

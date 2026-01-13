# -*- coding: utf-8 -*-
"""
故障数据清理和保存器

负责故障数据的清理、标准化和保存
"""
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class FaultDataSaver:
    """故障数据清理和保存器"""

    def __init__(self, project_root: str):
        """
        初始化数据保存器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = project_root
        self.data_dir = Path(project_root) / "data" / "daily_raw"

    @staticmethod
    def normalize_flight_number(flight_num) -> str:
        """
        统一航班号格式，将EU改为VJ

        Args:
            flight_num: 原始航班号

        Returns:
            str: 标准化后的航班号
        """
        if not flight_num or flight_num == '':
            return flight_num

        flight_num = str(flight_num).strip().upper()
        # 移除EU和VJ前缀
        match = flight_num.replace('EU', '').replace('VJ', '')

        if match.isdigit():
            return f'VJ{match}'
        return flight_num

    @staticmethod
    def clean_time_field(time_str) -> str:
        """
        清理时间字段，移除日期部分，只保留时间

        Args:
            time_str: 原始时间字符串，可能包含日期

        Returns:
            str: 只包含时间部分的字符串（HH:MM:SS）
        """
        if not time_str or time_str == '':
            return time_str

        time_str = str(time_str).strip()

        # 如果包含空格，取时间部分（空格后的部分）
        if ' ' in time_str:
            return time_str.split(' ')[-1]

        # 如果包含斜杠，取时间部分（斜杠后的部分）
        if '/' in time_str:
            parts = time_str.split('/')
            if len(parts) > 2:
                # 格式如 "2026/1/13 10:17:50" 或 "2026/1/13 10:17:50"
                time_part = parts[-1]
                if ' ' in time_part:
                    return time_part.split(' ')[-1]
                return time_part

        return time_str

    def save_to_csv(self, data: List[Dict], filename: Optional[str] = None) -> Optional[str]:
        """
        保存故障数据到CSV文件

        优化：
        1. 删除FlightlegId和ReportId列
        2. 清理时间字段（移除日期部分）
        3. 标准化航班号（EU改为VJ）

        Args:
            data: 故障数据列表
            filename: 文件名（可选）

        Returns:
            str: 保存的文件路径，失败返回 None
        """
        if not data:
            print("   ❌ 没有数据可保存")
            return None

        try:
            # 确定保存路径 - 使用 data/daily_raw 文件夹（使用绝对路径）
            today_str = datetime.now().strftime('%Y-%m-%d')
            self.data_dir.mkdir(parents=True, exist_ok=True)

            if filename is None:
                filename = f"fault_data_{today_str}.csv"

            file_path = self.data_dir / filename

            # 定义字段顺序（已删除FlightlegId和ReportId）
            fieldnames = [
                '获取时间', '机号', '机型', '航空公司', '航班号',
                'ATA', '航段', '触发时间', '描述', '故障类型',
                '飞行阶段', '处理状态', '类别-优先权'
            ]

            # 写入CSV文件（覆盖模式）
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # 写入表头
                writer.writeheader()

                # 写入数据行，进行字段映射和数据清理
                for row in data:
                    # 字段映射：原始字段名 -> 实际表头字段名
                    row_data = {
                        '获取时间': self.clean_time_field(row.get('提取时间', '')),
                        '机号': row.get('机号', ''),
                        '机型': row.get('机型', ''),
                        '航空公司': row.get('航空公司', ''),
                        '航班号': self.normalize_flight_number(row.get('航班号', '')),
                        'ATA': row.get('ATA章节', ''),
                        '航段': row.get('航段', ''),
                        '触发时间': self.clean_time_field(row.get('时间', '')),
                        '描述': row.get('故障描述', ''),
                        '故障类型': row.get('故障类型', ''),
                        '飞行阶段': row.get('阶段', ''),
                        '处理状态': row.get('状态', ''),
                        '类别-优先权': row.get('类别-优先权', '')
                    }
                    writer.writerow(row_data)

            print(f"   ✅ 数据已保存到: {file_path}")
            print(f"   📊 共保存 {len(data)} 条记录")
            return str(file_path)

        except Exception as e:
            print(f"   ❌ 保存文件失败: {e}")
            import traceback
            traceback.print_exc()
            return None

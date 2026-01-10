# -*- coding: utf-8 -*-
"""
航班备降检测模块

功能：
- 动态检测航班备降事件
- 基于航班计划配置检测异常
- 支持未知航班、航线异常、起降机场相同等情况
"""
import pandas as pd
from typing import Dict, List, Optional, Tuple
from config.flight_schedule import FlightSchedule


class DiversionDetector:
    """动态备降检测器"""

    # 机场名称映射（用于简化显示）
    AIRPORT_MAPPING = {
        'VVCS-昆仑国际机场': '昆岛',
        'VVNB-内排国际机场': '河内',
        'VVTS-新山一国际机场': '胡志明'
    }

    def __init__(self):
        """初始化备降检测器"""
        # 从 FlightSchedule 加载正常航班配置
        self.normal_flights = FlightSchedule.FLIGHT_SCHEDULES
        self.normal_flight_numbers = set(self.normal_flights.keys())

        # 构建正常城市对映射
        # 格式: {航班号: {(起飞机场, 着陆机场): 航线描述}}
        self.normal_route_pairs = {}
        for flight_num, info in self.normal_flights.items():
            dep = info['departure_airport']  # 如 'VVNB-内排国际机场'
            arr = info['arrival_airport']    # 如 'VVCS-昆仑国际机场'
            self.normal_route_pairs[flight_num] = {
                (dep, arr): info['route']
            }

    @classmethod
    def get_airport_short(cls, airport_full: str) -> str:
        """
        从完整机场名称获取简短名称（与 leg_status_monitor 保持一致）

        Args:
            airport_full: 完整机场名称（如 'VVNB-内排国际机场' 或 'VVCI-海防吉碑国际'）

        Returns:
            str: 简短名称（如 '河内' 或 '海防吉碑'）
        """
        if pd.isna(airport_full):
            return "未知"

        airport_str = str(airport_full)

        # 先查映射表（用于正常机场）
        if airport_str in cls.AIRPORT_MAPPING:
            return cls.AIRPORT_MAPPING[airport_str]

        # 动态解析：从机场代码后的名称中提取
        # 格式: "VVCI-海防吉碑国际" -> 提取 "海防吉碑"
        if '-' in airport_str:
            parts = airport_str.split('-', 1)
            if len(parts) == 2:
                name_part = parts[1]  # "海防吉碑国际"

                # 移除通用后缀（按优先级）
                # "国际机场" -> 移除
                # "机场" -> 移除
                # "国际" -> 移除（仅在"机场"不存在时）
                if name_part.endswith('国际机场'):
                    name_part = name_part[:-4]
                elif name_part.endswith('机场'):
                    name_part = name_part[:-2]
                elif name_part.endswith('国际'):
                    name_part = name_part[:-2]

                return name_part if name_part else airport_str

        # 如果没有 '-'，直接返回
        return airport_str

    def detect_diversion(
        self,
        flight_number: str,
        departure_airport: str,
        arrival_airport: str
    ) -> Optional[Dict]:
        """
        检测是否备降

        Args:
            flight_number: 航班号
            departure_airport: 起飞机场（全名）
            arrival_airport: 着陆机场（全名）

        Returns:
            dict: 备降信息字典，如果不是备降则返回 None
            {
                'is_diversion': bool,
                'diversion_type': str,  # 'unknown_flight', 'route_mismatch', 'same_airport'
                'original_route': str,   # 原计划航线
                'actual_route': str,     # 实际执行航线
                'diversion_airport': str # 备降机场
            }
        """
        # 处理空值
        if pd.isna(departure_airport) or pd.isna(arrival_airport):
            return None

        # 情况1: 未知航班号
        if flight_number not in self.normal_flight_numbers:
            dep_short = self.get_airport_short(departure_airport)
            arr_short = self.get_airport_short(arrival_airport)

            return {
                'is_diversion': True,
                'diversion_type': 'unknown_flight',
                'original_route': '未知',  # 未知航班没有原计划
                'actual_route': f'{dep_short}-{arr_short}',
                'diversion_airport': arr_short
            }

        # 情况2: 起降机场相同（明确备降）
        if departure_airport == arrival_airport:
            original_info = self.normal_flights[flight_number]
            dep_short = self.get_airport_short(departure_airport)

            return {
                'is_diversion': True,
                'diversion_type': 'same_airport',
                'original_route': original_info['route'],
                'actual_route': f'{dep_short}-{dep_short}',
                'diversion_airport': dep_short
            }

        # 情况3: 城市对不匹配
        normal_routes = self.normal_route_pairs.get(flight_number, {})
        actual_pair = (departure_airport, arrival_airport)

        if actual_pair not in normal_routes:
            original_info = self.normal_flights[flight_number]
            dep_short = self.get_airport_short(departure_airport)
            arr_short = self.get_airport_short(arrival_airport)

            return {
                'is_diversion': True,
                'diversion_type': 'route_mismatch',
                'original_route': original_info['route'],
                'actual_route': f'{dep_short}-{arr_short}',
                'diversion_airport': arr_short
            }

        # 正常情况
        return None

    def check_diversion_from_row(self, row: pd.Series) -> Optional[Dict]:
        """
        从数据行检测备降

        Args:
            row: 包含航班信息的数据行

        Returns:
            dict: 备降信息或 None
        """
        flight_number = row.get('航班号', '')
        departure_airport = row.get('起飞机场', '')
        arrival_airport = row.get('着陆机场', '')

        return self.detect_diversion(flight_number, departure_airport, arrival_airport)

    def get_diversion_type_description(self, diversion_type: str) -> str:
        """
        获取备降类型的中文名称

        Args:
            diversion_type: 备降类型代码

        Returns:
            str: 中文名称
        """
        type_map = {
            'unknown_flight': '检测到非计划航班',
            'route_mismatch': '航线异常',
            'same_airport': '起降机场相同'
        }
        return type_map.get(diversion_type, '未知异常')


if __name__ == "__main__":
    # 测试代码
    print("🧪 备降检测器测试")
    print("="*60)

    detector = DiversionDetector()

    # 测试1: 正常航班
    print("\n✅ 测试1: 正常航班 VJ105 (河内->昆岛)")
    result = detector.detect_diversion(
        'VJ105',
        'VVNB-内排国际机场',
        'VVCS-昆仑国际机场'
    )
    print(f"结果: {result if result else '正常，无备降'}")

    # 测试2: 备降海防
    print("\n⚠️ 测试2: VJ105备降海防")
    result = detector.detect_diversion(
        'VJ105',
        'VVNB-内排国际机场',
        'VVCI-海防吉碑国际'
    )
    if result:
        print(f"检测到备降: {detector.get_diversion_type_description(result['diversion_type'])}")
        print(f"原计划: {result['original_route']}")
        print(f"实际执行: {result['actual_route']}")
        print(f"备降机场: {result['diversion_airport']}")

    # 测试3: 起降机场相同
    print("\n⚠️ 测试3: VJ112起降机场相同（胡志明-胡志明）")
    result = detector.detect_diversion(
        'VJ112',
        'VVTS-新山一国际机场',
        'VVTS-新山一国际机场'
    )
    if result:
        print(f"检测到备降: {detector.get_diversion_type_description(result['diversion_type'])}")
        print(f"原计划: {result['original_route']}")
        print(f"实际执行: {result['actual_route']}")
        print(f"备降机场: {result['diversion_airport']}")

    # 测试4: 未知航班
    print("\n⚠️ 测试4: 未知航班号 VJ999")
    result = detector.detect_diversion(
        'VJ999',
        'VVNB-内排国际机场',
        'VVCI-海防吉碑国际'
    )
    if result:
        print(f"检测到备降: {detector.get_diversion_type_description(result['diversion_type'])}")
        print(f"实际执行: {result['actual_route']}")
        print(f"备降机场: {result['diversion_airport']}")

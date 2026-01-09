# -*- coding: utf-8 -*-
"""
航班计划时间配置
所有时间均为越南时间（北京时间-1小时）
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class FlightSchedule:
    """航班计划时间配置"""

    # 航班计划配置
    #
    # ⚠️ 重要：项目中所有时间统一使用北京时间
    # - 配置文件：北京时间
    # - 数据存储：北京时间
    # - 调度逻辑：北京时间
    # - 邮件展示：越南时间（北京时间-1小时）
    #
    # flight_number: 航班号
    # scheduled_departure: 计划起飞时间 (HH:MM, 北京时间)
    # duration_minutes: 计划航程（分钟）
    # route: 航线描述
    # 机场代码: HAN=河内(VVNB), SGN=胡志明(VVTS), VCS=昆岛(VVCS)
    #
    # 时间转换：越南时间 + 1小时 = 北京时间
    FLIGHT_SCHEDULES = {
        'VJ105': {
            'scheduled_departure': '07:45',  # 北京时间 (06:45越南时间 + 1)
            'duration_minutes': 110,
            'route': 'HAN-VCS',  # 河内 → 昆岛
            'departure_airport': 'VVNB-内排国际机场',
            'arrival_airport': 'VVCS-昆仑国际机场'
        },
        'VJ107': {
            'scheduled_departure': '09:15',  # 北京时间 (08:15越南时间 + 1)
            'duration_minutes': 110,
            'route': 'HAN-VCS',  # 河内 → 昆岛
            'departure_airport': 'VVNB-内排国际机场',
            'arrival_airport': 'VVCS-昆仑国际机场'
        },
        'VJ112': {
            'scheduled_departure': '10:20',  # 北京时间 (09:20越南时间 + 1)
            'duration_minutes': 30,
            'route': 'VCS-SGN',  # 昆岛 → 胡志明
            'departure_airport': 'VVCS-昆仑国际机场',
            'arrival_airport': 'VVTS-新山一国际机场'
        },
        'VJ113': {
            'scheduled_departure': '12:00',  # 北京时间 (11:00越南时间 + 1)
            'duration_minutes': 30,
            'route': 'SGN-VCS',  # 胡志明 → 昆岛
            'departure_airport': 'VVTS-新山一国际机场',
            'arrival_airport': 'VVCS-昆仑国际机场'
        },
        'VJ118': {
            'scheduled_departure': '12:00',  # 北京时间 (11:00越南时间 + 1)
            'duration_minutes': 30,
            'route': 'VCS-SGN',  # 昆岛 → 胡志明
            'departure_airport': 'VVCS-昆仑国际机场',
            'arrival_airport': 'VVTS-新山一国际机场'
        },
        'VJ106': {
            'scheduled_departure': '13:05',  # 北京时间 (12:05越南时间 + 1)
            'duration_minutes': 110,
            'route': 'VCS-HAN',  # 昆岛 → 河内
            'departure_airport': 'VVCS-昆仑国际机场',
            'arrival_airport': 'VVNB-内排国际机场'
        },
        'VJ119': {
            'scheduled_departure': '13:30',  # 北京时间 (12:30越南时间 + 1)
            'duration_minutes': 30,
            'route': 'SGN-VCS',  # 胡志明 → 昆岛
            'departure_airport': 'VVTS-新山一国际机场',
            'arrival_airport': 'VVCS-昆仑国际机场'
        },
        'VJ108': {
            'scheduled_departure': '15:00',  # 北京时间 (14:00越南时间 + 1)
            'duration_minutes': 110,
            'route': 'VCS-HAN',  # 昆岛 → 河内
            'departure_airport': 'VVCS-昆仑国际机场',
            'arrival_airport': 'VVNB-内排国际机场'
        }
    }

    @classmethod
    def get_flight_info(cls, flight_number: str) -> Optional[Dict]:
        """获取航班信息"""
        return cls.FLIGHT_SCHEDULES.get(flight_number)

    @classmethod
    def get_all_flights(cls) -> List[str]:
        """获取所有航班号列表"""
        return list(cls.FLIGHT_SCHEDULES.keys())

    @classmethod
    def calculate_scheduled_arrival(cls, flight_number: str, actual_departure_time: datetime) -> datetime:
        """
        根据实际起飞时间计算计划到达时间

        Args:
            flight_number: 航班号
            actual_departure_time: 实际起飞时间（北京时间）

        Returns:
            datetime: 计划到达时间（北京时间）
        """
        flight_info = cls.get_flight_info(flight_number)
        if not flight_info:
            raise ValueError(f"未知航班号: {flight_number}")

        duration = flight_info['duration_minutes']
        return actual_departure_time + timedelta(minutes=duration)

    @classmethod
    def parse_scheduled_time(cls, time_str: str, base_date: datetime = None) -> datetime:
        """
        解析计划时间字符串为datetime对象

        注意：项目中所有时间统一使用北京时间
        - 配置文件中的时间是北京时间
        - 直接使用，不需要转换

        Args:
            time_str: 时间字符串 (HH:MM, 北京时间)
            base_date: 基准日期，默认为今天（北京时间）

        Returns:
            datetime: datetime对象（北京时间）
        """
        if base_date is None:
            base_date = datetime.now()

        hour, minute = map(int, time_str.split(':'))
        # 直接使用配置时间，就是北京时间
        return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    @classmethod
    def get_scheduled_departure_datetime(cls, flight_number: str, base_date: datetime = None) -> datetime:
        """
        获取航班计划起飞时间的datetime对象

        Args:
            flight_number: 航班号
            base_date: 基准日期，默认为今天（北京时间）

        Returns:
            datetime: 计划起飞时间（北京时间）
        """
        flight_info = cls.get_flight_info(flight_number)
        if not flight_info:
            raise ValueError(f"未知航班号: {flight_number}")

        return cls.parse_scheduled_time(flight_info['scheduled_departure'], base_date)

    @classmethod
    def to_vietnam_time(cls, beijing_dt: datetime) -> datetime:
        """
        将北京时间转换为越南时间（用于展示）

        Args:
            beijing_dt: 北京时间

        Returns:
            datetime: 越南时间（北京时间-1小时）
        """
        return beijing_dt - timedelta(hours=1)

    @classmethod
    def format_vietnam_time(cls, beijing_dt: datetime, format_str: str = '%H:%M') -> str:
        """
        格式化北京时间为越南时间字符串（用于邮件展示）

        Args:
            beijing_dt: 北京时间
            format_str: 时间格式字符串

        Returns:
            str: 越南时间字符串
        """
        vietnam_dt = cls.to_vietnam_time(beijing_dt)
        return vietnam_dt.strftime(format_str)


if __name__ == "__main__":
    # 测试代码
    print("🧪 航班计划时间配置测试")
    print("="*60)

    # 显示所有航班信息
    print("\n📋 所有航班计划:")
    print("-"*60)
    for flight_num in FlightSchedule.get_all_flights():
        info = FlightSchedule.get_flight_info(flight_num)
        print(f"{flight_num}:")
        print(f"  计划起飞: {info['scheduled_departure']} (越南时间)")
        print(f"  航程: {info['duration_minutes']}分钟")
        print(f"  航线: {info['route']}")
        print()

    # 测试计划到达时间计算
    print("🧮 计划到达时间计算测试:")
    print("-"*60)
    test_flight = 'VJ105'
    test_departure = datetime(2026, 1, 9, 6, 45)  # 北京时间
    scheduled_arrival = FlightSchedule.calculate_scheduled_arrival(test_flight, test_departure)
    print(f"{test_flight} 实际起飞: {test_departure.strftime('%H:%M')} (北京时间)")
    print(f"{test_flight} 计划到达: {scheduled_arrival.strftime('%H:%M')} (北京时间)")
    print(f"航程: {FlightSchedule.get_flight_info(test_flight)['duration_minutes']}分钟")

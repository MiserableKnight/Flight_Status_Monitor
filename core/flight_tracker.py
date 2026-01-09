# -*- coding: utf-8 -*-
"""
航班状态跟踪器
实时跟踪每架飞机的航班执行状态
"""
import re
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Literal
from pathlib import Path

from config.flight_schedule import FlightSchedule
from core.logger import get_logger


class FlightPhase:
    """航班阶段枚举"""
    SCHEDULED = "scheduled"           # 计划中（未起飞）
    PUSHBACK = "pushback"             # 滑出（已滑出但未起飞）
    AIRBORNE = "airborne"             # 空中（已起飞未落地）
    LANDED = "landed"                 # 落地（已落地未滑入）
    IN_GATE = "in_gate"               # 滑入（已完成）
    UNKNOWN = "unknown"               # 未知状态


class FlightStatus:
    """单个航班状态"""

    def __init__(self, flight_number: str, aircraft_registration: str):
        """
        初始化航班状态

        Args:
            flight_number: 航班号
            aircraft_registration: 机号
        """
        self.flight_number = flight_number
        self.aircraft_registration = aircraft_registration

        # 时间信息
        self.scheduled_departure: Optional[datetime] = None  # 计划起飞时间
        self.scheduled_arrival: Optional[datetime] = None    # 计划到达时间

        self.pushback_time: Optional[datetime] = None        # 实际滑出时间
        self.takeoff_time: Optional[datetime] = None         # 实际起飞时间
        self.landing_time: Optional[datetime] = None         # 实际落地时间
        self.in_gate_time: Optional[datetime] = None         # 实际滑入时间

        # 状态
        self.current_phase = FlightPhase.SCHEDULED
        self.last_update_time: Optional[datetime] = None

        # 邮件通知标记
        self.pushback_notified = False
        self.takeoff_notified = False
        self.landing_notified = False
        self.in_gate_notified = False

    def get_flight_phase(self) -> FlightPhase:
        """
        根据已有时间判断当前航班阶段

        Returns:
            FlightPhase: 当前航班阶段
        """
        if self.in_gate_time:
            return FlightPhase.IN_GATE
        elif self.landing_time:
            return FlightPhase.LANDED
        elif self.takeoff_time:
            return FlightPhase.AIRBORNE
        elif self.pushback_time:
            return FlightPhase.PUSHBACK
        else:
            return FlightPhase.SCHEDULED

    def is_airborne(self) -> bool:
        """判断飞机是否在空中"""
        phase = self.get_flight_phase()
        return phase == FlightPhase.AIRBORNE

    def is_on_ground(self) -> bool:
        """判断飞机是否在地面"""
        phase = self.get_flight_phase()
        return phase in [FlightPhase.SCHEDULED, FlightPhase.PUSHBACK,
                        FlightPhase.LANDED, FlightPhase.IN_GATE]

    def is_completed(self) -> bool:
        """判断航班是否已完成（滑入）"""
        return self.get_flight_phase() == FlightPhase.IN_GATE

    def needs_arrival_monitoring(self, current_time: datetime) -> bool:
        """
        判断是否需要到达监控

        飞机在空中且已到计划到达时间

        Args:
            current_time: 当前时间

        Returns:
            bool: 是否需要监控到达
        """
        if not self.is_airborne():
            return False

        if self.takeoff_time and self.scheduled_arrival:
            return current_time >= self.scheduled_arrival

        return False

    def calculate_scheduled_arrival(self) -> Optional[datetime]:
        """计算计划到达时间"""
        if self.takeoff_time:
            return FlightSchedule.calculate_scheduled_arrival(
                self.flight_number,
                self.takeoff_time
            )
        return None

    def update_status(self, leg_data: Dict):
        """
        根据leg数据更新状态

        Args:
            leg_data: 航段数据字典
        """
        self.last_update_time = datetime.now()

        # 更新时间信息
        if leg_data.get('pushback_time'):
            self.pushback_time = self._parse_datetime(leg_data['pushback_time'])

        if leg_data.get('takeoff_time'):
            self.takeoff_time = self._parse_datetime(leg_data['takeoff_time'])

        if leg_data.get('landing_time'):
            self.landing_time = self._parse_datetime(leg_data['landing_time'])

        if leg_data.get('in_gate_time'):
            self.in_gate_time = self._parse_datetime(leg_data['in_gate_time'])

        # 更新当前阶段
        self.current_phase = self.get_flight_phase()

        # 如果已起飞，计算计划到达时间
        if self.takeoff_time and not self.scheduled_arrival:
            self.scheduled_arrival = self.calculate_scheduled_arrival()

    def _parse_datetime(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        if not time_str or pd.isna(time_str):
            return None
        try:
            # 假设时间格式为 YYYY-MM-DD HH:MM
            return datetime.strptime(time_str, '%Y-%m-%d %H:%M')
        except:
            return None


class FlightTracker:
    """航班状态跟踪器（管理多架飞机的多个航班）"""

    def __init__(self):
        """初始化跟踪器"""
        self.log = get_logger()
        self.flights: Dict[str, FlightStatus] = {}  # {aircraft_registration: FlightStatus}
        self.leg_data_file = Path("data/leg_data.csv")

        # 加载已有的leg数据
        self._load_existing_leg_data()

    def _load_existing_leg_data(self):
        """加载已有的leg数据，初始化航班状态"""
        if not self.leg_data_file.exists():
            return

        try:
            df = pd.read_csv(self.leg_data_file)

            # 按飞机号和日期分组，获取最新状态
            today = datetime.now().strftime('%Y-%m-%d')

            for _, row in df.iterrows():
                aircraft = row.get('aircraft_registration')
                flight_number = row.get('flight_number')

                if not aircraft or not flight_number:
                    continue

                # 只关注今天的航班
                flight_date = row.get('date')
                if flight_date != today:
                    continue

                # 初始化航班状态
                if aircraft not in self.flights:
                    self.flights[aircraft] = FlightStatus(flight_number, aircraft)

                # 更新状态
                leg_data = {
                    'pushback_time': row.get('pushback_time'),
                    'takeoff_time': row.get('takeoff_time'),
                    'landing_time': row.get('landing_time'),
                    'in_gate_time': row.get('in_gate_time')
                }
                self.flights[aircraft].update_status(leg_data)

            self.log(f"已加载 {len(self.flights)} 架飞机的航班状态")

        except Exception as e:
            self.log(f"加载leg数据失败: {e}", "ERROR")

    def get_aircraft_status(self, aircraft_registration: str) -> Optional[FlightStatus]:
        """获取指定飞机的状态"""
        return self.flights.get(aircraft_registration)

    def get_all_aircraft_in_air(self) -> List[str]:
        """获取所有在空中的飞机"""
        return [
            aircraft for aircraft, status in self.flights.items()
            if status.is_airborne()
        ]

    def get_all_aircraft_on_ground(self) -> List[str]:
        """获取所有在地面的飞机"""
        return [
            aircraft for aircraft, status in self.flights.items()
            if status.is_on_ground()
        ]

    def needs_fault_monitoring(self, current_time: datetime) -> bool:
        """
        判断是否应该进行故障监控

        当有任何飞机在空中时，应该监控故障

        Args:
            current_time: 当前时间

        Returns:
            bool: 是否需要故障监控
        """
        airborne_aircraft = self.get_all_aircraft_in_air()
        return len(airborne_aircraft) > 0

    def needs_leg_monitoring(self, current_time: datetime) -> bool:
        """
        判断是否应该进行leg监控

        满足以下任一条件需要leg监控：
        1. 有飞机在地面且已过计划起飞时间
        2. 有飞机需要到达监控（在空中且已到计划到达时间）

        Args:
            current_time: 当前时间

        Returns:
            bool: 是否需要leg监控
        """
        # 检查是否需要到达监控
        for aircraft, status in self.flights.items():
            if status.needs_arrival_monitoring(current_time):
                return True

        # 检查地面飞机是否已过计划起飞时间
        for aircraft, status in self.flights.items():
            if status.is_on_ground():
                scheduled_dept = FlightSchedule.get_scheduled_departure_datetime(
                    status.flight_number
                )
                if current_time >= scheduled_dept:
                    return True

        return False

    def should_monitor_leg_first(self, current_time: datetime) -> bool:
        """
        判断应该优先监控哪个页面

        监控逻辑：
        1. 有飞机在空中且已到计划到达时间 → 监控Leg页面（等待落地/滑入）
        2. 有飞机在地面 且 当前时间已过该飞机的计划起飞时间 → 监控Leg页面
           - 未起飞：等待滑出/起飞
           - 已滑出：等待起飞
           - 已落地：等待滑入
        3. 所有飞机都在空中 → 监控故障页面

        重要：只有在获得起飞时间（OFF）后，才认为飞机在空中，才能切换到故障监控

        "计划中"的含义：
        - 指当前时间已过该航班的计划起飞时间（北京时间）
        - 只有到这时才应该去Leg页面查看该飞机的状态
        - 避免过早监控（例如早上7点不用去等9点才起飞的飞机）

        Args:
            current_time: 当前时间（北京时间）

        Returns:
            bool: True=leg页面优先, False=故障页面优先
        """
        # 优先级1: 检查是否需要到达监控（在空中且已到计划到达时间）
        for aircraft, status in self.flights.items():
            if status.needs_arrival_monitoring(current_time):
                return True

        # 优先级2: 检查是否有任何飞机在地面 且 已过计划起飞时间
        # 只有当当前时间已过该飞机的计划起飞时间，才需要监控Leg页面
        for aircraft, status in self.flights.items():
            if status.is_on_ground():
                # 获取该飞机的计划起飞时间
                scheduled_dept = FlightSchedule.get_scheduled_departure_datetime(
                    status.flight_number
                )
                # 只有当前时间已过计划起飞时间，才需要监控
                if current_time >= scheduled_dept:
                    return True

        # 优先级3: 如果所有飞机都在空中（都有OFF时间且没有IN时间）
        # 则监控故障页面
        airborne_aircraft = self.get_all_aircraft_in_air()
        ground_aircraft = self.get_all_aircraft_on_ground()

        # 所有飞机都在空中，没有飞机在地面
        if len(airborne_aircraft) > 0 and len(ground_aircraft) == 0:
            return False

        # 默认监控Leg页面（防御性逻辑）
        return True

    def update_from_latest_leg_data(self, leg_data_list: List[Dict]):
        """
        从最新的leg数据更新所有航班状态

        Args:
            leg_data_list: leg数据列表
        """
        for leg_data in leg_data_list:
            aircraft = leg_data.get('aircraft_registration')
            flight_number = leg_data.get('flight_number')

            if not aircraft or not flight_number:
                continue

            # 初始化或更新航班状态
            if aircraft not in self.flights:
                self.flights[aircraft] = FlightStatus(flight_number, aircraft)

            self.flights[aircraft].update_status(leg_data)

        self.log(f"已更新 {len(self.flights)} 架飞机的航班状态")

    def get_status_summary(self) -> str:
        """获取状态摘要"""
        summary_lines = []
        summary_lines.append("="*60)
        summary_lines.append("📊 航班状态跟踪摘要")
        summary_lines.append("="*60)

        for aircraft, status in self.flights.items():
            phase_names = {
                FlightPhase.SCHEDULED: "计划中",
                FlightPhase.PUSHBACK: "滑出",
                FlightPhase.AIRBORNE: "空中",
                FlightPhase.LANDED: "落地",
                FlightPhase.IN_GATE: "滑入",
                FlightPhase.UNKNOWN: "未知"
            }

            phase_name = phase_names.get(status.current_phase, "未知")

            summary_lines.append(f"\n✈️ {aircraft} - {status.flight_number}")
            summary_lines.append(f"   当前阶段: {phase_name}")

            if status.pushback_time:
                summary_lines.append(f"   滑出时间: {status.pushback_time.strftime('%H:%M')}")
            if status.takeoff_time:
                summary_lines.append(f"   起飞时间: {status.takeoff_time.strftime('%H:%M')}")
            if status.landing_time:
                summary_lines.append(f"   落地时间: {status.landing_time.strftime('%H:%M')}")
            if status.in_gate_time:
                summary_lines.append(f"   滑入时间: {status.in_gate_time.strftime('%H:%M')}")

            if status.scheduled_arrival:
                summary_lines.append(f"   计划到达: {status.scheduled_arrival.strftime('%H:%M')}")

        summary_lines.append("\n" + "="*60)
        return "\n".join(summary_lines)


if __name__ == "__main__":
    # 测试代码
    print("🧪 航班状态跟踪器测试")
    print("="*60)

    tracker = FlightTracker()

    # 显示状态摘要
    print(tracker.get_status_summary())

    # 测试监控决策
    now = datetime.now()
    print(f"\n🔍 当前时间: {now.strftime('%H:%M')}")
    print(f"✈️ 在空中的飞机: {tracker.get_all_aircraft_in_air()}")
    print(f"🛫 在地面的飞机: {tracker.get_all_aircraft_on_ground()}")
    print(f"🔧 需要故障监控: {tracker.needs_fault_monitoring(now)}")
    print(f"📊 需要leg监控: {tracker.needs_leg_monitoring(now)}")
    print(f"🎯 优先监控: {'Leg页面' if tracker.should_monitor_leg_first(now) else '故障页面'}")

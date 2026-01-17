"""
航班状态监控脚本

⚠️ 时间策略说明：
- 项目内部统一使用北京时间
- 数据存储使用北京时间
- 邮件展示时转换为越南时间（北京时间-1小时）

功能：
- 对比新旧数据，检测航班状态变化
- 发送状态变化邮件通知
"""

import hashlib
import os
import sys

import pandas as pd

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.flight_schedule import FlightSchedule
from core.abnormal_detector import AbnormalDetector
from core.base_monitor import BaseStatusMonitor
from core.logger import get_logger
from notifiers.leg_status_notifier import LegStatusNotifier

# 正常机场的简短名称映射（仅用于正常航班）
AIRPORT_MAPPING = {
    "VVCS-昆仑国际机场": "昆岛",
    "VVNB-内排国际机场": "河内",
    "VVTS-新山一国际机场": "胡志明",
}


class LegStatusMonitor(BaseStatusMonitor):
    """航班状态监控器"""

    def __init__(self, target_date=None):
        super().__init__(target_date)
        self.log = get_logger()

    def get_data_file_path(self):
        """获取数据文件路径"""
        return os.path.join(project_root, "data", "daily_raw", f"leg_data_{self.target_date}.csv")

    def get_status_file_path(self):
        """获取状态文件路径"""
        return os.path.join(project_root, "data", "last_email_status.json")

    def generate_content(self, df):
        """生成航班状态通知内容"""
        notifications = []

        # 动态获取所有飞机（从实际数据中）
        all_aircraft = df["执飞飞机"].unique()
        print(f"   ✅ 检测到 {len(all_aircraft)} 架飞机")

        # 为每架飞机生成状态消息
        for aircraft_num in all_aircraft:
            df_aircraft = df[df["执飞飞机"] == aircraft_num]
            if len(df_aircraft) > 0:
                status_messages = self.get_current_flight_status(df_aircraft, aircraft_num)
                notifications.extend(status_messages)

        return notifications if notifications else []

    def get_content_hash(self, content):
        """获取内容哈希值"""
        status_text = "\n".join(content) if isinstance(content, list) else str(content)
        return hashlib.md5(status_text.encode("utf-8")).hexdigest()

    def send_notification(self, content):
        """发送航班状态通知"""
        if not content:
            return False

        notifier = LegStatusNotifier(config_dict=self.gmail_config)

        if notifier.is_enabled():
            subject = f"航班状态 - {self.target_date}"
            body = "\n".join(content)
            return notifier.send_email(subject, body)
        else:
            print("   ⚠️ 邮件通知未启用")
            print("\n📧 通知内容：")
            for msg in content:
                print(f"   - {msg}")
            return True  # 未启用时认为发送成功

    # ============ 辅助方法 ============

    @staticmethod
    def parse_time_vietnam(time_str):
        """解析时间字符串并转换为越南时间（实际时间-1小时）"""
        if pd.isna(time_str) or time_str == "":
            return None

        try:
            hour, minute = map(int, str(time_str).split(":"))
            hour -= 1
            if hour < 0:
                hour += 24
            return f"{hour:02d}:{minute:02d}"
        except:
            return None

    @staticmethod
    def get_airport_name(airport_full):
        """从完整机场名称获取简短名称（动态解析）"""
        if pd.isna(airport_full):
            return "未知"

        airport_str = str(airport_full)

        # 优先使用映射表（用于正常机场）
        if airport_str in AIRPORT_MAPPING:
            return AIRPORT_MAPPING[airport_str]

        # 动态解析：从机场代码后的名称中提取
        if "-" in airport_str:
            parts = airport_str.split("-", 1)
            if len(parts) == 2:
                name_part = parts[1]

                # 移除通用后缀（按优先级）
                if name_part.endswith("国际机场"):
                    name_part = name_part[:-4]
                elif name_part.endswith("机场") or name_part.endswith("国际"):
                    name_part = name_part[:-2]

                return name_part if name_part else airport_str

        return airport_str

    @staticmethod
    def get_flight_route(flight_number, departure_airport=None, arrival_airport=None):
        """获取航班航线描述（中文）"""
        # 如果提供了实际机场信息，优先使用实际航线
        if departure_airport and arrival_airport:
            dep_short = LegStatusMonitor.get_airport_name(departure_airport)
            arr_short = LegStatusMonitor.get_airport_name(arrival_airport)
            return f"{dep_short}-{arr_short}"

        # 否则使用计划航线
        flight_info = FlightSchedule.get_flight_info(flight_number)
        if flight_info and "route" in flight_info:
            route = flight_info["route"]
            route_mapping = {"HAN": "河内", "VCS": "昆岛", "SGN": "胡志明"}
            parts = route.split("-")
            if len(parts) == 2:
                departure = route_mapping.get(parts[0], parts[0])
                arrival = route_mapping.get(parts[1], parts[1])
                return f"{departure}-{arrival}"
        return ""

    @staticmethod
    def is_flight_completed(row):
        """判断航班是否已完成（所有4个阶段都有值）"""
        out = not pd.isna(row["OUT"]) and row["OUT"] != ""
        off = not pd.isna(row["OFF"]) and row["OFF"] != ""
        on = not pd.isna(row["ON"]) and row["ON"] != ""
        inn = not pd.isna(row["IN"]) and row["IN"] != ""
        return out and off and on and inn

    @staticmethod
    def get_flight_sequence_sorted(df_aircraft):
        """从飞机数据中获取按计划时间排序的航班序列"""
        # 获取实际出现的航班号
        actual_flights = []
        for _, row in df_aircraft.iterrows():
            flight_num = row["航班号"]
            if flight_num not in actual_flights:
                actual_flights.append(flight_num)

        if not actual_flights:
            return []

        # 根据第一个航班判断航线类型
        first_flight = actual_flights[0]
        route_chain = FlightSchedule.get_route_chain(first_flight)

        if route_chain:
            return route_chain
        else:
            # 未知航线,使用实际航班按时间排序
            flight_list = []
            for _, row in df_aircraft.iterrows():
                flight_num = row["航班号"]
                flight_info = FlightSchedule.get_flight_info(flight_num)

                if flight_info:
                    scheduled_time = flight_info["scheduled_departure"]
                else:
                    scheduled_time = row["OUT"] if pd.notna(row["OUT"]) else "00:00"

                flight_list.append({"flight_number": flight_num, "scheduled_time": scheduled_time})

            flight_list.sort(key=lambda x: x["scheduled_time"])
            return [f["flight_number"] for f in flight_list]

    @staticmethod
    def wrap_status_with_abnormal(
        status_notifications, abnormal_detected, abnormal_flight_num, abnormal_row, aircraft_num
    ):
        """包装状态通知，如果有异常事件，在状态后添加异常警告"""
        if not abnormal_detected:
            return status_notifications

        detector = AbnormalDetector()
        abnormal_type = detector.get_abnormal_type_description(abnormal_detected["abnormal_type"])
        abnormal_warning = f"⚠️ 提醒：原计划{abnormal_detected['original_route']}，系统显示{abnormal_detected['actual_route']}，{abnormal_type}。"

        return status_notifications + [abnormal_warning]

    def get_current_flight_status(self, df_aircraft, aircraft_num):
        """获取飞机当前正在执行的航班状态"""
        detector = AbnormalDetector()
        flight_sequence = self.get_flight_sequence_sorted(df_aircraft)

        if not flight_sequence:
            return [f"{aircraft_num}暂无航班数据"]

        current_flight = None
        current_row = None
        last_completed_flight = None
        last_completed_row = None

        # 遍历航线链,查找当前执行和已完成的航班
        abnormal_detected = None
        abnormal_flight_num = None
        abnormal_row = None

        for flight_num in flight_sequence:
            flight_rows = df_aircraft[df_aircraft["航班号"] == flight_num]
            if len(flight_rows) > 0:
                row = flight_rows.iloc[0]

                # 检测异常
                abnormal = detector.check_abnormal_from_row(row)
                if abnormal and abnormal["is_abnormal"]:
                    abnormal_detected = abnormal
                    abnormal_flight_num = flight_num
                    abnormal_row = row

                completed = self.is_flight_completed(row)

                if completed:
                    last_completed_flight = flight_num
                    last_completed_row = row
                else:
                    current_flight = flight_num
                    current_row = row
                    break
            else:
                current_flight = flight_num
                current_row = None
                break

        # 情况1: 有正在执行的航班
        if current_row is not None:
            out_val = (
                current_row["OUT"]
                if not pd.isna(current_row["OUT"]) and current_row["OUT"] != ""
                else None
            )
            off_val = (
                current_row["OFF"]
                if not pd.isna(current_row["OFF"]) and current_row["OFF"] != ""
                else None
            )
            on_val = (
                current_row["ON"]
                if not pd.isna(current_row["ON"]) and current_row["ON"] != ""
                else None
            )
            inn_val = (
                current_row["IN"]
                if not pd.isna(current_row["IN"]) and current_row["IN"] != ""
                else None
            )

            if inn_val is not None:
                # 已落地
                airport = self.get_airport_name(current_row["着陆机场"])
                route = self.get_flight_route(
                    current_flight, current_row["起飞机场"], current_row["着陆机场"]
                )
                current_idx = flight_sequence.index(current_flight)

                if current_idx == len(flight_sequence) - 1:
                    status_msg = f"{aircraft_num}停靠{airport}；已完成今日所有航班。"
                else:
                    next_flight = flight_sequence[current_idx + 1]
                    status_msg = f"{aircraft_num}停靠{airport}；计划执行{next_flight}。"

                return self.wrap_status_with_abnormal(
                    [status_msg], abnormal_detected, abnormal_flight_num, abnormal_row, aircraft_num
                )

            elif on_val is not None:
                # 空中/落地但未滑入
                vn_time = self.parse_time_vietnam(on_val)
                time_str = f"越南时间{vn_time}" if vn_time else "越南时间未知"
                airport = self.get_airport_name(current_row["着陆机场"])
                route = self.get_flight_route(
                    current_flight, current_row["起飞机场"], current_row["着陆机场"]
                )
                status_msg = f"{aircraft_num}执行{current_flight}（{route}），已于{time_str}在{airport}落地。"

                return self.wrap_status_with_abnormal(
                    [status_msg], abnormal_detected, abnormal_flight_num, abnormal_row, aircraft_num
                )

            elif off_val is not None:
                # 已起飞
                vn_time = self.parse_time_vietnam(off_val)
                time_str = f"越南时间{vn_time}" if vn_time else "越南时间未知"
                airport = self.get_airport_name(current_row["起飞机场"])
                route = self.get_flight_route(
                    current_flight, current_row["起飞机场"], current_row["着陆机场"]
                )
                status_msg = f"{aircraft_num}执行{current_flight}（{route}），已于{time_str}从{airport}起飞。"

                return self.wrap_status_with_abnormal(
                    [status_msg], abnormal_detected, abnormal_flight_num, abnormal_row, aircraft_num
                )

            elif out_val is not None:
                # 已滑出
                vn_time = self.parse_time_vietnam(out_val)
                time_str = f"越南时间{vn_time}" if vn_time else "越南时间未知"
                airport = self.get_airport_name(current_row["起飞机场"])
                route = self.get_flight_route(
                    current_flight, current_row["起飞机场"], current_row["着陆机场"]
                )
                status_msg = f"{aircraft_num}执行{current_flight}（{route}），已于{time_str}滑出。"

                return self.wrap_status_with_abnormal(
                    [status_msg], abnormal_detected, abnormal_flight_num, abnormal_row, aircraft_num
                )

            else:
                # 计划中
                route = self.get_flight_route(current_flight)
                status_msg = f"{aircraft_num}计划执行{current_flight}（{route}）。"

                return self.wrap_status_with_abnormal(
                    [status_msg], abnormal_detected, abnormal_flight_num, abnormal_row, aircraft_num
                )

        # 情况2: 上一航班已完成,查看下一个航班
        elif last_completed_row is not None:
            airport = self.get_airport_name(last_completed_row["着陆机场"])
            last_idx = flight_sequence.index(last_completed_flight)

            if last_idx == len(flight_sequence) - 1:
                status_msg = f"{aircraft_num}停靠{airport}；已完成今日所有航班。"
            else:
                next_flight = flight_sequence[last_idx + 1]
                status_msg = f"{aircraft_num}停靠{airport}；计划执行{next_flight}。"

            return self.wrap_status_with_abnormal(
                [status_msg], abnormal_detected, abnormal_flight_num, abnormal_row, aircraft_num
            )

        # 情况3: 第一个航班还未开始
        elif current_flight is not None:
            route = self.get_flight_route(current_flight)
            status_msg = f"{aircraft_num}计划执行{current_flight}（{route}）。"

            return self.wrap_status_with_abnormal(
                [status_msg], abnormal_detected, abnormal_flight_num, abnormal_row, aircraft_num
            )

        return self.wrap_status_with_abnormal(
            [f"{aircraft_num}暂无航班数据"],
            abnormal_detected,
            abnormal_flight_num,
            abnormal_row,
            aircraft_num,
        )


def monitor_flight_status(target_date=None):
    """
    监控航班状态变化并发送通知（向后兼容的包装函数）
    """
    monitor = LegStatusMonitor(target_date)
    return monitor.run()


if __name__ == "__main__":
    print("=" * 60)
    print("航班状态监控脚本")
    print("=" * 60)

    # 支持命令行参数指定日期
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]

    success = monitor_flight_status(target_date)

    if success:
        print("\n✅ 监控完成！")
        sys.exit(0)
    else:
        print("\n⚠️ 监控失败")
        sys.exit(1)

"""
航段告警监控脚本

功能：
- 检测航段数据中的异常状态
- 当滑出(OUT)后30分钟仍未起飞(OFF)时发送告警
- 当起飞(OFF)后超过计划航程时间+30分钟仍未落地(ON)时发送告警
- 当落地(ON)后30分钟仍未滑入(IN)时发送告警
"""

import json
import os
import sys
from datetime import datetime

import pandas as pd

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.config_loader import load_config
from config.flight_schedule import FlightSchedule
from core.logger import get_logger
from exceptions.data import DataFileError, DataFreshnessError
from exceptions.notification import EmailSendError
from notifiers.leg_alert_notifier import LegAlertNotifier


class LegAlertMonitor:
    """航段告警监控器

    检测航段数据中的异常状态并发送告警邮件
    """

    # 告警阈值（分钟）
    ALERT_THRESHOLD_OUT_OFF = 30  # 滑出后30分钟仍未起飞
    ALERT_THRESHOLD_OFF_ON = 30  # 起飞后超过计划航程时间+30分钟仍未落地
    ALERT_THRESHOLD_ON_IN = 30  # 落地后30分钟仍未滑入

    # 告警重复发送间隔（秒）- 同一告警至少间隔这么多时间才能再次发送
    ALERT_RESEND_INTERVAL = 300  # 5分钟

    # 数据过期阈值（秒）- 超过这个时间未更新数据认为是过期的
    DATA_STALE_THRESHOLD = 300  # 5分钟

    def __init__(self, target_date=None):
        """
        初始化告警监控器

        Args:
            target_date: 目标日期（YYYY-MM-DD格式），默认为今天
        """
        self.target_date = target_date or datetime.now().strftime("%Y-%m-%d")
        self.log = get_logger()
        self.config_loader = load_config()
        self.gmail_config = self.config_loader.get_gmail_config()

        # 状态文件路径
        self.alert_status_file = os.path.join(project_root, "data", "last_leg_alert_status.json")

        # 数据更新时间戳文件
        self.data_timestamp_file = os.path.join(project_root, "data", "last_data_update.json")

    def get_data_file_path(self):
        """获取数据文件路径"""
        return os.path.join(project_root, "data", "daily_raw", f"leg_data_{self.target_date}.csv")

    def load_alert_status(self):
        """
        加载上次的告警状态

        Returns:
            dict: 告警状态字典，如果文件不存在或读取失败返回空字典
        """
        if not os.path.exists(self.alert_status_file):
            return {}

        try:
            with open(self.alert_status_file, encoding="utf-8") as f:
                status_data = json.load(f)
                return status_data
        except json.JSONDecodeError as e:
            self.log(f"告警状态文件JSON格式错误: {e}", "WARNING")
            return {}
        except OSError as e:
            self.log(f"读取告警状态文件失败: {e}", "WARNING")
            return {}
        except Exception as e:
            self.log(f"读取告警状态异常: {type(e).__name__}: {e}", "WARNING")
            return {}

    def save_alert_status(self, status_data):
        """
        保存告警状态

        Args:
            status_data: 告警状态字典，包含：
                - alert_history: {alert_key: last_sent_timestamp}
                - timestamp: 当前时间戳
                - date: 日期
        """
        try:
            os.makedirs(os.path.dirname(self.alert_status_file), exist_ok=True)

            with open(self.alert_status_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)

            self.log(f"告警状态已保存: {self.alert_status_file}")
        except OSError as e:
            self.log(f"保存告警状态文件失败: {e}", "WARNING")
        except Exception as e:
            self.log(f"保存告警状态异常: {type(e).__name__}: {e}", "WARNING")

    @staticmethod
    def parse_time_to_minutes(time_str):
        """
        解析时间字符串(HH:MM)为当天的分钟数

        Args:
            time_str: 时间字符串，格式 "HH:MM"

        Returns:
            int: 从0点开始的分钟数，解析失败返回 None
        """
        if pd.isna(time_str) or time_str == "":
            return None

        try:
            hour, minute = map(int, str(time_str).split(":"))
            return hour * 60 + minute
        except (ValueError, AttributeError):
            # 时间格式错误或属性访问错误
            return None
        except Exception:
            # 其他未预期错误
            return None

    @staticmethod
    def get_current_minutes():
        """
        获取当前北京时间（UTC+8）的分钟数

        注意：数据中的时间都是北京时间，所以必须用北京时间来比较

        Returns:
            int: 从0点开始的分钟数
        """
        from datetime import timedelta

        # 获取UTC时间并转换为北京时间（UTC+8）
        now_utc = datetime.utcnow()
        beijing_time = now_utc + timedelta(hours=8)
        return beijing_time.hour * 60 + beijing_time.minute

    def is_data_fresh(self):
        """
        检查数据是否是新鲜的

        通过读取数据更新时间戳文件，判断数据是否在过期阈值内更新过

        Returns:
            bool: True=数据新鲜, False=数据过期
        """
        try:
            if not os.path.exists(self.data_timestamp_file):
                print("   ⚠️ 未找到数据更新时间戳文件")
                return False

            with open(self.data_timestamp_file, encoding="utf-8") as f:
                timestamp_data = json.load(f)

            last_update_str = timestamp_data.get("last_update_time")
            if not last_update_str:
                print("   ⚠️ 时间戳文件中没有更新时间")
                return False

            # 解析最后更新时间
            last_update = datetime.strptime(last_update_str, "%Y-%m-%d %H:%M:%S")
            current_time = datetime.now()

            # 计算时间差（秒）
            time_diff = (current_time - last_update).total_seconds()

            if time_diff > self.DATA_STALE_THRESHOLD:
                print(f"   ⚠️ 数据已过期：最后更新于 {last_update_str}（{int(time_diff)}秒前）")
                # 抛出数据新鲜度异常
                raise DataFreshnessError(
                    data_type="leg",
                    last_update_time=last_update_str,
                    current_time=current_time.strftime("%Y-%m-%d %H:%M:%S"),
                    max_age_minutes=int(self.DATA_STALE_THRESHOLD / 60),
                )

            print(f"   ✅ 数据新鲜：最后更新于 {last_update_str}（{int(time_diff)}秒前）")
            return True

        except (json.JSONDecodeError, ValueError) as e:
            print(f"   ⚠️ 时间戳文件格式错误: {e}")
            self.log(f"时间戳文件格式错误: {e}", "WARNING")
            return False
        except OSError as e:
            print(f"   ⚠️ 读取时间戳文件失败: {e}")
            self.log(f"读取时间戳文件失败: {e}", "WARNING")
            return False
        except DataFreshnessError:
            # 重新抛出数据新鲜度异常
            raise
        except Exception as e:
            print(f"   ⚠️ 检查数据新鲜度失败: {type(e).__name__}: {e}")
            self.log(f"检查数据新鲜度失败: {type(e).__name__}: {e}", "WARNING")
            return False

    def check_out_without_off(self, row, current_minutes):
        """
        检查滑出后30分钟仍未起飞的情况

        Args:
            row: 航段数据行
            current_minutes: 当前时间的分钟数

        Returns:
            dict: {"key": 告警唯一标识, "message": 告警消息}，如果无需告警返回 None
        """
        out_time = row.get("OUT")
        off_time = row.get("OFF")

        # 检查是否有OUT但没有OFF
        if pd.isna(out_time) or out_time == "":
            return None
        if not pd.isna(off_time) and off_time != "":
            return None

        # 计算OUT时间到现在的分钟数
        out_minutes = self.parse_time_to_minutes(out_time)
        if out_minutes is None:
            return None

        # 计算时间差
        time_diff = current_minutes - out_minutes

        # 如果时间差为负，说明OUT可能在昨天
        if time_diff < 0:
            time_diff += 24 * 60

        # 检查是否超过阈值
        if time_diff >= self.ALERT_THRESHOLD_OUT_OFF:
            aircraft = row.get("执飞飞机", "未知飞机")
            flight = row.get("航班号", "未知航班")
            alert_key = f"{aircraft}_{flight}_OUT_WITHOUT_OFF"
            message = f"{aircraft} ({flight}) 滑出30分钟仍未起飞。请确认飞机状态。"
            return {"key": alert_key, "message": message}

        return None

    def check_on_without_in(self, row, current_minutes):
        """
        检查落地后30分钟仍未滑入的情况

        Args:
            row: 航段数据行
            current_minutes: 当前时间的分钟数

        Returns:
            dict: {"key": 告警唯一标识, "message": 告警消息}，如果无需告警返回 None
        """
        on_time = row.get("ON")
        in_time = row.get("IN")

        # 检查是否有ON但没有IN
        if pd.isna(on_time) or on_time == "":
            return None
        if not pd.isna(in_time) and in_time != "":
            return None

        # 计算ON时间到现在的分钟数
        on_minutes = self.parse_time_to_minutes(on_time)
        if on_minutes is None:
            return None

        # 计算时间差
        time_diff = current_minutes - on_minutes

        # 如果时间差为负，说明ON可能在昨天
        if time_diff < 0:
            time_diff += 24 * 60

        # 检查是否超过阈值
        if time_diff >= self.ALERT_THRESHOLD_ON_IN:
            aircraft = row.get("执飞飞机", "未知飞机")
            flight = row.get("航班号", "未知航班")
            alert_key = f"{aircraft}_{flight}_ON_WITHOUT_IN"
            message = f"{aircraft} ({flight}) 落地30分钟仍未停靠。请确认飞机状态。"
            return {"key": alert_key, "message": message}

        return None

    def check_off_without_on_by_duration(self, row, current_minutes):
        """
        检查起飞后超过计划航程时间+30分钟仍未落地的情况

        告警条件：起飞时刻 + 计划航程时间 + 30分钟 > 当前时间，但仍未落地

        Args:
            row: 航段数据行
            current_minutes: 当前时间的分钟数

        Returns:
            dict: {"key": 告警唯一标识, "message": 告警消息}，如果无需告警返回 None
        """
        off_time = row.get("OFF")
        on_time = row.get("ON")
        flight_number = row.get("航班号", "")

        # 检查是否有OFF但没有ON
        if pd.isna(off_time) or off_time == "":
            return None
        if not pd.isna(on_time) and on_time != "":
            return None

        # 获取航班信息（计划航程时间）
        flight_info = FlightSchedule.get_flight_info(flight_number)
        if not flight_info:
            # 未知航班，跳过此检查
            return None

        duration_minutes = flight_info.get("duration_minutes", 0)

        # 计算OFF时间到现在的分钟数
        off_minutes = self.parse_time_to_minutes(off_time)
        if off_minutes is None:
            return None

        # 计算时间差（从起飞到现在）
        time_diff = current_minutes - off_minutes

        # 如果时间差为负，说明OFF可能在昨天（跨天情况）
        if time_diff < 0:
            time_diff += 24 * 60

        # 检查是否超过（计划航程时间 + 30分钟）
        threshold = duration_minutes + self.ALERT_THRESHOLD_OFF_ON
        if time_diff >= threshold:
            aircraft = row.get("执飞飞机", "未知飞机")
            # 消息中不包含动态的time_diff，避免每次检查时消息都不同
            alert_key = f"{aircraft}_{flight_number}_OFF_WITHOUT_ON"
            message = f"{aircraft} ({flight_number}) 起飞超过计划航程时间仍未落地。请确认飞机状态。"
            return {"key": alert_key, "message": message}

        return None

    def check_alerts(self, df):
        """
        检查所有告警条件

        Args:
            df: 航段数据DataFrame

        Returns:
            list: 告警字典列表，每个元素包含 {"key": 唯一标识, "message": 消息}
        """
        alerts = []
        current_minutes = self.get_current_minutes()

        for _, row in df.iterrows():
            # 检查OUT后30分钟仍未OFF
            alert1 = self.check_out_without_off(row, current_minutes)
            if alert1:
                alerts.append(alert1)

            # 检查OFF后超过计划航程时间+30分钟仍未ON
            alert2 = self.check_off_without_on_by_duration(row, current_minutes)
            if alert2:
                alerts.append(alert2)

            # 检查ON后30分钟仍未IN
            alert3 = self.check_on_without_in(row, current_minutes)
            if alert3:
                alerts.append(alert3)

        return alerts

    def filter_new_alerts(self, alerts, last_status):
        """
        过滤掉已发送过的告警

        基于告警key和最后发送时间进行过滤：
        - 如果告警key不在历史记录中，视为新告警
        - 如果告警key在历史记录中，检查是否超过重发间隔

        Args:
            alerts: 告警字典列表，每个元素包含 {"key": 唯一标识, "message": 消息}
            last_status: 上次的告警状态字典

        Returns:
            list: 新的告警字典列表
        """
        if not last_status:
            return alerts

        # 获取当前时间
        current_time = datetime.now()

        # 兼容旧格式：如果检测到旧格式（有"alerts"字段但没有"alert_history"字段）
        # 则清空历史，让所有告警都作为新告警发送
        if "alerts" in last_status and "alert_history" not in last_status:
            print("   ℹ️ 检测到旧格式状态文件，将重置告警历史")
            return alerts

        # 获取历史告警记录 {alert_key: last_sent_timestamp}
        alert_history = last_status.get("alert_history", {})

        new_alerts = []
        for alert in alerts:
            alert_key = alert["key"]
            last_sent_str = alert_history.get(alert_key)

            if not last_sent_str:
                # 这个告警从未发送过
                new_alerts.append(alert)
            else:
                # 检查是否超过重发间隔
                try:
                    last_sent = datetime.strptime(last_sent_str, "%Y-%m-%d %H:%M:%S")
                    time_diff = (current_time - last_sent).total_seconds()

                    if time_diff >= self.ALERT_RESEND_INTERVAL:
                        # 超过重发间隔，需要再次发送
                        new_alerts.append(alert)
                except (ValueError, TypeError):
                    # 时间解析失败，视为新告警
                    new_alerts.append(alert)

        return new_alerts

    def send_alert_notification(self, alerts):
        """
        发送告警通知

        Args:
            alerts: 告警字典列表，每个元素包含 {"key": 唯一标识, "message": 消息}

        Returns:
            bool: 发送是否成功
        """
        if not alerts:
            return True

        # 提取消息部分
        alert_messages = [alert["message"] for alert in alerts]

        notifier = LegAlertNotifier(config_dict=self.gmail_config)

        if notifier.is_enabled():
            return notifier.send_alert_notification(alert_messages, self.target_date)
        else:
            print("   ⚠️ 邮件通知未启用")
            print("\n📧 告警内容：")
            for msg in alert_messages:
                print(f"   - {msg}")
            return True  # 未启用时认为发送成功

    def monitor(self):
        """
        执行告警监控

        Returns:
            bool: 监控成功返回 True，否则返回 False
        """
        print(f"📅 告警监控日期：{self.target_date}")

        # 读取数据文件
        data_file = self.get_data_file_path()
        if not os.path.exists(data_file):
            print(f"❌ 错误：找不到数据文件 {data_file}")
            self.log(f"数据文件不存在: {data_file}", "ERROR")
            return False

        print("📂 读取数据文件...")
        try:
            df = pd.read_csv(data_file)
            print(f"   ✅ 读取到 {len(df)} 行数据")
        except pd.errors.EmptyDataError:
            print(f"❌ 数据文件为空: {data_file}")
            self.log(f"数据文件为空: {data_file}", "ERROR")
            return False
        except pd.errors.ParserError as e:
            print(f"❌ CSV格式错误: {e}")
            self.log(f"CSV解析失败: {e}", "ERROR")
            return False
        except OSError as e:
            print(f"❌ 文件读取失败: {e}")
            self.log(f"文件读取失败: {data_file} - {e}", "ERROR")
            return False
        except Exception as e:
            print(f"❌ 读取数据文件失败: {type(e).__name__}: {e}")
            self.log(f"读取数据文件异常: {type(e).__name__}: {e}", "ERROR")
            return False

        # 检查数据新鲜度
        print("\n🔍 检查数据新鲜度...")
        try:
            if not self.is_data_fresh():
                print("   ⚠️ 数据已过期，跳过超时告警检查")
                print("   💡 可能原因：浏览器连接断开、网络问题或数据抓取失败")
                self.log("数据已过期，跳过超时告警检查", "WARNING")
                return True  # 返回True避免被外层认为是失败
        except DataFreshnessError as e:
            # 数据新鲜度异常，记录详细信息
            print(f"   ⚠️ 数据已过期: {e}")
            self.log(f"数据新鲜度检查失败: {e}", "WARNING")
            return True  # 返回True避免被外层认为是失败

        # 检查告警
        print("\n🔍 检查告警条件...")
        alerts = self.check_alerts(df)

        if not alerts:
            print("   ℹ️ 未检测到告警")
            return True

        print(f"   ✅ 检测到 {len(alerts)} 个告警")

        # 加载上次的告警状态
        print("\n📋 加载上次告警状态...")
        last_status = self.load_alert_status()

        # 过滤新告警
        print("\n🔍 过滤已发送的告警...")
        new_alerts = self.filter_new_alerts(alerts, last_status)

        if not new_alerts:
            print("   ℹ️ 无新告警（均已发送过或未到重发时间）")
            # 即使没有新告警，也要更新alert_history的时间戳
            current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            alert_history = {alert["key"]: current_time_str for alert in alerts}
            self.save_alert_status(
                {
                    "alert_history": alert_history,
                    "timestamp": current_time_str,
                    "date": self.target_date,
                }
            )
            return True

        print(f"   ✅ 有 {len(new_alerts)} 个新告警需要发送")

        # 发送告警通知
        print("\n📧 发送告警通知...")
        success = self.send_alert_notification(new_alerts)

        if success:
            print("   ✅ 告警通知发送成功")

            # 保存当前告警状态（包括所有告警的key和时间戳）
            current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            alert_history = {alert["key"]: current_time_str for alert in alerts}
            self.save_alert_status(
                {
                    "alert_history": alert_history,
                    "timestamp": current_time_str,
                    "date": self.target_date,
                }
            )
            return True
        else:
            print("   ⚠️ 告警通知发送失败")
            return False

    def run(self):
        """
        运行告警监控（供外部调用的入口方法）

        Returns:
            bool: 成功返回 True，失败返回 False
        """
        try:
            return self.monitor()
        except DataFileError as e:
            print(f"❌ 数据文件错误: {e}")
            self.log(f"数据文件错误: {e}", "ERROR")
            return False
        except DataFreshnessError as e:
            # 数据新鲜度异常不视为失败
            print(f"⚠️ 数据新鲜度检查: {e}")
            self.log(f"数据新鲜度检查: {e}", "WARNING")
            return True
        except EmailSendError as e:
            print(f"❌ 邮件发送失败: {e}")
            self.log(f"邮件发送失败: {e}", "ERROR")
            return False
        except Exception as e:
            print(f"❌ 告警监控执行失败：{type(e).__name__}: {e}")
            self.log(f"告警监控执行失败: {type(e).__name__}: {e}", "ERROR")
            import traceback

            traceback.print_exc()
            return False


def monitor_leg_alerts(target_date=None):
    """
    监控航段告警并发送通知（向后兼容的包装函数）

    Args:
        target_date: 目标日期（YYYY-MM-DD格式），默认为今天

    Returns:
        bool: 监控成功返回 True，失败返回 False
    """
    monitor = LegAlertMonitor(target_date)
    return monitor.run()


if __name__ == "__main__":
    print("=" * 60)
    print("航段告警监控脚本")
    print("=" * 60)

    # 支持命令行参数指定日期
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]

    success = monitor_leg_alerts(target_date)

    if success:
        print("\n✅ 告警监控完成！")
        sys.exit(0)
    else:
        print("\n⚠️ 告警监控失败")
        sys.exit(1)

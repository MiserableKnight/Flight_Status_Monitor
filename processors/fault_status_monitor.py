# -*- coding: utf-8 -*-
"""
故障状态监控脚本

功能：
- 读取每日故障数据
- 读取航班起降时间数据
- 生成故障汇总信息（含时间背景）
- 发送故障邮件通知
"""
import pandas as pd
from datetime import datetime
import os
import sys
import hashlib
import re

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.logger import get_logger
from notifiers.fault_status_notifier import FaultStatusNotifier
from core.fault_filter import FaultFilter
from core.base_monitor import BaseStatusMonitor
from config.flight_phase_mapping import get_phase_name, get_fault_type_name, get_phase_name_without_suffix
from config.flight_schedule import FlightSchedule

# 机场代码到城市名称的映射
AIRPORT_TO_CITY = {
    'VVNB': '河内',
    'VVTS': '胡志明',
    'VVCS': '昆岛'
}


class FaultStatusMonitor(BaseStatusMonitor):
    """故障状态监控器"""

    def __init__(self, target_date=None):
        super().__init__(target_date)
        self.log = get_logger()
        self.flight_times = None

    def get_data_file_path(self):
        """获取数据文件路径"""
        return os.path.join(project_root, 'data', 'daily_raw', f'fault_data_{self.target_date}.csv')

    def get_status_file_path(self):
        """获取状态文件路径"""
        return os.path.join(project_root, 'data', 'last_fault_email_status.json')

    def read_data_file(self):
        """读取数据文件（重写以支持编码处理和列名重命名）"""
        data_file = self.get_data_file_path()

        if not os.path.exists(data_file):
            self.log(f"数据文件不存在: {data_file}", "ERROR")
            print(f"❌ 错误：找不到数据文件 {data_file}")
            return None

        try:
            # 读取CSV文件，处理可能的编码问题
            try:
                df = pd.read_csv(data_file, encoding='utf-8-sig')
            except:
                df = pd.read_csv(data_file, encoding='gbk')

            # 重命名可能的列名变体（处理编码问题）
            if '触发_time' in df.columns and '触发时间' not in df.columns:
                df.rename(columns={'触发_time': '触发时间'}, inplace=True)

            print(f"   ✅ 读取到 {len(df)} 行数据")
            return df
        except Exception as e:
            self.log(f"读取数据文件失败: {e}", "ERROR")
            print(f"❌ 读取数据文件失败：{e}")
            return None

    def generate_content(self, df):
        """生成故障汇总内容"""
        # 应用故障过滤规则
        print("\n🔍 应用故障过滤规则...")
        try:
            filter_obj = FaultFilter()
            filter_stats = filter_obj.get_filter_stats()
            print(f"   📋 过滤规则: 组合规则 {filter_stats['single_filter_rules']} 条, 关联规则 {filter_stats['group_filter_rules']} 条")

            df = filter_obj.apply_filters(df)
            print(f"   ✅ 过滤后剩余 {len(df)} 行数据")
        except Exception as e:
            print(f"   ⚠️ 过滤失败，继续使用原始数据: {e}")
            self.log(f"Filter application failed: {e}", "WARNING")

        # 加载航班时间数据
        print("\n✈️ 加载航班时间数据...")
        self.flight_times = self.load_flight_times()
        if self.flight_times:
            print(f"   ✅ 成功加载 {len(self.flight_times)} 条航班时间记录")
        else:
            print(f"   ⚠️ 未找到航班时间数据，邮件将不包含时间背景信息")

        # 生成故障汇总
        print("\n📊 生成故障汇总...")
        return self.generate_fault_summary(df)

    def get_content_hash(self, content):
        """获取内容哈希值（基于数据行数）"""
        return hashlib.md5(
            f"{self.target_date}_{len(content) if hasattr(content, '__len__') else 0}".encode('utf-8')
        ).hexdigest()

    def send_notification(self, content):
        """发送故障通知"""
        notifier = FaultStatusNotifier(config_dict=self.gmail_config)

        if notifier.is_enabled():
            return notifier.send_fault_status_notification(content, self.target_date, None)
        else:
            print(f"   ⚠️ 邮件通知未启用")
            print("\n📧 通知内容：")
            print(content)
            return True  # 未启用时认为发送成功

    def save_current_status(self, status_hash, **metadata):
        """保存当前状态（重写以保存额外的元数据）"""
        status_file = self.get_status_file_path()

        try:
            os.makedirs(os.path.dirname(status_file), exist_ok=True)

            status_data = {
                'data_hash': status_hash,  # 故障监控使用 data_hash 而不是 status_hash
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'date': self.target_date,
                **metadata
            }

            with open(status_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(status_data, f, ensure_ascii=False, indent=2)

            print(f"   💾 已保存当前状态")
            self.log(f"状态已保存: {status_file}")
        except Exception as e:
            print(f"   ⚠️ 保存状态失败: {e}")
            self.log(f"保存状态文件失败: {e}", "WARNING")

    def load_last_status(self):
        """加载上次保存的状态（重写以支持 data_hash）"""
        status_file = self.get_status_file_path()

        if not os.path.exists(status_file):
            return None

        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                import json
                status_data = json.load(f)
                # 兼容 status_hash 和 data_hash
                if 'data_hash' not in status_data and 'status_hash' in status_data:
                    status_data['data_hash'] = status_data['status_hash']
                print(f"   📋 上次状态已加载")
                return status_data
        except Exception as e:
            print(f"   ⚠️ 读取上次状态失败: {e}")
            self.log(f"读取状态文件失败: {e}", "WARNING")
            return None

    def has_status_changed(self, current_hash, last_status):
        """检查状态是否发生变化（重写以使用 data_hash）"""
        if last_status is None:
            print(f"   ✅ 首次运行，需要发送通知")
            return True

        last_hash = last_status.get('data_hash')  # 使用 data_hash 而不是 status_hash
        print(f"   📊 上次数据哈希: {last_hash}")
        print(f"   📊 当前数据哈希: {current_hash}")

        if current_hash == last_hash:
            print(f"\n   ℹ️ 数据无变化，跳过通知")
            self.log("数据无变化，跳过通知")
            return False

        print(f"\n   ✅ 检测到数据变化")
        return True

    # ============ 辅助方法 ============

    @staticmethod
    def parse_time_str(time_str):
        """解析时间字符串为 datetime.time 对象"""
        if pd.isna(time_str) or not time_str:
            return None

        # 如果包含日期，只取时间部分
        if isinstance(time_str, str) and ' ' in time_str:
            time_str = time_str.split(' ')[-1]

        try:
            # 解析时间 HH:MM:SS 或 HH:MM
            parts = str(time_str).split(':')
            if len(parts) == 3:
                hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2])
                if 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59:
                    return datetime.strptime(time_str, '%H:%M:%S').time()
            elif len(parts) == 2:
                hour, minute = int(parts[0]), int(parts[1])
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return datetime.strptime(f"{time_str}:00", '%H:%M:%S').time()
            return None
        except:
            return None

    @staticmethod
    def calculate_time_context(fault_time_str, flight_times):
        """计算故障时间相对于航班关键时间点的时间差"""
        fault_time = FaultStatusMonitor.parse_time_str(fault_time_str)
        if not fault_time:
            return None

        # 解析航班关键时间点
        times = {}
        for key, time_str in flight_times.items():
            t = FaultStatusMonitor.parse_time_str(time_str)
            if t:
                times[key] = t

        if not times:
            return None

        # 定义时间点顺序
        time_events = [
            ('OUT', '滑出'),
            ('OFF', '起飞'),
            ('ON', '降落'),
            ('IN', '滑入')
        ]

        # 将故障时间转换为分钟数（从0:00开始）
        fault_minutes = fault_time.hour * 60 + fault_time.minute + fault_time.second / 60

        # 找到故障时间在时间轴上的位置
        last_event_time = None
        last_event_name = None

        for event_key, event_name in time_events:
            if event_key not in times:
                continue

            event_time = times[event_key]
            event_minutes = event_time.hour * 60 + event_time.minute + event_time.second / 60

            if fault_minutes >= event_minutes:
                last_event_time = event_time
                last_event_name = event_name
            else:
                break

        if last_event_name and last_event_time:
            last_minutes = last_event_time.hour * 60 + last_event_time.minute + last_event_time.second / 60
            diff_minutes = fault_minutes - last_minutes
            minutes = int(round(diff_minutes))

            if minutes == 0:
                return f"{last_event_name}时"
            elif minutes < 60:
                return f"{last_event_name}后{minutes}分钟"
            else:
                hours = minutes // 60
                remain_minutes = minutes % 60
                if remain_minutes == 0:
                    return f"{last_event_name}后{hours}小时"
                else:
                    return f"{last_event_name}后{hours}小时{remain_minutes}分钟"
        elif 'OUT' in times:
            out_time = times['OUT']
            out_minutes = out_time.hour * 60 + out_time.minute + out_time.second / 60
            diff_minutes = out_minutes - fault_minutes

            minutes = int(round(diff_minutes))
            if minutes == 0:
                return "滑出时"
            elif minutes < 60:
                return f"滑出前{minutes}分钟"
            else:
                hours = minutes // 60
                remain_minutes = minutes % 60
                if remain_minutes == 0:
                    return f"滑出前{hours}小时"
                else:
                    return f"滑出前{hours}小时{remain_minutes}分钟"

        return None

    @staticmethod
    def clean_description(description: str) -> str:
        """清理故障描述，移除方括号及其内容"""
        if not description:
            return ''

        # 移除所有方括号及其内容
        cleaned = re.sub(r'\[.*?\]', '', description)
        # 移除多余的空格
        cleaned = ' '.join(cleaned.split())
        return cleaned.strip()

    @staticmethod
    def extract_city_name(airport_str):
        """从机场字符串中提取城市名称"""
        if not airport_str:
            return None

        # 如果包含"-"，提取机场代码部分
        if '-' in airport_str:
            airport_code = airport_str.split('-')[0].strip()
        else:
            airport_code = airport_str.strip()

        # 映射到城市名称
        return AIRPORT_TO_CITY.get(airport_code)

    @staticmethod
    def get_route_pair(flight_num, departure_airport_str, arrival_airport_str):
        """获取城市对字符串"""
        # 尝试从实际机场数据中提取
        dep_city = FaultStatusMonitor.extract_city_name(departure_airport_str)
        arr_city = FaultStatusMonitor.extract_city_name(arrival_airport_str)

        if dep_city and arr_city:
            return f"{dep_city}-{arr_city}"

        # 如果实际数据无法获取，尝试从配置文件获取
        flight_info = FlightSchedule.get_flight_info(flight_num)
        if flight_info and 'route' in flight_info:
            route = flight_info['route']
            parts = route.split('-')
            if len(parts) == 2:
                city_map = {
                    'HAN': '河内',
                    'SGN': '胡志明',
                    'VCS': '昆岛'
                }
                dep = city_map.get(parts[0])
                arr = city_map.get(parts[1])
                if dep and arr:
                    return f"{dep}-{arr}"

        return None

    def load_flight_times(self):
        """加载航班起降时间数据和机场信息"""
        leg_file = os.path.join(project_root, 'data', 'daily_raw', f'leg_data_{self.target_date}.csv')

        if not os.path.exists(leg_file):
            self.log(f"航班数据文件不存在: {leg_file}", "WARNING")
            return {}

        try:
            try:
                df = pd.read_csv(leg_file, encoding='utf-8-sig')
            except:
                df = pd.read_csv(leg_file, encoding='gbk')

            flight_times = {}

            for _, row in df.iterrows():
                key = (row['执飞飞机'], row['航班号'])
                flight_times[key] = {
                    'OUT': row.get('OUT', ''),
                    'OFF': row.get('OFF', ''),
                    'ON': row.get('ON', ''),
                    'IN': row.get('IN', ''),
                    'departure_airport': row.get('起飞机场', ''),
                    'arrival_airport': row.get('着陆机场', '')
                }

            self.log(f"成功加载 {len(flight_times)} 条航班时间数据")
            return flight_times

        except Exception as e:
            self.log(f"读取航班数据失败: {e}", "ERROR")
            return {}

    def generate_fault_summary(self, df):
        """生成故障汇总信息"""
        if df.empty:
            return "今日无故障记录\n"

        # 按飞机分组
        aircraft_groups = df.groupby('机号')
        summary_lines = []

        for aircraft_num, group in aircraft_groups:
            summary_lines.append(f"{aircraft_num}:")

            # 按航班号分组，并收集每个航班的最新故障时间
            flight_groups = group.groupby('航班号')

            # 收集每个航班的故障数据和最新故障时间
            flights_data = []
            for flight_num, flight_group in flight_groups:
                # 转换为列表并按触发时间排序（倒序）
                faults = flight_group.to_dict('records')
                faults.sort(key=lambda x: x['触发时间'], reverse=True)

                # 获取该航班的最新故障时间（第一个故障的时间）
                latest_fault_time = faults[0]['触发时间'] if faults else ''

                # 获取该航班的时间数据
                flight_key = (aircraft_num, flight_num)
                flight_data = self.flight_times.get(flight_key, {}) if self.flight_times else {}

                flights_data.append({
                    'flight_num': flight_num,
                    'faults': faults,
                    'flight_data': flight_data,
                    'latest_fault_time': latest_fault_time
                })

            # 按照最新故障时间倒序排列航班（最新故障的航班在最上面）
            flights_data.sort(key=lambda x: x['latest_fault_time'], reverse=True)

            # 处理排序后的航班
            for flight_info in flights_data:
                flight_num = flight_info['flight_num']
                faults = flight_info['faults']
                flight_data = flight_info['flight_data']

                # 获取城市对信息
                route_pair = None
                if flight_data:
                    route_pair = self.get_route_pair(
                        flight_num,
                        flight_data.get('departure_airport', ''),
                        flight_data.get('arrival_airport', '')
                    )

                # 构建航班行，包含城市对
                if route_pair:
                    flight_line = f"  {flight_num}（{route_pair}）:"
                else:
                    flight_line = f"  {flight_num}:"

                fault_lines = []

                # 提取时间数据（用于计算时间背景）
                flight_times = {
                    'OUT': flight_data.get('OUT', ''),
                    'OFF': flight_data.get('OFF', ''),
                    'ON': flight_data.get('ON', ''),
                    'IN': flight_data.get('IN', '')
                }

                for fault in faults:
                    trigger_time = fault['触发_time'] if '触发_time' in fault else fault.get('触发时间', '')

                    # 格式化故障描述
                    description = fault.get('描述', '')
                    fault_type = fault.get('故障类型', '')
                    phase = fault.get('飞行阶段', '')

                    # 清理描述：移除方括号内容
                    cleaned_desc = self.clean_description(description)

                    # 将故障类型和飞行阶段缩写转换为中文
                    fault_type_cn = get_fault_type_name(fault_type) if fault_type else ''
                    phase_cn = get_phase_name_without_suffix(phase) if phase else ''

                    # 计算时间背景
                    time_context = None
                    if flight_times:
                        time_context = self.calculate_time_context(trigger_time, flight_times)

                    # 构建故障行
                    fault_line_parts = []

                    # 添加飞行阶段和时间背景
                    if phase_cn:
                        if time_context:
                            fault_line_parts.append(f"{phase_cn}（{time_context}）")
                        else:
                            fault_line_parts.append(f"{phase_cn}阶段")
                    elif time_context:
                        fault_line_parts.append(f"（{time_context}）")

                    # 添加故障类型和描述
                    if fault_type_cn:
                        fault_line_parts.append(f"有{fault_type_cn}：{cleaned_desc}")
                    else:
                        fault_line_parts.append(cleaned_desc)

                    # 组合最终行
                    if fault_line_parts:
                        fault_lines.append(f"    - {'，'.join(fault_line_parts)}")
                    else:
                        fault_lines.append(f"    - {cleaned_desc}")

                if fault_lines:
                    summary_lines.append(flight_line)
                    summary_lines.extend(fault_lines[:10])  # 最多显示10条
                    if len(fault_lines) > 10:
                        summary_lines.append(f"    ... (还有{len(fault_lines)-10}条)")

            summary_lines.append("")

        return '\n'.join(summary_lines)


def monitor_fault_status(target_date=None):
    """
    监控故障状态并发送通知（向后兼容的包装函数）
    """
    monitor = FaultStatusMonitor(target_date)
    return monitor.run()


if __name__ == "__main__":
    print("=" * 60)
    print("故障状态监控脚本")
    print("=" * 60)

    # 支持命令行参数指定日期
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]

    success = monitor_fault_status(target_date)

    if success:
        print("\n✅ 监控完成！")
        sys.exit(0)
    else:
        print("\n⚠️ 监控失败")
        sys.exit(1)

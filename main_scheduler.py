# -*- coding: utf-8 -*-
"""
航班数据抓取系统 - 主调度器
系统唯一入口，负责全天任务调度 (06:30 - 21:00)

⚠️ 重要技术说明：
- 本项目使用 DrissionPage 作为浏览器自动化框架（不是 Playwright！）
- 所有 fetcher 模块都是独立的函数式脚本，通过调用其 main() 函数执行
- BrowserHandler 使用 DrissionPage 的 ChromiumPage 和 ChromiumOptions

功能：
- 定时执行航段数据抓取（leg_fetcher）
- 定时执行故障数据抓取（faults_fetcher）
- 定时执行飞行数据抓取（flight_fetcher，运力统计）
- Gmail通知（可选）
- 任务统计和报告
"""
import sys
import os
import time
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config.config_loader import load_config
from config.flight_schedule import FlightSchedule
from core.logger import get_logger
from core.notifier import GmailNotifier
from core.flight_tracker import FlightTracker


class TaskScheduler:
    """任务调度器类"""

    def __init__(self):
        """初始化调度器"""
        # 加载配置
        self.config_loader = load_config()
        self.config = self.config_loader.get_all_config()

        # 初始化核心组件
        self.log = get_logger()

        # 初始化通知器（如果配置了Gmail）
        gmail_config = self.config.get('gmail', {})
        self.notifier = GmailNotifier(config=gmail_config) if gmail_config else None

        # 初始化航班状态跟踪器
        self.flight_tracker = FlightTracker()

        # 统计数据
        self.stats = {
            'leg_fetch_count': 0,
            'leg_success_count': 0,
            'leg_failure_count': 0,
            'faults_fetch_count': 0,
            'faults_success_count': 0,
            'faults_failure_count': 0,
            'flight_fetch_count': 0,
            'flight_success_count': 0,
            'flight_failure_count': 0
        }

        # 当前监控模式：'leg' 或 'faults'
        self.current_monitor_mode = 'leg'

        self.log("系统初始化完成")

    def run_script(self, script_name: str, task_name: str) -> bool:
        """
        运行数据抓取脚本

        Args:
            script_name: 脚本模块名 (如 'modules.leg_fetcher')
            task_name: 任务名称（用于日志）

        Returns:
            bool: 是否成功
        """
        print(f"\n{'='*60}")
        print(f"🚀 开始执行任务: {task_name}")
        print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('='*60)

        self.log(f"开始执行任务: {task_name}")

        try:
            # 使用 subprocess 运行脚本
            script_path = os.path.join(project_root, 'modules', f"{script_name}.py")

            if not os.path.exists(script_path):
                raise Exception(f"脚本不存在: {script_path}")

            # 运行脚本
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            # 打印输出
            if result.stdout:
                print(result.stdout)

            if result.returncode == 0:
                print(f"✅ 任务 {task_name} 执行成功")
                self.log(f"任务成功: {task_name}", "SUCCESS")

                # 发送成功通知（如果启用）
                if self.notifier and self.notifier.is_enabled():
                    self.notifier.send_success_notification(task_name, "脚本执行成功")

                return True
            else:
                print(f"❌ 任务 {task_name} 执行失败")
                if result.stderr:
                    print(result.stderr)
                self.log(f"任务失败: {task_name}", "ERROR")

                # 发送失败通知（如果启用）
                if self.notifier and self.notifier.is_enabled():
                    self.notifier.send_error_notification(task_name, result.stderr or "脚本执行失败")

                return False

        except subprocess.TimeoutExpired:
            error_msg = f"任务执行超时（300秒）"
            print(f"❌ {error_msg}")
            self.log(f"任务超时: {task_name}", "ERROR")

            if self.notifier and self.notifier.is_enabled():
                self.notifier.send_error_notification(task_name, error_msg)

            return False

        except Exception as e:
            print(f"❌ 任务执行出错: {e}")
            self.log(f"任务出错: {task_name} - {e}", "ERROR")

            # 发送错误通知
            if self.notifier and self.notifier.is_enabled():
                self.notifier.send_error_notification(task_name, str(e))

            return False

    def run_update_script(self, script_name: str, task_name: str, date_arg: str = None) -> bool:
        """
        运行数据更新/监控脚本

        Args:
            script_name: 脚本文件名 (如 'leg_data_update')
            task_name: 任务名称（用于日志）
            date_arg: 可选的日期参数

        Returns:
            bool: 是否成功
        """
        print(f"\n{'='*60}")
        print(f"🔄 开始执行任务: {task_name}")
        if date_arg:
            print(f"📅 日期: {date_arg}")
        print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('='*60)

        self.log(f"开始执行任务: {task_name}")

        try:
            script_path = os.path.join(project_root, f"{script_name}.py")

            if not os.path.exists(script_path):
                raise Exception(f"脚本不存在: {script_path}")

            # 构建命令参数
            cmd = [sys.executable, script_path]
            if date_arg:
                cmd.append(date_arg)

            # 运行脚本
            result = subprocess.run(
                cmd,
                capture_output=False,  # 实时输出
                text=True,
                timeout=120  # 2分钟超时
            )

            if result.returncode == 0:
                print(f"✅ 任务 {task_name} 执行成功")
                self.log(f"任务成功: {task_name}", "SUCCESS")
                return True
            else:
                print(f"❌ 任务 {task_name} 执行失败")
                self.log(f"任务失败: {task_name}", "ERROR")
                return False

        except subprocess.TimeoutExpired:
            error_msg = f"任务执行超时（120秒）"
            print(f"❌ {error_msg}")
            self.log(f"任务超时: {task_name}", "ERROR")
            return False

        except Exception as e:
            print(f"❌ 任务执行出错: {e}")
            self.log(f"任务出错: {task_name} - {e}", "ERROR")
            return False

    def fetch_leg_data(self):
        """抓取航段数据"""
        return self.run_script('leg_fetcher', '航段数据抓取')

    def fetch_flight_data(self):
        """抓取飞行数据（运力统计）"""
        return self.run_script('flight_fetcher', '飞行数据抓取')

    def fetch_faults_data(self):
        """抓取故障数据"""
        return self.run_script('faults_fetcher', '故障数据抓取')

    def parse_time(self, time_str: str) -> datetime:
        """
        解析时间字符串为今天的datetime对象

        Args:
            time_str: 时间字符串 (HH:MM)

        Returns:
            datetime: datetime对象
        """
        today = datetime.now().date()
        hour, minute = map(int, time_str.split(':'))
        return datetime.combine(today, datetime.min.time()) + timedelta(hours=hour, minutes=minute)

    def wait_until_time(self, target_time: datetime):
        """
        等待直到目标时间

        Args:
            target_time: 目标时间
        """
        now = datetime.now()

        if target_time <= now:
            # 目标时间已过，设置为明天
            target_time += timedelta(days=1)

        delta = target_time - now
        wait_seconds = delta.total_seconds()

        print(f"\n⏰ 等待至 {target_time.strftime('%Y-%m-%d %H:%M:%S')}...")
        print(f"⏳ 等待时长: {delta.seconds // 3600}小时 {(delta.seconds % 3600) // 60}分钟")

        self.log(f"等待至 {target_time.strftime('%Y-%m-%d %H:%M:%S')}")

        time.sleep(wait_seconds)

    def run_daily_schedule(self):
        """
        运行每日调度 - 基于航班生命周期的智能监控

        ⚠️ 注意：项目中所有时间统一使用北京时间

        监控策略:
        1. 起飞前: 每分钟检查leg页面（等待滑出）
        2. 起飞后: 切换到故障页面监控（每分钟）
        3. 快落地时: 切回leg页面（计划到达时间）
        4. 落地后: 继续监控leg页面直到滑入
        5. 21:00: 抓取flight数据（运力统计）
        """
        scheduler_config = self.config['scheduler']

        # 解析时间配置
        start_time = self.parse_time(scheduler_config['start_time'])
        end_time = self.parse_time(scheduler_config['end_time'])

        # 显示航班计划
        print("\n" + "="*60)
        print("📋 今日航班计划:")
        print("="*60)
        for flight_num in FlightSchedule.get_all_flights():
            info = FlightSchedule.get_flight_info(flight_num)
            print(f"  {flight_num}: 计划起飞 {info['scheduled_departure']} (北京时间)")
            print(f"           航程 {info['duration_minutes']}分钟, 航线 {info['route']}")

        print(f"\n⏰ 运行时间: {scheduler_config['start_time']} - {scheduler_config['end_time']}")
        print("🎯 监控模式: 智能航班生命周期监控")
        print("   - 起飞前/落地后: 监控Leg数据页面")
        print("   - 空中: 监控故障页面")
        print("   - 21:00: 抓取Flight数据（运力统计）")
        print("="*60)

        # 等待到启动时间
        now = datetime.now()
        if start_time > now:
            self.wait_until_time(start_time)

        # 主循环 - 智能航班生命周期监控
        print("\n🚀 开始智能航班生命周期监控...")
        print(self.flight_tracker.get_status_summary())

        last_check_time = None
        check_interval = timedelta(minutes=1)  # 每分钟检查一次
        flight_data_fetched_today = False

        while True:
            now = datetime.now()

            # 检查是否超过结束时间
            if now > end_time:
                print("\n🌙 已到达结束时间，停止运行")
                self.log("到达结束时间，停止运行")

                # 结束前抓取flight数据（如果还没抓）
                if not flight_data_fetched_today:
                    print("\n📊 抓取今日Flight数据（运力统计）...")
                    if self.fetch_flight_data():
                        flight_data_fetched_today = True
                        self.stats['flight_success_count'] += 1
                    else:
                        self.stats['flight_failure_count'] += 1

                break

            # 每分钟检查一次
            if last_check_time is None or (now - last_check_time) >= check_interval:
                print(f"\n{'='*60}")
                print(f"🔍 [{now.strftime('%H:%M:%S')}] 检查航班状态...")
                print('='*60)

                # 更新航班跟踪状态（读取最新leg数据）
                # 注意: 这里需要从leg_data.csv读取最新状态
                # 为了简化，我们在每次fetch_leg_data后自动更新tracker

                # 决定应该监控哪个页面
                should_monitor_leg = self.flight_tracker.should_monitor_leg_first(now)

                if should_monitor_leg:
                    # 监控Leg页面
                    if self.current_monitor_mode != 'leg':
                        print("🔄 切换到 Leg 数据页面监控")
                        self.current_monitor_mode = 'leg'

                    print("📊 监控 Leg 数据（航段状态）...")
                    self.stats['leg_fetch_count'] += 1

                    if self.fetch_and_update_leg_data():
                        self.stats['leg_success_count'] += 1
                        print("✅ Leg数据检查完成")
                    else:
                        self.stats['leg_failure_count'] += 1
                        print("⚠️ Leg数据检查失败")

                else:
                    # 监控故障页面
                    if self.current_monitor_mode != 'faults':
                        print("🔄 切换到故障监控页面")
                        self.current_monitor_mode = 'faults'

                    print("🔧 监控故障数据...")
                    self.stats['faults_fetch_count'] += 1

                    if self.fetch_faults_data():
                        self.stats['faults_success_count'] += 1
                        print("✅ 故障数据检查完成")
                    else:
                        self.stats['faults_failure_count'] += 1
                        print("⚠️ 故障数据检查失败")

                # 显示当前状态摘要
                print(self.flight_tracker.get_status_summary())

                last_check_time = now

            # 短暂休眠避免CPU占用过高
            time.sleep(10)

        # 发送汇总报告
        self.send_summary_report()

    def send_summary_report(self):
        """发送汇总报告"""
        if not self.notifier or not self.notifier.is_enabled():
            return

        report_data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'leg_fetch_count': self.stats['leg_fetch_count'],
            'leg_success_count': self.stats['leg_success_count'],
            'leg_failure_count': self.stats['leg_failure_count'],
            'flight_fetch_count': self.stats['flight_fetch_count'],
            'flight_success_count': self.stats['flight_success_count'],
            'flight_failure_count': self.stats['flight_failure_count'],
            'faults_fetch_count': self.stats['faults_fetch_count'],
            'faults_success_count': self.stats['faults_success_count'],
            'faults_failure_count': self.stats['faults_failure_count']
        }

        self.notifier.send_summary_report(report_data)

    def fetch_and_update_leg_data(self, target_date=None):
        """
        抓取并更新航段数据（完整流程）
        1. Fetch leg data
        2. Update leg data（仅在状态变化时）
        3. 更新 flight_tracker 状态
        4. 自动触发邮件通知

        Args:
            target_date: 可选的目标日期

        Returns:
            bool: 整体是否成功
        """
        # 步骤1: 抓取数据
        fetch_success = self.fetch_leg_data()
        if not fetch_success:
            print("❌ 数据抓取失败，跳过更新")
            return False

        # 步骤2: 更新数据（会自动检测状态变化和发送邮件）
        if target_date is None:
            target_date = datetime.now().strftime('%Y-%m-%d')

        update_success = self.run_update_script(
            'leg_data_update',
            '航段数据更新',
            target_date
        )

        # 步骤3: 更新flight_tracker状态
        if update_success:
            try:
                import pandas as pd
                from pathlib import Path

                leg_data_file = Path("data/leg_data.csv")
                if leg_data_file.exists():
                    df = pd.read_csv(leg_data_file)
                    today = datetime.now().strftime('%Y-%m-%d')

                    # 只读取今天的最新数据（CSV列名是中文'日期'）
                    today_data = df[df['日期'] == today].to_dict('records')

                    if today_data:
                        self.flight_tracker.update_from_latest_leg_data(today_data)
                        self.log(f"已更新flight_tracker状态，共{len(today_data)}条记录")

            except Exception as e:
                self.log(f"更新flight_tracker失败: {e}", "ERROR")

        return update_success

    def run_interactive(self):
        """交互式运行（用于测试）"""
        print("\n🎯 交互式模式")
        print("="*60)
        print("1. 抓取并更新航段数据（Fetch & Update Leg Data）")
        print("   - 抓取最新数据")
        print("   - 检测状态变化并更新")
        print("   - 自动发送邮件通知")
        print("2. 抓取故障数据（Faults Data）")
        print("3. 抓取飞行数据（Flight Data - 运力统计）")
        print("4. 退出")
        print("="*60)

        while True:
            choice = input("\n请选择操作 (1-4): ").strip()

            if choice == '1':
                print("\n📋 执行航段数据完整流程...")
                self.stats['leg_fetch_count'] = self.stats.get('leg_fetch_count', 0) + 1

                if self.fetch_and_update_leg_data():
                    self.stats['leg_success_count'] = self.stats.get('leg_success_count', 0) + 1
                    print("\n✅ 航段数据流程执行完成")
                else:
                    self.stats['leg_failure_count'] = self.stats.get('leg_failure_count', 0) + 1
                    print("\n⚠️ 航段数据流程执行失败")

            elif choice == '2':
                self.stats['faults_fetch_count'] += 1
                if self.fetch_faults_data():
                    self.stats['faults_success_count'] += 1
                else:
                    self.stats['faults_failure_count'] += 1

            elif choice == '3':
                self.stats['flight_fetch_count'] += 1
                if self.fetch_flight_data():
                    self.stats['flight_success_count'] += 1
                else:
                    self.stats['flight_failure_count'] += 1

            elif choice == '4':
                print("\n👋 退出系统")
                self.send_summary_report()
                break

            else:
                print("❌ 无效选择，请重新输入")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🛫 航班数据抓取系统")
    print("="*60)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    scheduler = TaskScheduler()

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        # 交互式模式
        scheduler.run_interactive()
    else:
        # 调度模式
        try:
            scheduler.run_daily_schedule()
        except KeyboardInterrupt:
            print("\n\n⚠️ 收到中断信号，正在退出...")
            scheduler.send_summary_report()
        except Exception as e:
            print(f"\n❌ 系统错误: {e}")
            scheduler.log(f"系统错误: {e}", "ERROR")


if __name__ == "__main__":
    main()

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
from core.logger import get_logger
from core.notifier import GmailNotifier


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

        # 统计数据
        self.stats = {
            'leg_fetch_count': 0,
            'leg_success_count': 0,
            'leg_failure_count': 0,
            'flight_fetch_count': 0,
            'flight_success_count': 0,
            'flight_failure_count': 0,
            'faults_fetch_count': 0,
            'faults_success_count': 0,
            'faults_failure_count': 0
        }

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
        """运行每日调度"""
        scheduler_config = self.config['scheduler']

        # 解析时间配置
        start_time = self.parse_time(scheduler_config['start_time'])
        end_time = self.parse_time(scheduler_config['end_time'])

        # 解析任务时间
        leg_times = [self.parse_time(t) for t in scheduler_config.get('leg_fetch_times', '').split(',') if t.strip()]
        flight_times = [self.parse_time(t) for t in scheduler_config['flight_fetch_times'].split(',')]
        faults_times = [self.parse_time(t) for t in scheduler_config['faults_fetch_times'].split(',')]

        # 合并所有任务时间并排序
        all_times = []
        for t in leg_times:
            all_times.append(('leg', t))
        for t in flight_times:
            all_times.append(('flight', t))
        for t in faults_times:
            all_times.append(('faults', t))

        all_times.sort(key=lambda x: x[1])

        print("\n" + "="*60)
        print("📅 调度计划:")
        print("="*60)
        for task_type, task_time in all_times:
            task_names = {
                'leg': '航段数据抓取',
                'flight': '飞行数据抓取（运力统计）',
                'faults': '故障数据抓取'
            }
            task_name = task_names.get(task_type, task_type)
            print(f"  {task_time.strftime('%H:%M')} - {task_name}")

        print(f"\n⏰ 运行时间: {scheduler_config['start_time']} - {scheduler_config['end_time']}")
        print("="*60)

        # 等待到启动时间
        now = datetime.now()
        if start_time > now:
            self.wait_until_time(start_time)

        # 主循环
        running = True
        task_index = 0

        while running:
            now = datetime.now()

            # 检查是否超过结束时间
            if now > end_time:
                print("\n🌙 已到达结束时间，停止运行")
                self.log("到达结束时间，停止运行")
                break

            # 检查是否有任务需要执行
            if task_index < len(all_times):
                task_type, task_time = all_times[task_index]

                if now >= task_time:
                    if task_type == 'leg':
                        self.stats['leg_fetch_count'] += 1
                        if self.fetch_leg_data():
                            self.stats['leg_success_count'] += 1
                        else:
                            self.stats['leg_failure_count'] += 1
                    elif task_type == 'flight':
                        self.stats['flight_fetch_count'] += 1
                        if self.fetch_flight_data():
                            self.stats['flight_success_count'] += 1
                        else:
                            self.stats['flight_failure_count'] += 1
                    elif task_type == 'faults':
                        self.stats['faults_fetch_count'] += 1
                        if self.fetch_faults_data():
                            self.stats['faults_success_count'] += 1
                        else:
                            self.stats['faults_failure_count'] += 1

                    task_index += 1

            # 短暂休眠避免CPU占用过高
            time.sleep(30)

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

    def run_interactive(self):
        """交互式运行（用于测试）"""
        print("\n🎯 交互式模式")
        print("="*60)
        print("1. 抓取航段数据（Leg Data）")
        print("2. 抓取故障数据（Faults Data）")
        print("3. 抓取飞行数据（Flight Data - 运力统计）")
        print("4. 退出")
        print("="*60)

        while True:
            choice = input("\n请选择操作 (1-4): ").strip()

            if choice == '1':
                self.stats['leg_fetch_count'] = self.stats.get('leg_fetch_count', 0) + 1
                if self.fetch_leg_data():
                    self.stats['leg_success_count'] = self.stats.get('leg_success_count', 0) + 1
                else:
                    self.stats['leg_failure_count'] = self.stats.get('leg_failure_count', 0) + 1

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

# -*- coding: utf-8 -*-
"""
统一调度器 - 单进程模式

核心改进：
- 废弃多进程模式，所有 Fetcher 在同一进程内运行
- 避免跨进程竞争条件和资源冲突
- 更稳定的标签页管理和浏览器连接
"""
import sys
import os
import time
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
from fetchers.leg_fetcher import LegFetcher
from fetchers.fault_fetcher import FaultFetcher


class UnifiedScheduler:
    """统一调度器类（单进程模式）"""

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
        aircraft_list = self.config.get('aircraft_list', [])
        self.flight_tracker = FlightTracker(monitored_aircraft=aircraft_list)

        # ========== 核心改进：在同一进程内创建所有 Fetcher ==========
        print("\n" + "="*60)
        print("🔧 初始化统一调度器（单进程模式）")
        print("="*60)

        # 创建 Fetcher 实例（共享同一个浏览器连接）
        self.leg_fetcher = LegFetcher()
        self.fault_fetcher = FaultFetcher()

        print("✅ LegFetcher 已创建")
        print("✅ FaultFetcher 已创建")
        print("💡 所有 Fetcher 将在同一进程内运行")
        print("="*60)

        # 统计数据
        self.stats = {
            'leg_fetch_count': 0,
            'leg_success_count': 0,
            'leg_failure_count': 0,
            'fault_check_count': 0,
            'fault_success_count': 0,
            'fault_failure_count': 0,
        }

        self.log("统一调度器初始化完成")

    def connect_all_fetchers(self):
        """
        连接所有 Fetcher 到浏览器

        核心改进：
        - 确保所有 Fetcher 共享同一个浏览器连接
        - 为每个 Fetcher 分配独立的标签页
        - 基于 URL 匹配的标签页管理

        Returns:
            bool: 是否成功
        """
        print("\n" + "="*60)
        print("🌐 连接浏览器并分配标签页")
        print("="*60)

        try:
            # 步骤1：连接 LegFetcher
            print("\n📍 步骤1: 连接 LegFetcher...")
            self.leg_page = self.leg_fetcher.connect_browser()
            if not self.leg_page:
                print("❌ LegFetcher 连接失败")
                return False
            print("✅ LegFetcher 已连接")

            # 步骤2：连接 FaultFetcher
            print("\n📍 步骤2: 连接 FaultFetcher...")
            self.fault_page = self.fault_fetcher.connect_browser()
            if not self.fault_page:
                print("❌ FaultFetcher 连接失败")
                return False
            print("✅ FaultFetcher 已连接")

            print("\n" + "="*60)
            print("✅ 所有 Fetcher 已成功连接")
            print("="*60)
            return True

        except Exception as e:
            print(f"❌ 连接失败: {e}")
            self.log(f"连接浏览器失败: {e}", "ERROR")
            return False

    def login_all_fetchers(self):
        """
        为所有 Fetcher 执行登录

        核心改进：
        - 共享登录状态（Cookie共享）
        - 只需第一个 Fetcher 执行完整登录
        - 后续 Fetcher 直接跳转即可

        Returns:
            bool: 是否成功
        """
        print("\n" + "="*60)
        print("🔑 执行智能登录")
        print("="*60)

        try:
            # 只需对 LegFetcher 执行登录（Cookie 会自动共享）
            print("\n📍 步骤1: LegFetcher 登录...")
            if not self.leg_fetcher.smart_login(self.leg_page):
                print("❌ LegFetcher 登录失败")
                return False
            print("✅ LegFetcher 登录成功")

            # FaultFetcher 可以直接跳转（无需重新登录）
            print("\n📍 步骤2: FaultFetcher 使用共享登录状态...")
            print("💡 Cookie 已自动共享，无需重新登录")
            print("✅ FaultFetcher 准备就绪")

            print("\n" + "="*60)
            print("✅ 所有 Fetcher 登录完成")
            print("="*60)
            return True

        except Exception as e:
            print(f"❌ 登录失败: {e}")
            self.log(f"登录失败: {e}", "ERROR")
            return False

    def fetch_leg_data(self):
        """
        抓取航段数据（在同一进程内）

        Returns:
            bool: 是否成功
        """
        print(f"\n{'='*60}")
        print(f"🚀 执行任务: 航段数据抓取")
        print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('='*60)

        self.log("开始抓取航段数据")

        try:
            # 确保在正确的标签页上操作
            if not self.leg_fetcher.ensure_assigned_tab(self.leg_page):
                print("⚠️  标签页切换失败")
                return False

            # 执行抓取
            target_date = datetime.now().strftime('%Y-%m-%d')
            data = self.leg_fetcher.navigate_to_target_page(self.leg_page, target_date)

            if data:
                # 保存数据
                csv_file = self.leg_fetcher.save_to_csv(
                    data,
                    filename=f"leg_data_{target_date}.csv"
                )

                if csv_file:
                    print(f"✅ 航段数据抓取成功")
                    print(f"📄 文件路径: {csv_file}")
                    self.log(f"航段数据抓取成功: {csv_file}", "SUCCESS")
                    return True
                else:
                    print("❌ 保存失败")
                    self.log("保存航段数据失败", "ERROR")
                    return False
            else:
                print("❌ 未提取到数据")
                self.log("未提取到航段数据", "ERROR")
                return False

        except Exception as e:
            print(f"❌ 航段数据抓取出错: {e}")
            self.log(f"航段数据抓取出错: {e}", "ERROR")
            return False

    def check_fault_data(self):
        """
        抓取故障数据（在同一进程内）

        Returns:
            bool: 是否成功
        """
        print(f"\n{'='*60}")
        print(f"🔍 执行任务: 故障数据抓取")
        print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('='*60)

        self.log("开始抓取故障数据")

        try:
            # 确保在正确的标签页上操作
            if not self.fault_fetcher.ensure_assigned_tab(self.fault_page):
                print("⚠️  标签页切换失败")
                return False

            # 获取配置的飞机列表
            aircraft_list = self.config.get('aircraft_list', [])
            target_date = datetime.now().strftime('%Y-%m-%d')

            # 执行抓取
            data = self.fault_fetcher.navigate_to_target_page(
                self.fault_page,
                target_date,
                aircraft_list
            )

            if data:
                # 保存数据
                csv_file = self.fault_fetcher.save_to_csv(
                    data,
                    filename=f"fault_data_{target_date}.csv"
                )

                if csv_file:
                    print(f"✅ 故障数据抓取成功")
                    print(f"📄 文件路径: {csv_file}")
                    self.log(f"故障数据抓取成功: {csv_file}", "SUCCESS")
                    return True
                else:
                    print("❌ 保存失败")
                    self.log("保存故障数据失败", "ERROR")
                    return False
            else:
                print("❌ 未提取到数据")
                self.log("未提取到故障数据", "ERROR")
                return False

        except Exception as e:
            print(f"❌ 故障数据抓取出错: {e}")
            self.log(f"故障数据抓取出错: {e}", "ERROR")
            return False

    def parse_time(self, time_str: str) -> datetime:
        """解析时间字符串为今天的datetime对象"""
        today = datetime.now().date()
        hour, minute = map(int, time_str.split(':'))
        return datetime.combine(today, datetime.min.time()) + timedelta(hours=hour, minutes=minute)

    def run_daily_schedule(self):
        """
        运行每日调度 - 单进程智能监控

        监控策略:
        1. 持续监控 leg 页面（每分钟检查）
        2. 定期检查 fault 页面（每5分钟）
        3. 检测航段状态变化并自动通知
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
        print("🎯 监控模式: 单进程智能监控")
        print("   - Leg数据: 每分钟检查")
        print("   - Fault数据: 每5分钟检查")
        print("   - 自动检测状态变化并通知")
        print("="*60)

        # ========== 初始化阶段 ==========
        print("\n🔧 初始化阶段...")
        if not self.connect_all_fetchers():
            print("❌ 浏览器连接失败，退出")
            return

        if not self.login_all_fetchers():
            print("❌ 登录失败，退出")
            return

        # 等待到启动时间
        now = datetime.now()
        if start_time > now:
            print(f"\n⏰ 等待至 {start_time.strftime('%Y-%m-%d %H:%M:%S')}...")
            time.sleep((start_time - now).total_seconds())

        # ========== 主监控循环 ==========
        print("\n🚀 开始智能监控...")
        print(self.flight_tracker.get_status_summary())

        last_leg_check = None
        last_fault_check = None
        leg_interval = timedelta(minutes=1)
        fault_interval = timedelta(minutes=5)

        while True:
            now = datetime.now()

            # 检查是否超过结束时间
            if now > end_time:
                print("\n🌙 已到达结束时间，停止运行")
                self.log("到达结束时间，停止运行")
                break

            # 每分钟检查 Leg 数据
            if last_leg_check is None or (now - last_leg_check) >= leg_interval:
                print(f"\n{'='*60}")
                print(f"🔍 [{now.strftime('%H:%M:%S')}] 检查航段状态...")
                print('='*60)

                self.stats['leg_fetch_count'] += 1

                if self.fetch_leg_data():
                    self.stats['leg_success_count'] += 1
                    print("✅ Leg数据检查完成")
                else:
                    self.stats['leg_failure_count'] += 1
                    print("⚠️ Leg数据检查失败")

                last_leg_check = now

                # 更新 flight_tracker 状态
                try:
                    import pandas as pd
                    from pathlib import Path

                    leg_data_file = Path("data/leg_data.csv")
                    if leg_data_file.exists():
                        df = pd.read_csv(leg_data_file)
                        today = datetime.now().strftime('%Y-%m-%d')

                        if '日期' in df.columns:
                            today_data = df[df['日期'] == today].to_dict('records')
                        else:
                            self.log("CSV中缺少'日期'列", "ERROR")
                            today_data = []

                        if today_data:
                            self.flight_tracker.update_from_latest_leg_data(today_data)
                            self.log(f"已更新flight_tracker状态，共{len(today_data)}条记录")

                except Exception as e:
                    self.log(f"更新flight_tracker失败: {e}", "ERROR")

                # 显示当前状态摘要
                print(self.flight_tracker.get_status_summary())

            # 每5分钟检查 Fault 数据
            if last_fault_check is None or (now - last_fault_check) >= fault_interval:
                print(f"\n{'='*60}")
                print(f"🔍 [{now.strftime('%H:%M:%S')}] 检查故障状态...")
                print('='*60)

                self.stats['fault_check_count'] += 1

                if self.check_fault_data():
                    self.stats['fault_success_count'] += 1
                    print("✅ Fault数据检查完成")
                else:
                    self.stats['fault_failure_count'] += 1
                    print("⚠️ Fault数据检查失败")

                last_fault_check = now

            # 短暂休眠避免CPU占用过高
            time.sleep(10)

    def run_interactive(self):
        """交互式运行（用于测试）"""
        print("\n🎯 交互式模式")
        print("="*60)
        print("1. 抓取航段数据（Fetch Leg Data）")
        print("2. 检查故障数据（Check Fault Data）")
        print("3. 同时执行两者（Both）")
        print("4. 退出")
        print("="*60)

        while True:
            choice = input("\n请选择操作 (1-4): ").strip()

            if choice == '1':
                print("\n📋 执行航段数据抓取...")
                self.stats['leg_fetch_count'] = self.stats.get('leg_fetch_count', 0) + 1

                if self.fetch_leg_data():
                    self.stats['leg_success_count'] = self.stats.get('leg_success_count', 0) + 1
                    print("\n✅ 航段数据抓取完成")
                else:
                    self.stats['leg_failure_count'] = self.stats.get('leg_failure_count', 0) + 1
                    print("\n⚠️ 航段数据抓取失败")

            elif choice == '2':
                print("\n📋 执行故障数据检查...")
                self.stats['fault_check_count'] = self.stats.get('fault_check_count', 0) + 1

                if self.check_fault_data():
                    self.stats['fault_success_count'] = self.stats.get('fault_success_count', 0) + 1
                    print("\n✅ 故障数据检查完成")
                else:
                    self.stats['fault_failure_count'] = self.stats.get('fault_failure_count', 0) + 1
                    print("\n⚠️ 故障数据检查失败")

            elif choice == '3':
                print("\n📋 同时执行航段数据和故障数据检查...")

                leg_success = self.fetch_leg_data()
                fault_success = self.check_fault_data()

                if leg_success and fault_success:
                    print("\n✅ 所有任务执行完成")
                else:
                    print("\n⚠️ 部分任务执行失败")

            elif choice == '4':
                print("\n👋 退出系统")
                break

            else:
                print("❌ 无效选择，请重新输入")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🛫 航段数据监控系统 - 统一调度器")
    print("="*60)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    scheduler = UnifiedScheduler()

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        # 交互式模式
        # 首先连接浏览器
        if not scheduler.connect_all_fetchers():
            print("❌ 浏览器连接失败，退出")
            return

        if not scheduler.login_all_fetchers():
            print("❌ 登录失败，退出")
            return

        scheduler.run_interactive()
    else:
        # 调度模式
        try:
            scheduler.run_daily_schedule()
        except KeyboardInterrupt:
            print("\n\n⚠️ 收到中断信号，正在退出...")
        except Exception as e:
            print(f"\n❌ 系统错误: {e}")
            scheduler.log(f"系统错误: {e}", "ERROR")


if __name__ == "__main__":
    main()

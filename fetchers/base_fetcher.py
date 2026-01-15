# -*- coding: utf-8 -*-
"""
数据抓取基类

提供公共功能:
- 配置文件读取
- 浏览器连接管理
- 智能登录系统
- 日期处理
- CSV保存
- 工具函数
"""
from DrissionPage import ChromiumPage, ChromiumOptions
import time
import csv
import configparser
import os
import shutil
from datetime import datetime
from abc import ABC, abstractmethod
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.logger import get_logger
from config.config_loader import ConfigLoader


class BaseFetcher(ABC):
    """数据抓取基类"""

    # 类级别的浏览器实例管理（支持多端口）
    _browsers = {}  # 按端口存储浏览器实例 {port: ChromiumPage}

    def get_browser_port(self):
        """
        获取浏览器端口（子类可重写）

        Returns:
            int: 浏览器调试端口，默认 9222
        """
        return 9222

    def get_browser_user_data_path(self):
        """
        获取浏览器用户数据路径（子类可重写）

        Returns:
            str: 用户数据路径
        """
        return self.user_data_path

    def __init__(self, config_file=None):
        """
        初始化

        :param config_file: 配置文件路径,默认为 config/config.ini
        """
        self.config_file = config_file or os.path.join(project_root, 'config/config.ini')
        self.cfg = None
        self.user_data_path = None
        self.aircraft_list = []
        self.log = get_logger()

        # 初始化状态标记（避免重复设置机号和日期）
        self._initialized = False
        self._initialized_date = None  # 记录已初始化的日期
        self.fetcher_name = self.__class__.__name__  # 记录fetcher类型名称

        # 加载配置
        self._load_config()

    def _load_config(self):
        """加载配置文件（优先从环境变量读取敏感配置）"""
        # 使用统一的配置加载器（自动从环境变量和 config.ini 加载）
        config_loader = ConfigLoader(self.config_file)

        try:
            self.cfg = {
                'username': config_loader.get_credentials()['username'],
                'password': config_loader.get_credentials()['password'],
                'user_data_path': config_loader.get_paths()['user_data_path'],
                'target_url': config_loader.get_target_url()
            }
            self.user_data_path = self.cfg['user_data_path']
        except Exception as e:
            raise ValueError(f"配置文件缺失: {e}")

        # 读取飞机号列表
        self.aircraft_list = config_loader.get_aircraft_list()
        if self.aircraft_list:
            print(f"✅ 读取到 {len(self.aircraft_list)} 架飞机: {', '.join(self.aircraft_list)}")
        else:
            print("⚠️ 配置文件中未找到飞机号列表,使用默认值")
            self.aircraft_list = ["B-652G", "B-656E"]

    def _cleanup_old_backups(self, backup_dir, base_name, extension, keep_count=2):
        """
        清理旧备份文件，只保留最新的几个

        :param backup_dir: 备份目录
        :param base_name: 文件基础名称（如 'leg_data'）
        :param extension: 文件扩展名（如 '.csv'）
        :param keep_count: 保留的备份数量，默认为2
        """
        try:
            # 获取所有匹配的备份文件
            pattern = f"{base_name}_*{extension}"
            backup_files = []

            for filename in os.listdir(backup_dir):
                if filename.startswith(f"{base_name}_") and filename.endswith(extension):
                    filepath = os.path.join(backup_dir, filename)
                    # 获取文件修改时间
                    mtime = os.path.getmtime(filepath)
                    backup_files.append((filepath, mtime, filename))

            # 按修改时间排序（最新的在前）
            backup_files.sort(key=lambda x: x[1], reverse=True)

            # 如果文件数量超过保留数量，删除旧的
            if len(backup_files) > keep_count:
                files_to_delete = backup_files[keep_count:]
                for filepath, _, filename in files_to_delete:
                    os.remove(filepath)
                    print(f"   🗑️  删除旧备份: {filename}")

        except Exception as e:
            print(f"   ⚠️ 清理旧备份失败: {e}")

    @staticmethod
    def get_today_date():
        """获取当天日期,格式: YYYY-MM-DD"""
        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def wait_and_click(page, selector, timeout=10, desc="元素"):
        """等待元素出现并点击"""
        for i in range(timeout):
            ele = page.ele(selector)
            if ele and ele.states.is_displayed:
                print(f"   ✅ 找到 {desc}")
                ele.click(by_js=True)
                time.sleep(1)
                return True
            time.sleep(1)
            print(f"   ⏳ 等待 {desc}... ({i+1}/{timeout})")
        print(f"   ❌ 超时: 未找到 {desc}")
        return False

    def connect_browser(self):
        """
        连接到浏览器

        核心改进：
        - 支持多端口浏览器实例管理
        - 子类通过重写 get_browser_port() 指定端口
        - 每个端口使用独立的浏览器实例

        :return: ChromiumPage 对象,失败返回 None
        """
        # 获取子类指定的端口配置
        port = self.get_browser_port()
        user_data_path = self.get_browser_user_data_path()

        # 按端口管理浏览器实例
        if port not in BaseFetcher._browsers:
            co = ChromiumOptions()
            co.set_user_data_path(user_data_path)
            co.set_local_port(port)

            try:
                print(f"\n{'='*60}")
                print(f"🌐 初始化浏览器连接...")
                print(f"📍 端口: {port}")
                print(f"📍 用户数据: {user_data_path}")
                print(f"{'='*60}")
                BaseFetcher._browsers[port] = ChromiumPage(co)
                print(f"✅ 浏览器连接成功!")
                self.log(f"Browser connected successfully (port: {port})", "INFO")
            except Exception as e:
                print(f"❌ 浏览器连接失败: {e}")
                print(f"请确保Chrome调试模式已启动 (端口{port})")
                self.log(f"Browser connection failed: {e}", "ERROR")
                return None

        # 返回浏览器对象
        return BaseFetcher._browsers[port]

    def smart_login(self, page, target_url=None):
        """
        智能登录系统 - 自动检测并处理各种页面状态

        核心优化:
        1. 检查是否已在目标页面（lineLogController 或 integratedMonitorController）
        2. 如果已在目标页面，直接返回，不做任何跳转
        3. 只在必要时才执行登录和跳转逻辑
        4. 如果提供了 target_url，登录成功后直接跳转到目标页面

        :param page: ChromiumPage 对象
        :param target_url: 目标URL（可选），登录成功后直接跳转
        :return: 成功返回 True,失败返回 False
        """
        print("\n🔍 检查当前页面状态...")
        current_url = page.url
        print(f"📍 当前URL: {current_url}")

        # ========== 优先级1: 检查是否在系统首页 ==========
        if "mainController/index.html" in current_url:
            print("✅ 已在系统首页: mainController/index.html")
            self.log("Already at main page", "INFO")
            return True

        # ========== 优先级3: 处理登录流程 ==========
        # 如果在新标签页,导航到登录页
        if "chrome://" in current_url or current_url == "about:blank" or "newtab" in current_url:
            print("🌐 检测到空白页,导航到登录页面...")
            page.get("https://cis2.comac.cc:8040/portal/")
            time.sleep(2)
            current_url = page.url

        # 判断页面状态
        is_blank_page = "chrome://" in current_url or current_url == "about:blank" or "newtab" in current_url
        is_login_page = ("portal" in current_url and "login" in current_url) or "rbacUsersController/login.html" in current_url
        is_in_system = ("cis.comac.cc:8004" in current_url or "cis.comac.cc:8010" in current_url)

        # 如果已在系统内但不在首页，也认为就绪（由子类决定是否需要导航）
        if is_in_system:
            print(f"✅ 已在系统内")
            self.log("Already in system", "INFO")
            return True

        # 如果不在登录流程中，导航到首页
        if not is_blank_page and not is_login_page:
            print("🚀 不在登录流程中,导航到系统首页...")
            page.get("https://cis.comac.cc:8004/caphm/mainController/index.html")
            time.sleep(2)
            current_url = page.url

        # 智能等待:监控所有可能的页面状态
        print("\n⏳ 智能监控页面跳转...")
        max_wait = 90  # 增加等待时间到90秒
        found_target = False
        login_executed = False

        for i in range(max_wait):
            # 实时检测URL变化
            current_url = page.url

            # 每5秒打印一次URL
            if i % 10 == 0:
                print(f"   📍 [{i//2}s] 当前URL: {current_url}")

            # 情况1: 已在目标首页
            if "mainController/index.html" in current_url:
                print(f"   ✅ 已在首页!")
                found_target = True
                break

            # 情况2: 在portal登录页 - 需要填充账号密码
            # 修改检测条件：portal 在URL中 或者 cis.comac.cc 在URL中且能找到密码框
            is_portal_page = "portal" in current_url
            is_cis_login = "cis.comac.cc" in current_url and page.ele('#loginPwd')

            if (is_portal_page or is_cis_login) and not login_executed:
                pwd_ele = page.ele('#loginPwd')
                if pwd_ele:
                    print(f"   🔒 检测到登录页,开始登录...")
                    try:
                        # 填账号
                        user_ele = page.ele('tag:input@@placeholder=请输入账号')
                        if not user_ele:
                            user_ele = page.ele('tag:input@@type=text')
                        if not user_ele:
                            # 尝试通过name属性查找
                            user_ele = page.ele('tag:input@@name=username')

                        if user_ele:
                            print(f"   ✅ 找到账号输入框")
                            user_ele.clear()
                            user_ele.input(self.cfg['username'])
                            print(f"   📝 账号已填写")  # 不再打印具体账号信息
                            try:
                                page.ele('text:FLYWIN').click(by_js=True)
                            except:
                                pass

                        # 填密码并提交
                        pwd_ele = page.ele('#loginPwd')
                        if pwd_ele:
                            print(f"   ✅ 找到密码输入框")
                            pwd_ele.clear()
                            pwd_ele.input(self.cfg['password'])
                            print(f"   📝 密码已填写")
                            print(f"   ⚡ 提交登录...")
                            pwd_ele.input('\n')
                            login_executed = True

                    except Exception as e:
                        print(f"   ❌ 登录出错: {e}")
                        import traceback
                        traceback.print_exc()

            # 情况3: 在rbacUsersController中间页 - 需要点击WEB
            elif "rbacUsersController/login.html" in current_url:
                web_btn = page.ele('text:WEB')
                if web_btn and web_btn.states.is_displayed:
                    print(f"   👀 检测到中间页,点击 'WEB' 按钮...")
                    web_btn.click(by_js=True)

            # 情况4: 已在系统内其他页面（支持8004和8010端口）
            elif ("cis.comac.cc:8004" in current_url or "cis.comac.cc:8010" in current_url):
                print(f"   ✅ 已在系统内")
                found_target = True
                break

            # 每5秒打印一次进度(减少输出)
            if i % 10 == 0 and i > 0:
                print(f"   ⏳ 等待中... {i//2}秒", end="\r")

            # 快速检测,0.5秒间隔
            time.sleep(0.5)

        print()  # 换行

        # 最终验证
        if found_target or "mainController/index.html" in page.url:
            print(f"🎉 准备完成!当前页面: {page.title}")
            self.log("系统就绪", "SUCCESS")

            # 如果提供了目标URL，直接跳转（避免二次跳转被拦截）
            if target_url:
                print(f"🎯 登录成功，直接跳转到目标页面...")
                print(f"   📍 目标URL: {target_url}")
                try:
                    # 记录跳转前的URL
                    before_url = page.url
                    print(f"   📍 跳转前URL: {before_url}")

                    page.get(target_url)

                    # 等待页面加载完成
                    print("   ⏳ 等待目标页面加载...")
                    success = False
                    for i in range(15):  # 增加到15秒
                        current_url = page.url
                        # 检查是否已到达目标页面（通过URL关键词）
                        if "integratedMonitorController" in current_url or "lineLogController" in current_url:
                            print(f"   ✅ 已到达目标页面 (耗时: {i+1}秒)")
                            print(f"   📍 最终URL: {current_url}")
                            success = True
                            break
                        print(f"   ⏳ 加载中... URL: {current_url[:80]}... ({i+1}/15秒)")
                        time.sleep(1)

                    if not success:
                        print(f"   ⚠️ 页面加载超时，可能被重定向")
                        print(f"   📍 最终URL: {page.url}")
                        print(f"   💡 将在后续流程中尝试重新跳转")

                except Exception as e:
                    print(f"   ❌ 跳转失败: {e}")
                    import traceback
                    traceback.print_exc()
                    print(f"   💡 将在后续流程中重试")

            return True
        else:
            print(f"❌ 超时或异常,当前页面: {page.url}")
            self.log("页面状态异常", "ERROR")
            return False

    def save_to_csv(self, data, filename=None, subdir='data/daily_raw'):
        """
        保存数据到CSV文件(覆盖模式)

        :param data: 要保存的数据(二维列表)
        :param filename: 文件名,不指定则自动生成
        :param subdir: 子目录名,默认为 'data/daily_raw'
        :return: 保存成功返回文件路径,失败返回 None
        """
        if not data:
            print("   ❌ 没有数据可保存")
            return None

        # 生成文件名
        if not filename:
            today = self.get_today_date()
            filename = f"{self.get_data_prefix()}_{today}.csv"

        # 确保目录存在
        data_dir = os.path.join(project_root, subdir)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            print(f"   📁 创建文件夹: {data_dir}")

        filepath = os.path.join(data_dir, filename)

        # 备份策略：只备份 data/leg_data.csv 总表，最多保留2个备份
        needs_backup = (
            subdir == 'data' and  # 只在 data 文件夹下
            filename == 'leg_data.csv' and  # 只备份总表
            os.path.exists(filepath)  # 文件已存在
        )

        if needs_backup:
            backup_dir = os.path.join(project_root, 'data', 'backup')
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)

            # 生成带时间戳的备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(filename)
            backup_filename = f"{name}_{timestamp}{ext}"
            backup_path = os.path.join(backup_dir, backup_filename)

            try:
                # 先备份当前文件
                shutil.copy2(filepath, backup_path)
                print(f"   💾 已备份总表: {backup_path}")

                # 清理旧备份，只保留最新的2个
                self._cleanup_old_backups(backup_dir, name, ext, keep_count=2)

            except Exception as e:
                print(f"   ⚠️ 备份失败: {e}")

        try:
            # 使用 'w' 模式覆盖写入
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerows(data)
            print(f"\n✅ 数据已保存到: {filepath}")
            return filepath
        except Exception as e:
            print(f"   ❌ 保存CSV失败: {e}")
            return None

    @abstractmethod
    def get_data_prefix(self):
        """返回数据文件前缀,子类必须实现"""
        pass

    @abstractmethod
    def navigate_to_target_page(self, page, target_date):
        """
        导航到目标页面并执行抓取逻辑
        子类必须实现

        :param page: ChromiumPage 对象
        :param target_date: 目标日期
        :return: 成功返回数据,失败返回 None
        """
        pass

    def main(self, target_date=None):
        """
        主函数模板方法

        :param target_date: 目标日期,不指定则使用今天
        :return: 成功返回 True,失败返回 False
        """
        # 确定要抓取的日期
        if target_date:
            target = target_date
            print(f"🎯 目标日期:{target}")
            self.log(f"Fetching data for: {target}")
        else:
            target = self.get_today_date()
            print(f"🎯 默认抓取今天的数据:{target}")
            self.log(f"Fetching today's data: {target}")

        # 连接浏览器
        page = self.connect_browser()
        if not page:
            return False

        # 智能登录
        if not self.smart_login(page):
            return False

        time.sleep(0.5)

        # 导航到目标页面并执行抓取(子类实现)
        print("\n🎯 开始执行抓取流程...")
        data = self.navigate_to_target_page(page, target)

        # 保存数据(子类可以选择是否在 navigate_to_target_page 中保存)
        if data:
            csv_file = self.save_to_csv(data, filename=f"{self.get_data_prefix()}_{target}.csv")
            if csv_file:
                print(f"\n🎉 数据抓取完成!")
                print(f"📄 文件路径: {csv_file}")
                print(f"📊 总记录数: {len(data) - 1 if len(data) > 1 else 0}")
                self.log(f"Data saved successfully: {csv_file}", "SUCCESS")
            else:
                print("\n❌ 保存失败")
                self.log("Failed to save data", "ERROR")
                return False
        else:
            print("\n❌ 未提取到数据")
            self.log("No data extracted", "ERROR")
            return False

        print("\n✨ 任务完成")
        self.log(f"Task completed for {target}", "SUCCESS")
        return True

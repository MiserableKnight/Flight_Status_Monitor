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
import json
from datetime import datetime
from abc import ABC, abstractmethod
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.logger import get_logger


class BaseFetcher(ABC):
    """数据抓取基类"""

    # 类级别的浏览器实例管理（共享同一个浏览器连接）
    _shared_browser = None
    _shared_tab_counter = 0
    _tab_registry_file = os.path.join(project_root, 'data', '.tab_registry.json')  # 跨进程共享的注册表文件

    @classmethod
    def _load_tab_registry(cls):
        """从文件加载标签页注册表"""
        if os.path.exists(cls._tab_registry_file):
            try:
                with open(cls._tab_registry_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  加载注册表失败: {e}")
                return {}
        return {}

    @classmethod
    def _save_tab_registry(cls, registry):
        """保存标签页注册表到文件"""
        try:
            os.makedirs(os.path.dirname(cls._tab_registry_file), exist_ok=True)
            with open(cls._tab_registry_file, 'w', encoding='utf-8') as f:
                json.dump(registry, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  保存注册表失败: {e}")

    @classmethod
    def reset_tab_registry(cls):
        """重置标签页注册表（用于测试或重新初始化）"""
        cls._save_tab_registry({})
        cls._shared_browser = None
        cls._shared_tab_counter = 0
        print("✅ 标签页注册表已重置")

    @classmethod
    def cleanup_invalid_registry_entries(cls, current_tab_count):
        """
        清理注册表中的无效条目（索引超出当前标签页数量）

        :param current_tab_count: 当前浏览器的标签页数量
        :return: 清理的条目数量
        """
        tab_registry = cls._load_tab_registry()
        if not tab_registry:
            return 0

        invalid_keys = [
            key for key, index in tab_registry.items()
            if index >= current_tab_count
        ]

        if invalid_keys:
            print(f"🧹 清理 {len(invalid_keys)} 个无效注册条目: {invalid_keys}")
            for key in invalid_keys:
                del tab_registry[key]
            cls._save_tab_registry(tab_registry)
            return len(invalid_keys)

        return 0

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

        # 标签页管理（使用索引）
        self.assigned_tab_index = None  # 分配给此fetcher的标签页索引
        self.assigned_tab_object = None  # 分配给此fetcher的标签页对象（用于操作）
        self.fetcher_name = self.__class__.__name__  # 记录fetcher类型名称

        # 加载配置
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        config = configparser.ConfigParser()
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"❌ 配置文件不存在: {self.config_file}")

        config.read(self.config_file, encoding='utf-8')

        try:
            self.cfg = {
                'username': config.get('credentials', 'username'),
                'password': config.get('credentials', 'password'),
                'user_data_path': config.get('paths', 'user_data_path'),
                'target_url': config.get('target', 'url')
            }
            self.user_data_path = self.cfg['user_data_path']
        except Exception as e:
            raise ValueError(f"配置文件缺失: {e}")

        # 读取飞机号列表
        if config.has_section('aircraft') and config.has_option('aircraft', 'aircraft_list'):
            aircraft_list_str = config.get('aircraft', 'aircraft_list')
            self.aircraft_list = [x.strip() for x in aircraft_list_str.split(',')]
            print(f"✅ 读取到 {len(self.aircraft_list)} 架飞机: {', '.join(self.aircraft_list)}")
        else:
            print("⚠️ 配置文件中未找到飞机号列表,使用默认值")
            self.aircraft_list = ["B-652G", "B-656E"]

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
        连接到浏览器并分配独立标签页

        使用共享浏览器模式：
        - 所有fetcher实例共享同一个浏览器连接
        - 每个fetcher分配一个独立的标签页（使用索引）
        - 避免标签页冲突和互相干扰

        :return: ChromiumPage 对象,失败返回 None
        """
        # 如果已有共享浏览器实例，直接复用
        if BaseFetcher._shared_browser is None:
            co = ChromiumOptions()
            co.set_user_data_path(self.user_data_path)
            co.set_local_port(9222)

            try:
                print(f"\n{'='*60}")
                print(f"🌐 初始化浏览器连接...")
                print(f"{'='*60}")
                BaseFetcher._shared_browser = ChromiumPage(co)
                print(f"✅ 浏览器连接成功! (端口: 9222)")
                self.log("Browser connected successfully", "INFO")
            except Exception as e:
                print(f"❌ 浏览器连接失败: {e}")
                print("请确保Chrome调试模式已启动 (端口9222)")
                self.log(f"Browser connection failed: {e}", "ERROR")
                return None

        # 为当前fetcher分配独立标签页
        page = BaseFetcher._shared_browser

        # 获取当前标签页数量
        tab_count = len(page.browser.get_tabs())

        # 主动清理所有无效的注册表条目（防止浏览器重启后索引失效）
        BaseFetcher.cleanup_invalid_registry_entries(tab_count)

        print(f"\n{'='*60}")
        print(f"📋 标签页分配管理")
        print(f"{'='*60}")
        print(f"📊 当前标签页数量: {tab_count}")
        print(f"🏷️  Fetcher类型: {self.fetcher_name}")
        print(f"📍 当前标签页ID: {page.tab_id}")
        print(f"📋 所有标签页数量: {tab_count}")

        # 从文件加载注册表（跨进程共享）
        tab_registry = self._load_tab_registry()
        print(f"📝 已注册标签页（从文件）: {tab_registry}")

        # 步骤1：检查是否已为此类型分配标签页，并验证有效性
        needs_new_tab = True  # 默认需要分配新标签页

        if self.fetcher_name in tab_registry:
            # 已分配，验证索引是否仍然有效
            self.assigned_tab_index = tab_registry[self.fetcher_name]
            print(f"✅ 复用已分配的标签页索引: {self.assigned_tab_index}")

            # 验证标签页索引是否仍然有效
            if self.assigned_tab_index < len(page.browser.get_tabs()):
                # 索引有效，直接复用
                self.assigned_tab_object = page.get_tab(self.assigned_tab_index)
                if hasattr(self.assigned_tab_object, 'focus'):
                    self.assigned_tab_object.focus()
                print(f"🔄 已切换到标签页索引: {self.assigned_tab_index}")
                needs_new_tab = False  # 不需要创建新标签页
            else:
                # 索引无效（可能是新浏览器会话，标签页数量减少）
                print(f"⚠️  警告: 标签页索引 {self.assigned_tab_index} 超出范围 (当前只有 {len(page.browser.get_tabs())} 个标签页)")
                print(f"🔄 清除无效注册，将创建新标签页...")

                # 从注册表中移除无效条目
                del tab_registry[self.fetcher_name]
                self._save_tab_registry(tab_registry)
                # needs_new_tab 保持为 True，将执行下面的新标签页创建逻辑

        # 步骤2：如果需要，创建新标签页或使用现有标签页
        if needs_new_tab:
            # 检查注册表中是否已有其他 fetcher
            if len(tab_registry) == 0:
                # 注册表为空，这是第一个 fetcher，使用现有标签页（索引0）
                self.assigned_tab_index = 0
                self.assigned_tab_object = page  # 第一个标签页就是主page对象
                tab_registry[self.fetcher_name] = self.assigned_tab_index
                self._save_tab_registry(tab_registry)  # 保存到文件
                print(f"✅ 使用第一个标签页索引: {self.assigned_tab_index}")
            else:
                # 注册表非空，说明已有其他 fetcher，需要创建新标签页
                print(f"🆕 检测到已有 {len(tab_registry)} 个 fetcher，创建新标签页...")
                # 创建新标签页
                new_tab = page.new_tab("about:blank")

                # 等待新标签页创建完成
                time.sleep(0.5)

                # 重新获取标签页列表，获取最新索引
                new_tab_count = len(page.browser.get_tabs())
                self.assigned_tab_index = new_tab_count - 1

                # 获取新标签页对象并保存
                self.assigned_tab_object = page.get_tab(self.assigned_tab_index)

                tab_registry[self.fetcher_name] = self.assigned_tab_index
                self._save_tab_registry(tab_registry)  # 保存到文件

                print(f"✅ 新标签页已创建，索引: {self.assigned_tab_index}")

                # 显式切换到新创建的标签页
                if hasattr(self.assigned_tab_object, 'focus'):
                    self.assigned_tab_object.focus()
                print(f"🔄 已切换到新标签页")

        print(f"{'='*60}\n")

        # 返回分配的标签页对象（而不是主page对象）
        return self.assigned_tab_object

    def ensure_assigned_tab(self, page):
        """
        确保操作在分配的标签页上执行

        :param page: ChromiumPage 对象
        """
        if self.assigned_tab_index is None:
            print(f"⚠️  警告: {self.fetcher_name} 尚未分配标签页")
            return False

        # 通过查找当前标签页在列表中的索引来判断
        # 获取所有标签页的ID列表
        tabs = page.browser.get_tabs()
        tab_ids_list = [tab.tab_id for tab in tabs]
        current_tab_id = page.tab_id
        current_tab_index = tab_ids_list.index(current_tab_id) if current_tab_id in tab_ids_list else -1

        if current_tab_index != self.assigned_tab_index:
            print(f"\n🔄 检测到标签页切换，切换回分配的标签页...")
            print(f"   当前标签页索引: {current_tab_index}")
            print(f"   分配标签页索引: {self.assigned_tab_index}")

            # 切换到分配的标签页
            if self.assigned_tab_index < len(page.browser.get_tabs()):
                target_tab = page.get_tab(self.assigned_tab_index)
                if hasattr(target_tab, 'focus'):
                    target_tab.focus()
                print(f"   ✅ 已切换回 {self.fetcher_name} 的标签页\n")
            else:
                print(f"   ❌ 标签页索引超出范围\n")
                return False

        return True

    def smart_login(self, page):
        """
        智能登录系统 - 自动检测并处理各种页面状态

        核心优化:
        1. 优先确保在分配的标签页上操作
        2. 检查是否已在目标页面（lineLogController/index.html）
        3. 如果已在目标页面，直接返回，不做任何跳转
        4. 只在必要时才执行登录和跳转逻辑

        :param page: ChromiumPage 对象
        :return: 成功返回 True,失败返回 False
        """
        # 标签页隔离检查：确保在分配的标签页上操作
        if not self.ensure_assigned_tab(page):
            print("⚠️  无法切换到分配的标签页")
            return False

        print("\n🔍 检查当前页面状态...")
        current_url = page.url
        print(f"📍 当前URL: {current_url}")

        # ========== 优先级1: 检查是否已在目标页面 ==========
        # 核心优化: 如果已在航段数据页面，直接返回，不做任何跳转
        if "lineLogController/index.html" in current_url:
            print("✅ 已在目标页面: lineLogController/index.html")
            print("💡 跳过登录流程，保持当前状态")
            self.log("Already at target page, skipping login", "INFO")
            return True

        # ========== 优先级2: 检查是否在系统首页 ==========
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
        max_wait = 60
        found_target = False
        login_executed = False

        for i in range(max_wait):
            # 实时检测URL变化
            current_url = page.url

            # 情况1: 已在目标首页
            if "mainController/index.html" in current_url:
                print(f"   ✅ 已在首页!")
                found_target = True
                break

            # 情况2: 在portal登录页 - 需要填充账号密码
            elif "portal" in current_url and "login" in current_url:
                if not login_executed and page.ele('#loginPwd'):
                    print(f"   🔒 检测到portal登录页,开始登录...")
                    try:
                        # 填账号
                        user_ele = page.ele('tag:input@@placeholder=请输入账号')
                        if not user_ele:
                            user_ele = page.ele('tag:input@@type=text')

                        if user_ele:
                            user_ele.clear()
                            user_ele.input(self.cfg['username'])
                            try:
                                page.ele('text:FLYWIN').click(by_js=True)
                            except:
                                pass

                        # 填密码并提交
                        pwd_ele = page.ele('#loginPwd')
                        if pwd_ele:
                            pwd_ele.clear()
                            pwd_ele.input(self.cfg['password'])
                            print(f"   ⚡ 提交登录...")
                            pwd_ele.input('\n')
                            login_executed = True

                    except Exception as e:
                        print(f"   ❌ 登录出错: {e}")

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

        # 备份策略：只备份 data/leg_data.csv 总表，且每天最多备份一次
        needs_backup = (
            subdir == 'data' and  # 只在 data 文件夹下
            filename == 'leg_data.csv' and  # 只备份总表
            os.path.exists(filepath)  # 文件已存在
        )

        if needs_backup:
            backup_dir = os.path.join(project_root, 'data', 'backup')
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)

            # 检查今天是否已备份
            today = datetime.now().strftime("%Y%m%d")
            name, ext = os.path.splitext(filename)
            today_backup = f"{name}_{today}{ext}"
            today_backup_path = os.path.join(backup_dir, today_backup)

            if not os.path.exists(today_backup_path):
                # 今天还没备份，执行备份
                try:
                    shutil.copy2(filepath, today_backup_path)
                    print(f"   💾 已备份总表: {today_backup_path}")
                except Exception as e:
                    print(f"   ⚠️ 备份失败: {e}")
            # 如果今天的备份已存在，跳过备份

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

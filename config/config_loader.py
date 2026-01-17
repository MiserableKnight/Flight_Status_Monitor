"""
统一配置加载模块
提供系统各模块的配置加载接口

敏感配置说明：
- 敏感配置（登录凭证、Gmail密码等）优先从环境变量读取
- 环境变量未配置时，fallback 到 config.ini（但不推荐）
- 参考 .env.template 文件了解需要配置哪些环境变量
"""

import configparser
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConfigLoader:
    """配置加载器类（支持环境变量优先）"""

    # 环境变量映射
    ENV_MAPPING = {
        "username": "SYSTEM_USERNAME",
        "password": "SYSTEM_PASSWORD",
        "sender_email": "GMAIL_SENDER_EMAIL",
        "app_password": "GMAIL_APP_PASSWORD",
        "recipients": "GMAIL_RECIPIENTS",
        "sender_name": "GMAIL_SENDER_NAME",
    }

    def __init__(self, config_file: str = None):
        """
        初始化配置加载器

        Args:
            config_file: 配置文件路径，默认为 config/config.ini
        """
        if config_file is None:
            # 默认配置文件路径
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_file = os.path.join(project_root, "config", "config.ini")

        self.config_file = config_file

        # 先加载 .env 文件到环境变量
        self._load_env()

        # 再加载 config.ini
        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_env(self):
        """从项目根目录加载 .env 文件到环境变量"""
        project_root = Path(__file__).parent.parent
        env_file = project_root / ".env"

        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # 跳过注释和空行
                    if not line or line.startswith("#"):
                        continue
                    # 解析 KEY=VALUE 格式
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()

    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding="utf-8")
        # 配置文件不存在时不报错，依赖环境变量

    def _get_value(self, section: str, key: str, fallback: Any = None) -> Optional[str]:
        """
        获取配置值（优先从环境变量读取）

        优先级: 环境变量 > config.ini > fallback

        Args:
            section: 配置节名
            key: 配置键名
            fallback: 默认值

        Returns:
            配置值
        """
        # 检查是否有对应的环境变量
        composite_key = f"{section}.{key}"
        if composite_key in self.ENV_MAPPING:
            env_value = os.environ.get(self.ENV_MAPPING[composite_key])
            if env_value:
                return env_value

        # 尝试从 config.ini 读取
        if self.config.has_section(section) and self.config.has_option(section, key):
            return self.config.get(section, key)

        return fallback

    def get_credentials(self) -> Dict[str, str]:
        """
        获取登录凭证（优先从环境变量读取）

        Returns:
            Dict[str, str]: {'username': 'xxx', 'password': 'xxx'}
        """
        username = os.environ.get("SYSTEM_USERNAME") or ""
        password = os.environ.get("SYSTEM_PASSWORD") or ""

        if not username:
            print("⚠️  警告: SYSTEM_USERNAME 环境变量未配置")
        if not password:
            print("⚠️  警告: SYSTEM_PASSWORD 环境变量未配置")

        return {"username": username, "password": password}

    def get_paths(self) -> Dict[str, str]:
        """
        获取路径配置

        Returns:
            Dict[str, str]: {'user_data_path': 'xxx'}
        """
        user_data_path = self._get_value("paths", "user_data_path", "")
        return {"user_data_path": user_data_path}

    def get_target_url(self) -> str:
        """
        获取系统首页URL

        Returns:
            str: 首页URL
        """
        return self._get_value("target", "url", "")

    def get_aircraft_list(self) -> List[str]:
        """
        获取飞机号列表

        Returns:
            List[str]: 飞机号列表
        """
        if self.config.has_section("aircraft") and self.config.has_option(
            "aircraft", "aircraft_list"
        ):
            aircraft_list_str = self.config.get("aircraft", "aircraft_list")
            return [x.strip() for x in aircraft_list_str.split(",")]
        return []

    def get_urls(self) -> Dict[str, str]:
        """
        获取URL配置

        Returns:
            Dict[str, str]: URL配置字典
        """
        if self.config.has_section("urls"):
            return dict(self.config.items("urls"))
        return {}

    def get_scheduler_config(self) -> Dict[str, Any]:
        """
        获取调度器配置

        Returns:
            Dict[str, Any]: 调度器配置字典
        """
        if not self.config.has_section("scheduler"):
            return self._get_default_scheduler_config()

        config = {}
        section = self.config["scheduler"]

        # 时间配置
        config["start_time"] = section.get("start_time", "06:30")
        config["end_time"] = section.get("end_time", "21:00")

        # 抓取时间列表
        flight_times = section.get("flight_fetch_times", "07:00, 12:00, 18:00")
        config["flight_fetch_times"] = [t.strip() for t in flight_times.split(",")]

        faults_times = section.get("faults_fetch_times", "08:00, 14:00, 20:00")
        config["faults_fetch_times"] = [t.strip() for t in faults_times.split(",")]

        return config

    def _get_default_scheduler_config(self) -> Dict[str, Any]:
        """获取默认调度器配置"""
        return {
            "start_time": "06:30",
            "end_time": "21:00",
            "flight_fetch_times": ["07:00", "12:00", "18:00"],
            "faults_fetch_times": ["08:00", "14:00", "20:00"],
        }

    def get_gmail_config(self) -> Dict[str, str]:
        """
        获取Gmail配置（优先从环境变量读取）

        Returns:
            Dict[str, str]: Gmail配置字典，包含:
                - sender_email: 发件人邮箱
                - app_password: Gmail应用专用密码
                - recipients: 收件人列表
                - sender_name: 发件人显示名称
        """
        sender_email = os.environ.get("GMAIL_SENDER_EMAIL") or ""
        app_password = os.environ.get("GMAIL_APP_PASSWORD") or ""
        sender_name = os.environ.get("GMAIL_SENDER_NAME") or "航班监控系统"
        recipients_str = os.environ.get("GMAIL_RECIPIENTS") or ""

        recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]

        if not sender_email:
            print("⚠️  警告: GMAIL_SENDER_EMAIL 环境变量未配置")
        if not app_password:
            print("⚠️  警告: GMAIL_APP_PASSWORD 环境变量未配置")
        if not recipients:
            print("⚠️  警告: GMAIL_RECIPIENTS 环境变量未配置")

        return {
            "sender_email": sender_email,
            "app_password": app_password,
            "sender_name": sender_name,
            "recipients": recipients,
        }

    def get_all_config(self) -> Dict[str, Any]:
        """
        获取所有配置

        Returns:
            Dict[str, Any]: 包含所有配置的字典
        """
        return {
            "credentials": self.get_credentials(),
            "paths": self.get_paths(),
            "target_url": self.get_target_url(),
            "aircraft_list": self.get_aircraft_list(),
            "urls": self.get_urls(),
            "scheduler": self.get_scheduler_config(),
            "gmail": self.get_gmail_config(),
        }


# 全局实例（延迟加载）
_config_loader_instance = None


def load_config() -> ConfigLoader:
    """
    获取配置加载器实例（单例模式）

    Returns:
        ConfigLoader: 配置加载器实例
    """
    global _config_loader_instance
    if _config_loader_instance is None:
        _config_loader_instance = ConfigLoader()
    return _config_loader_instance


# 向后兼容的便捷函数
def get_aircraft_mapping():
    """快捷方法：获取飞机号映射"""
    from .aircraft_cfg import get_aircraft_mapping as _get_aircraft_mapping

    return _get_aircraft_mapping()


if __name__ == "__main__":
    # 测试代码
    print("🧪 配置加载器测试")
    print("=" * 60)

    loader = load_config()

    print("\n🔑 登录凭证:")
    creds = loader.get_credentials()
    print(f"  用户名: {creds['username']}")
    print(f"  密码: {'*' * len(creds['password']) if creds['password'] else '未配置'}")

    print("\n📁 路径配置:")
    paths = loader.get_paths()
    for key, value in paths.items():
        print(f"  {key}: {value}")

    print("\n🎯 目标URL:")
    print(f"  {loader.get_target_url()}")

    print("\n✈️ 飞机号列表:")
    aircraft_list = loader.get_aircraft_list()
    for aircraft in aircraft_list:
        print(f"  - {aircraft}")

    print("\n🔗 URL配置:")
    urls = loader.get_urls()
    for key, value in urls.items():
        print(f"  {key}: {value}")

    print("\n⏰ 调度器配置:")
    scheduler = loader.get_scheduler_config()
    print(f"  启动时间: {scheduler['start_time']}")
    print(f"  结束时间: {scheduler['end_time']}")
    print(f"  航班数据抓取时间: {', '.join(scheduler['flight_fetch_times'])}")
    print(f"  故障数据抓取时间: {', '.join(scheduler['faults_fetch_times'])}")

    print("\n📧 Gmail配置:")
    gmail = loader.get_gmail_config()
    print(f"  发件人邮箱: {gmail['sender_email']}")
    print(f"  应用密码: {'已配置' if gmail['app_password'] else '未配置'}")
    print(f"  收件人: {', '.join(gmail['recipients']) if gmail['recipients'] else '未配置'}")
    print(f"  发件人名称: {gmail['sender_name']}")

    print("\n✅ 测试完成")

"""
飞机号映射配置模块
提供飞机号映射逻辑和配置管理
"""

import configparser
import os
from typing import Dict, List


class AircraftConfig:
    """飞机号配置管理类"""

    def __init__(self, config_file: str = None):
        """
        初始化飞机号配置

        Args:
            config_file: 配置文件路径，默认为 config/config.ini
        """
        if config_file is None:
            # 默认配置文件路径
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_file = os.path.join(project_root, "config", "config.ini")

        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"❌ 配置文件不存在: {self.config_file}")

        self.config.read(self.config_file, encoding="utf-8")

    def get_aircraft_list(self) -> List[str]:
        """
        获取配置的飞机号列表

        Returns:
            List[str]: 飞机号列表，例如 ['B-652G', 'B-656E']
        """
        if self.config.has_section("aircraft") and self.config.has_option(
            "aircraft", "aircraft_list"
        ):
            aircraft_list_str = self.config.get("aircraft", "aircraft_list")
            aircraft_list = [x.strip() for x in aircraft_list_str.split(",")]
            return aircraft_list
        else:
            # 默认值
            return ["B-652G", "B-656E"]

    def get_aircraft_mapping(self) -> Dict[str, str]:
        """
        获取飞机号映射字典

        将短飞机号映射为完整显示名称（B-652G -> C909-185/B-652G）

        Returns:
            Dict[str, str]: 映射字典，例如 {'B-652G': 'C909-185/B-652G'}
        """
        aircraft_list = self.get_aircraft_list()
        mapping = {}

        # 默认映射规则
        # 如果飞机号本身不包含"C909-"，则添加前缀
        for aircraft in aircraft_list:
            if "C909-" in aircraft:
                # 已经是完整格式
                mapping[aircraft] = aircraft
                # 同时提取短飞机号作为键
                short_name = aircraft.split("/")[-1] if "/" in aircraft else aircraft
                mapping[short_name] = aircraft
            else:
                # 需要添加前缀（从飞机号提取编号）
                # B-652G -> C909-185/B-652G
                # B-656E -> C909-196/B-656E
                # 这里使用预定义的映射
                predefined_mappings = {"B-652G": "C909-185/B-652G", "B-656E": "C909-196/B-656E"}

                if aircraft in predefined_mappings:
                    mapping[aircraft] = predefined_mappings[aircraft]
                else:
                    # 如果没有预定义映射，使用飞机号本身
                    mapping[aircraft] = aircraft

        return mapping

    def get_full_aircraft_name(self, short_name: str) -> str:
        """
        获取飞机号的完整显示名称

        Args:
            short_name: 短飞机号，例如 'B-652G'

        Returns:
            str: 完整名称，例如 'C909-185/B-652G'
        """
        mapping = self.get_aircraft_mapping()
        return mapping.get(short_name, short_name)

    def get_all_short_names(self) -> List[str]:
        """
        获取所有短飞机号

        Returns:
            List[str]: 短飞机号列表
        """
        mapping = self.get_aircraft_mapping()
        return list(mapping.keys())


# 全局实例（延迟加载）
_aircraft_config_instance = None


def get_aircraft_config() -> AircraftConfig:
    """
    获取飞机号配置实例（单例模式）

    Returns:
        AircraftConfig: 配置实例
    """
    global _aircraft_config_instance
    if _aircraft_config_instance is None:
        _aircraft_config_instance = AircraftConfig()
    return _aircraft_config_instance


def get_aircraft_mapping() -> Dict[str, str]:
    """
    快捷方法：获取飞机号映射字典

    Returns:
        Dict[str, str]: 映射字典
    """
    return get_aircraft_config().get_aircraft_mapping()


if __name__ == "__main__":
    # 测试代码
    print("🧪 飞机号配置测试")
    print("=" * 60)

    cfg = get_aircraft_config()

    print("\n📋 飞机号列表:")
    aircraft_list = cfg.get_aircraft_list()
    for aircraft in aircraft_list:
        print(f"  - {aircraft}")

    print("\n🔗 飞机号映射:")
    mapping = cfg.get_aircraft_mapping()
    for short, full in mapping.items():
        print(f"  {short} -> {full}")

    print("\n✅ 测试完成")

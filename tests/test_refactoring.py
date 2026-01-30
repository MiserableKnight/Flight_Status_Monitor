"""
重构验证测试

验证 BaseFetcher 重构后的功能是否正常
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_base_fetcher_composition():
    """测试 BaseFetcher 的组件组合"""
    from fetchers.base_fetcher import BaseFetcher

    # 创建一个简单的测试类
    class TestFetcher(BaseFetcher):
        def get_data_prefix(self):
            return "test"

        def navigate_to_target_page(self, page, target_date):
            return []

    fetcher = TestFetcher()

    # 验证组件已正确初始化
    assert hasattr(fetcher, "login_manager"), "❌ 缺少 login_manager"
    assert hasattr(fetcher, "data_saver"), "❌ 缺少 data_saver"

    # 验证组件类型
    from core.data_saver import DataSaver
    from core.login_manager import LoginManager

    assert isinstance(fetcher.login_manager, LoginManager), "❌ login_manager 类型错误"
    assert isinstance(fetcher.data_saver, DataSaver), "❌ data_saver 类型错误"

    print("✅ BaseFetcher 组件组合测试通过")


def test_login_manager():
    """测试 LoginManager 可以正常实例化"""
    from core.login_manager import LoginManager

    credentials = {"username": "test", "password": "test"}

    def mock_logger(msg, level):
        pass

    login_mgr = LoginManager(credentials, mock_logger)

    # 验证方法存在
    assert hasattr(login_mgr, "login"), "❌ 缺少 login 方法"
    assert callable(login_mgr.login), "❌ login 不是可调用方法"

    print("✅ LoginManager 测试通过")


def test_data_saver():
    """测试 DataSaver 可以正常实例化"""
    from core.data_saver import DataSaver

    def mock_logger(msg, level):
        pass

    data_saver = DataSaver(project_root, mock_logger)

    # 验证方法存在
    assert hasattr(data_saver, "save_csv"), "❌ 缺少 save_csv 方法"
    assert hasattr(data_saver, "_cleanup_old_backups"), "❌ 缺少 _cleanup_old_backups 方法"

    print("✅ DataSaver 测试通过")


def test_constants():
    """测试 constants.py 是否正确导出"""
    from config.constants import (
        DEFAULT_BACKUP_KEEP_COUNT,
        DEFAULT_BROWSER_PORT,
        LOGIN_CHECK_INTERVAL,
        MAX_LOGIN_WAIT_SECONDS,
    )

    assert DEFAULT_BROWSER_PORT == 9222, "❌ DEFAULT_BROWSER_PORT 值错误"
    assert MAX_LOGIN_WAIT_SECONDS == 90, "❌ MAX_LOGIN_WAIT_SECONDS 值错误"
    assert LOGIN_CHECK_INTERVAL == 0.5, "❌ LOGIN_CHECK_INTERVAL 值错误"
    assert DEFAULT_BACKUP_KEEP_COUNT == 2, "❌ DEFAULT_BACKUP_KEEP_COUNT 值错误"

    print("✅ Constants 测试通过")


def test_backwards_compatibility():
    """测试向后兼容性 - 子类无需修改"""
    from fetchers.fault_fetcher import FaultFetcher
    from fetchers.leg_fetcher import LegFetcher

    # 验证子类仍然可以正常实例化
    leg_fetcher = LegFetcher()
    fault_fetcher = FaultFetcher()

    # 验证子类继承了组件
    assert hasattr(leg_fetcher, "login_manager"), "❌ LegFetcher 缺少 login_manager"
    assert hasattr(leg_fetcher, "data_saver"), "❌ LegFetcher 缺少 data_saver"
    assert hasattr(fault_fetcher, "login_manager"), "❌ FaultFetcher 缺少 login_manager"
    assert hasattr(fault_fetcher, "data_saver"), "❌ FaultFetcher 缺少 data_saver"

    print("✅ 向后兼容性测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 重构验证测试")
    print("=" * 60)
    print()

    try:
        test_base_fetcher_composition()
        test_login_manager()
        test_data_saver()
        test_constants()
        test_backwards_compatibility()

        print()
        print("=" * 60)
        print("🎉 所有测试通过！重构成功！")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

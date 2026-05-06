"""
测试 BaseFetcher 整页刷新机制

覆盖 should_force_refresh() 和 mark_full_refresh() 的逻辑
"""

import os
import sys
import time
from unittest.mock import patch

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from fetchers.base_fetcher import BaseFetcher


class _DummyFetcher(BaseFetcher):
    """用于测试的具体子类"""

    def get_data_prefix(self):
        return "test"

    def navigate_to_target_page(self, page, target_date, aircraft_list=None):
        return None


@pytest.fixture
def fetcher():
    """创建测试用 fetcher 实例（跳过配置加载）"""
    with patch.object(BaseFetcher, "__init__", lambda self, **kwargs: None):
        inst = _DummyFetcher.__new__(_DummyFetcher)
        inst._initialized = False
        inst._initialized_date = None
        inst._last_full_refresh = 0
        # 提供 mock log（should_force_refresh 中有 self.log 调用）
        inst.log = lambda msg, level="INFO": None
        return inst


class TestShouldForceRefresh:
    """测试 should_force_refresh() 方法"""

    def test_uninitialized_returns_needs_init(self, fetcher):
        """未初始化时应返回 needs_init=True"""
        fetcher._initialized = False
        needs_init, minutes_left = fetcher.should_force_refresh()
        assert needs_init is True
        assert minutes_left is None

    def test_recently_initialized_no_refresh_needed(self, fetcher):
        """刚初始化不久，不需要刷新"""
        fetcher._initialized = True
        fetcher._last_full_refresh = time.time()  # 刚刚刷新过

        needs_init, minutes_left = fetcher.should_force_refresh()
        assert needs_init is False
        assert minutes_left is not None
        assert minutes_left >= 59  # 应该接近60分钟

    def test_expired_initialization_forces_refresh(self, fetcher):
        """超过刷新间隔后强制重新初始化"""
        fetcher._initialized = True
        fetcher._last_full_refresh = time.time() - 7200  # 2小时前

        needs_init, minutes_left = fetcher.should_force_refresh()
        assert needs_init is True
        assert minutes_left is None
        assert fetcher._initialized is False  # 应被重置

    def test_exactly_at_boundary(self, fetcher):
        """恰好到达刷新间隔边界"""
        fetcher._initialized = True
        # 恰好 3600 秒前（等于阈值，不算超过）
        fetcher._last_full_refresh = time.time() - 3600

        needs_init, minutes_left = fetcher.should_force_refresh()
        assert needs_init is False

    def test_one_second_past_boundary(self, fetcher):
        """超过边界1秒就触发刷新"""
        fetcher._initialized = True
        fetcher._last_full_refresh = time.time() - 3601

        needs_init, minutes_left = fetcher.should_force_refresh()
        assert needs_init is True
        assert fetcher._initialized is False

    def test_minutes_left_decreases_over_time(self, fetcher):
        """minutes_left 随时间推移减少"""
        fetcher._initialized = True
        fetcher._last_full_refresh = time.time() - 1800  # 30分钟前

        _, minutes_left = fetcher.should_force_refresh()
        assert 29 <= minutes_left <= 30  # 约30分钟剩余


class TestMarkFullRefresh:
    """测试 mark_full_refresh() 方法"""

    def test_updates_timestamp(self, fetcher):
        """调用后 _last_full_refresh 应更新为当前时间"""
        before = time.time()
        fetcher.mark_full_refresh()
        after = time.time()

        assert before <= fetcher._last_full_refresh <= after

    def test_refresh_resets_expiration(self, fetcher):
        """刷新后 should_force_refresh 不再要求重新初始化"""
        fetcher._initialized = True
        fetcher._last_full_refresh = time.time() - 7200  # 已过期

        # 确认已过期
        needs_init, _ = fetcher.should_force_refresh()
        assert needs_init is True

        # 重置状态（模拟重新初始化完成）
        fetcher._initialized = True
        fetcher.mark_full_refresh()

        # 现在不应需要刷新
        needs_init, _ = fetcher.should_force_refresh()
        assert needs_init is False

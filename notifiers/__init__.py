# -*- coding: utf-8 -*-
"""
业务通知器模块

包含所有业务相关的邮件通知器：
- TaskNotifier: 任务通知器（数据抓取任务）
- LegStatusNotifier: 航段状态通知器
- FaultStatusNotifier: 故障状态通知器

所有通知器继承自 core.base_notifier.BaseNotifier
"""

from .task_notifier import TaskNotifier
from .leg_status_notifier import LegStatusNotifier
from .fault_status_notifier import FaultStatusNotifier

__all__ = ['TaskNotifier', 'LegStatusNotifier', 'FaultStatusNotifier']

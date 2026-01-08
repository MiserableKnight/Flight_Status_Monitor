# -*- coding: utf-8 -*-
"""
配置管理模块
提供统一的配置加载接口
"""
from .config_loader import load_config, get_aircraft_mapping

__all__ = ['load_config', 'get_aircraft_mapping']

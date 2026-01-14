# -*- coding: utf-8 -*-
"""
故障过滤模块

功能：
- 基于配置规则过滤故障数据
- 支持组合过滤规则（多字段AND关系）
- 支持关联故障过滤规则（同一时间的多个故障组合）
"""

import pandas as pd
from typing import List, Set
import os
from core.logger import get_logger

log = get_logger()


class FaultFilter:
    """故障过滤器"""

    def __init__(self, config_dir: str = None):
        """
        初始化故障过滤器

        Args:
            config_dir: 配置文件目录路径
        """
        if config_dir is None:
            # 默认使用项目config目录
            # __file__ 位于 core/fault_filter.py，需要向上两级到项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_dir = os.path.join(project_root, 'config')

        self.config_dir = config_dir
        self.single_rules = self._load_single_filter_rules()
        self.group_rules = self._load_group_filter_rules()

    def _load_single_filter_rules(self) -> pd.DataFrame:
        """加载组合过滤规则"""
        path = os.path.join(self.config_dir, 'fault_filter_rules.csv')
        if not os.path.exists(path):
            log(f"组合过滤规则文件不存在: {path}", "WARNING")
            return pd.DataFrame()

        try:
            df = pd.read_csv(path, encoding='utf-8-sig')
            log(f"加载组合过滤规则: {len(df)} 条", "INFO")
            return df
        except Exception as e:
            log(f"加载组合过滤规则失败: {e}", "ERROR")
            return pd.DataFrame()

    def _load_group_filter_rules(self) -> pd.DataFrame:
        """加载关联故障过滤规则"""
        path = os.path.join(self.config_dir, 'fault_group_filter_rules.csv')
        if not os.path.exists(path):
            log(f"关联故障过滤规则文件不存在: {path}", "WARNING")
            return pd.DataFrame()

        try:
            df = pd.read_csv(path, encoding='utf-8-sig')
            log(f"加载关联故障过滤规则: {len(df)} 条", "INFO")
            return df
        except Exception as e:
            log(f"加载关联故障过滤规则失败: {e}", "ERROR")
            return pd.DataFrame()

    def apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用所有过滤规则

        Args:
            df: 故障数据DataFrame

        Returns:
            pd.DataFrame: 过滤后的故障数据
        """
        if df.empty:
            return df

        original_count = len(df)

        # 应用组合过滤规则
        df = self._apply_single_filters(df)

        # 应用关联故障过滤规则
        df = self._apply_group_filters(df)

        filtered_count = len(df)
        if original_count > filtered_count:
            log(f"过滤完成: {original_count} 条 → {filtered_count} 条 (过滤掉 {original_count - filtered_count} 条)", "INFO")

        return df

    def _apply_single_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用组合过滤规则（单行多字段AND关系）

        规则说明：
        - 配置文件中同一行的多个非空字段为AND关系
        - 使用 str.contains() 进行模糊匹配
        - 多行规则之间为OR关系（满足任一行即过滤）
        """
        if self.single_rules.empty:
            return df

        # 记录需要过滤的索引
        indices_to_filter = set()

        # 遍历每条过滤规则
        for idx, rule in self.single_rules.iterrows():
            # 获取规则中所有非空字段
            rule_conditions = []
            for col in df.columns:
                if col in rule.index and pd.notna(rule[col]) and str(rule[col]).strip() != '':
                    rule_value = str(rule[col]).strip()
                    rule_conditions.append((col, rule_value))

            if not rule_conditions:
                continue

            # 应用AND逻辑：检查所有条件是否都满足
            mask = pd.Series([True] * len(df), index=df.index)

            for col, rule_value in rule_conditions:
                # 使用 str.contains() 进行模糊匹配
                col_mask = df[col].astype(str).str.contains(rule_value, na=False)
                mask = mask & col_mask

            # 将满足该规则的行添加到过滤集合
            matched_indices = df[mask].index.tolist()
            indices_to_filter.update(matched_indices)

            if matched_indices:
                log(f"组合规则 {idx} 匹配 {len(matched_indices)} 条: {rule_conditions}", "DEBUG")

        # 返回未匹配的行
        if indices_to_filter:
            result = df.drop(indices_to_filter)
            log(f"组合过滤: 过滤掉 {len(indices_to_filter)} 条故障", "INFO")
            return result
        else:
            return df

    def _apply_group_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用关联故障过滤规则

        规则说明：
        - 针对同一架飞机、同一时间（HH:MM相同）
        - 同时出现配置文件中定义的多个特定故障描述
        - 使用 str.contains() 进行模糊匹配
        - 如果所有配置的故障都在同一时间内出现，则将这些故障全部过滤
        """
        if self.group_rules.empty:
            return df

        # 记录需要过滤的索引
        indices_to_filter = set()

        # 添加时间键（机号 + HH:MM）
        df = df.copy()
        df['_time_key'] = df['机号'] + '_' + df['触发时间'].str[:5]  # 取前5个字符 "HH:MM"

        # 按时间键分组
        for time_key, group in df.groupby('_time_key'):
            # 检查该时间组是否匹配任一关联故障规则
            for rule_idx, rule in self.group_rules.iterrows():
                # 获取规则中定义的所有故障描述（非空）
                fault_descriptions = []
                for col in rule.index:
                    if col.startswith('故障描述') and pd.notna(rule[col]) and str(rule[col]).strip() != '':
                        fault_descriptions.append(str(rule[col]).strip())

                if len(fault_descriptions) < 2:
                    continue  # 至少需要2个故障描述才构成关联规则

                # 检查该时间组是否包含所有配置的故障描述
                group_descriptions = group['描述'].tolist()

                # 检查每个规则中的故障描述是否在组内出现
                all_matched = True
                for rule_desc in fault_descriptions:
                    # 使用 str.contains() 检查是否有故障描述包含规则描述
                    found = any(rule_desc in fault_desc for fault_desc in group_descriptions)
                    if not found:
                        all_matched = False
                        break

                if all_matched:
                    # 所有故障都在同一时间出现，标记该组所有故障为过滤
                    matched_indices = group.index.tolist()
                    indices_to_filter.update(matched_indices)
                    log(f"关联规则 {rule_idx} 匹配时间组 {time_key}: {fault_descriptions}, 过滤 {len(matched_indices)} 条", "DEBUG")

        # 清除临时列
        df = df.drop(columns=['_time_key'])

        # 返回未匹配的行
        if indices_to_filter:
            result = df.drop(indices_to_filter)
            log(f"关联故障过滤: 过滤掉 {len(indices_to_filter)} 条故障", "INFO")
            return result
        else:
            return df

    def get_filter_stats(self) -> dict:
        """
        获取过滤规则统计信息

        Returns:
            dict: 包含规则数量的字典
        """
        return {
            'single_filter_rules': len(self.single_rules),
            'group_filter_rules': len(self.group_rules)
        }

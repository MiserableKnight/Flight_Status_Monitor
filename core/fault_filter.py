"""
故障过滤模块

功能：
- 基于配置规则过滤故障数据
- 支持组合过滤规则（多字段AND关系）
- 支持关联故障过滤规则（同一时间的多个故障组合）
"""

import os
from datetime import datetime

import pandas as pd

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
            config_dir = os.path.join(project_root, "config")

        self.config_dir = config_dir
        self.single_rules = self._load_single_filter_rules()
        self.group_rules = self._load_group_filter_rules()

    def _load_single_filter_rules(self) -> pd.DataFrame:
        """加载组合过滤规则"""
        path = os.path.join(self.config_dir, "fault_filter_rules.csv")
        if not os.path.exists(path):
            log(f"组合过滤规则文件不存在: {path}", "WARNING")
            return pd.DataFrame()

        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
            log(f"加载组合过滤规则: {len(df)} 条", "INFO")
            return df
        except Exception as e:
            log(f"加载组合过滤规则失败: {e}", "ERROR")
            return pd.DataFrame()

    def _load_group_filter_rules(self) -> pd.DataFrame:
        """加载关联故障过滤规则"""
        path = os.path.join(self.config_dir, "fault_group_filter_rules.csv")
        if not os.path.exists(path):
            log(f"关联故障过滤规则文件不存在: {path}", "WARNING")
            return pd.DataFrame()

        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
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
            log(
                f"过滤完成: {original_count} 条 → {filtered_count} 条 (过滤掉 {original_count - filtered_count} 条)",
                "INFO",
            )

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
                if col in rule.index and pd.notna(rule[col]) and str(rule[col]).strip() != "":
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
        - 针对同一架飞机
        - 同时出现配置文件中定义的多个特定故障描述
        - 使用 str.contains() 进行模糊匹配
        - 如果所有配置的故障都在设定的时间间隔内出现，则将这些故障全部过滤
        - 时间间隔由规则中的"时间间隔(秒)"字段指定
        """
        if self.group_rules.empty:
            return df

        # 记录需要过滤的索引
        indices_to_filter = set()

        df = df.copy()

        # 按机号分组
        for aircraft, group in df.groupby("机号"):
            # 检查该机号的故障是否匹配任一关联故障规则
            for rule_idx, rule in self.group_rules.iterrows():
                # 获取规则中定义的所有故障描述（非空）
                fault_descriptions = []
                for col in rule.index:
                    if (
                        col.startswith("故障描述")
                        and pd.notna(rule[col])
                        and str(rule[col]).strip() != ""
                    ):
                        fault_descriptions.append(str(rule[col]).strip())

                if len(fault_descriptions) < 2:
                    continue  # 至少需要2个故障描述才构成关联规则

                # 获取时间间隔阈值（秒）
                time_threshold = 0
                if "时间间隔(秒)" in rule.index and pd.notna(rule["时间间隔(秒)"]):
                    try:
                        time_threshold = int(rule["时间间隔(秒)"])
                    except (ValueError, TypeError):
                        time_threshold = 0

                # 检查该机号的故障组是否包含所有配置的故障描述
                matched_faults = {}  # 故障描述 -> [匹配的行索引列表]

                # 遍历组内的每一条故障记录
                for idx, row in group.iterrows():
                    fault_desc = str(row["描述"])

                    # 检查该故障是否匹配规则中的任一故障描述
                    for rule_desc in fault_descriptions:
                        if rule_desc in fault_desc:
                            if rule_desc not in matched_faults:
                                matched_faults[rule_desc] = []
                            matched_faults[rule_desc].append(idx)
                            break

                # 检查是否所有规则的故障描述都找到了匹配
                if len(matched_faults) == len(fault_descriptions):
                    # 所有故障都出现了，现在检查时间间隔
                    # 收集所有匹配故障的触发时间
                    all_matched_indices = []
                    for indices in matched_faults.values():
                        all_matched_indices.extend(indices)

                    # 去重（可能同一行匹配多个规则描述）
                    all_matched_indices = list(set(all_matched_indices))

                    # 获取所有匹配故障的触发时间
                    trigger_times = df.loc[all_matched_indices, "触发时间"].tolist()

                    # 解析时间并计算时间范围
                    try:
                        # 解析时间字符串 (假设格式为 "YYYY-MM-DD HH:MM:SS" 或 "HH:MM:SS")
                        parsed_times = []
                        for t in trigger_times:
                            # 尝试解析完整的时间戳
                            if " " in str(t):
                                parsed_times.append(datetime.strptime(str(t), "%Y-%m-%d %H:%M:%S"))
                            else:
                                # 如果只有时间部分，使用今天日期
                                time_part = str(t).split(".")[0]  # 去掉可能的毫秒部分
                                parsed_times.append(datetime.strptime(time_part, "%H:%M:%S"))

                        # 计算时间差（秒）
                        if len(parsed_times) > 1:
                            time_span = (max(parsed_times) - min(parsed_times)).total_seconds()

                            # 如果时间差小于阈值，则过滤这些故障
                            if time_span <= time_threshold:
                                indices_to_filter.update(all_matched_indices)
                                log(
                                    f"关联规则 {rule_idx} 匹配机号 {aircraft}: {fault_descriptions}, "
                                    f"时间跨度 {time_span:.1f}秒 <= {time_threshold}秒, 过滤 {len(all_matched_indices)} 条",
                                    "DEBUG",
                                )
                            else:
                                log(
                                    f"关联规则 {rule_idx} 匹配机号 {aircraft}: {fault_descriptions}, "
                                    f"时间跨度 {time_span:.1f}秒 > {time_threshold}秒, 不予过滤",
                                    "DEBUG",
                                )
                        else:
                            # 只有一个时间点，直接过滤
                            indices_to_filter.update(all_matched_indices)
                            log(
                                f"关联规则 {rule_idx} 匹配机号 {aircraft}: {fault_descriptions}, "
                                f"单点时间, 过滤 {len(all_matched_indices)} 条",
                                "DEBUG",
                            )
                    except Exception as e:
                        log(f"解析时间失败: {e}, 跳过该规则", "WARNING")

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
            "single_filter_rules": len(self.single_rules),
            "group_filter_rules": len(self.group_rules),
        }

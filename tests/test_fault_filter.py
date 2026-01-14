# -*- coding: utf-8 -*-
"""
故障过滤功能测试脚本

测试故障过滤器的功能
"""
import pandas as pd
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.fault_filter import FaultFilter
from core.logger import get_logger

log = get_logger()


def test_filter_with_today_data():
    """使用今日数据测试过滤器"""
    print("=" * 80)
    print("故障过滤功能测试")
    print("=" * 80)

    # 获取今天的日期
    target_date = datetime.now().strftime('%Y-%m-%d')
    print(f"\n📅 测试日期: {target_date}")

    # 读取今日故障数据
    data_file = os.path.join(project_root, 'data', 'daily_raw', f'fault_data_{target_date}.csv')

    if not os.path.exists(data_file):
        print(f"\n❌ 数据文件不存在: {data_file}")
        return False

    try:
        # 读取CSV文件
        df = pd.read_csv(data_file, encoding='utf-8-sig')

        # 重命名可能的列名变体
        if '触发_time' in df.columns and '触发时间' not in df.columns:
            df.rename(columns={'触发_time': '触发时间'}, inplace=True)

        print(f"\n📊 原始数据: {len(df)} 行")
        print("\n原始故障列表:")
        print("-" * 80)
        for idx, row in df.iterrows():
            print(f"{idx+1}. [{row['机号']}] {row['航班号']} - {row['触发时间']} - {row['描述']} - 阶段:{row['飞行阶段']}")

    except Exception as e:
        print(f"\n❌ 读取数据失败: {e}")
        return False

    # 创建过滤器
    print(f"\n🔧 创建故障过滤器...")
    filter_obj = FaultFilter()

    # 获取过滤规则统计
    stats = filter_obj.get_filter_stats()
    print(f"   📋 组合过滤规则: {stats['single_filter_rules']} 条")
    print(f"   📋 关联故障过滤规则: {stats['group_filter_rules']} 条")

    # 显示过滤规则
    if not filter_obj.single_rules.empty:
        print(f"\n📝 组合过滤规则详情:")
        for idx, rule in filter_obj.single_rules.iterrows():
            conditions = []
            for col in df.columns:
                if col in rule.index and pd.notna(rule[col]) and str(rule[col]).strip() != '':
                    conditions.append(f"{col}={rule[col]}")
            if conditions:
                print(f"   规则 {idx+1}: {' AND '.join(conditions)}")

    if not filter_obj.group_rules.empty:
        print(f"\n📝 关联故障过滤规则详情:")
        for idx, rule in filter_obj.group_rules.iterrows():
            fault_descs = []
            for col in rule.index:
                if col.startswith('故障描述') and pd.notna(rule[col]) and str(rule[col]).strip() != '':
                    fault_descs.append(rule[col])
            if fault_descs:
                print(f"   规则 {idx+1}: {rule.get('规则名称', '未命名')} - 同时出现: {' + '.join(fault_descs)}")

    # 应用过滤
    print(f"\n🔍 应用过滤规则...")
    filtered_df = filter_obj.apply_filters(df)

    print(f"\n✅ 过滤完成: {len(df)} → {len(filtered_df)} (过滤掉 {len(df) - len(filtered_df)} 条)")

    # 显示过滤后的数据
    if len(filtered_df) < len(df):
        print(f"\n📋 过滤后剩余故障:")
        print("-" * 80)
        for idx, row in filtered_df.iterrows():
            trigger_time = row['触发时间'] if '触发时间' in row else row.get('触发_time', '')
            print(f"{idx+1}. [{row['机号']}] {row['航班号']} - {trigger_time} - {row['描述']} - 阶段:{row['飞行阶段']}")
    else:
        print(f"\nℹ️  没有故障被过滤")

    # 分析被过滤的故障
    filtered_indices = set(df.index) - set(filtered_df.index)
    if filtered_indices:
        print(f"\n🗑️  被过滤的故障:")
        print("-" * 80)
        for idx in sorted(filtered_indices):
            row = df.loc[idx]
            trigger_time = row['触发时间'] if '触发时间' in row else row.get('触发_time', '')
            print(f"{idx+1}. [{row['机号']}] {row['航班号']} - {trigger_time} - {row['描述']} - 阶段:{row['飞行阶段']}")

    print(f"\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

    return True


if __name__ == "__main__":
    test_filter_with_today_data()

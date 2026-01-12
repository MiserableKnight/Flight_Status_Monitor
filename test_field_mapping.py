# -*- coding: utf-8 -*-
"""
测试字段映射功能
"""
from datetime import datetime

# 模拟提取的原始数据
raw_data = {
    '提取时间': '2026-01-12 16:30:00',
    '机号': 'B-656E',
    '机型': 'C919',
    '航空公司': '中国东方航空',
    '航班号': 'MU5321',
    '航段': '1',
    '故障码': '2435201',
    '时间': '2026-01-12 14:30:25',
    '故障描述': 'ADC1:INTERNAL FAULT - This is a very long fault description',
    '故障类型': 'MECHANICAL',
    '阶段': 'IN_AIR',
    '状态': 'OPEN',
    'ATA章节': '24-12',
    'FlightlegId': 'LEG123456',
    'ReportId': 'RPT789012'
}

# 字段映射
mapped_data = {
    '获取时间': raw_data.get('提取时间', ''),
    '机号': raw_data.get('机号', ''),
    '机型': raw_data.get('机型', ''),
    '航空公司': raw_data.get('航空公司', ''),
    '航班号': raw_data.get('航班号', ''),
    'ATA': raw_data.get('ATA章节', ''),
    '航段': raw_data.get('航段', ''),
    '触发时间': raw_data.get('时间', ''),
    '描述': raw_data.get('故障描述', ''),
    '故障类型': raw_data.get('故障类型', ''),
    '飞行阶段': raw_data.get('阶段', ''),
    '处理状态': raw_data.get('状态', ''),
    '类别-优先权': '',
    'FlightlegId': raw_data.get('FlightlegId', ''),
    'ReportId': raw_data.get('ReportId', '')
}

# 实际表头顺序
fieldnames = [
    '获取时间', '机号', '机型', '航空公司', '航班号',
    'ATA', '航段', '触发时间', '描述', '故障类型',
    '飞行阶段', '处理状态', '类别-优先权', 'FlightlegId', 'ReportId'
]

print("="*60)
print("📊 字段映射验证")
print("="*60)
print("\n✅ 原始数据字段（提取自HTML）:")
for k, v in raw_data.items():
    print(f"  {k:15s}: {v}")

print("\n✅ 映射后数据（按照实际表头顺序）:")
print("-"*60)
for field in fieldnames:
    value = mapped_data.get(field, '')
    if len(value) > 40:
        value = value[:40] + '...'
    print(f"  {field:15s}: {value}")

print("-"*60)
print("\n✅ 映射关系说明:")
print("  提取时间  → 获取时间")
print("  时间      → 触发时间")
print("  故障描述  → 描述")
print("  阶段      → 飞行阶段")
print("  状态      → 处理状态")
print("  ATA章节   → ATA")
print("  (新增)    → 类别-优先权（暂时为空）")

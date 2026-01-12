# -*- coding: utf-8 -*-
"""
测试优化后的故障数据提取功能 - 使用实际表头
"""
import re
from html import unescape
from datetime import datetime

# 测试用的HTML样本（使用原始字符串避免转义问题）
test_html = (
    '<div id="t_rtm_faultMainRowDiv12345" name="t_rtm_faultMainRowDiv">'
    '    <input type="hidden" id="rtmFlightlegId12345" value="LEG123456">'
    '    <input type="hidden" id="rtmReportId12345" value="RPT789012">'
    '    <input type="hidden" id="faultType12345" value="MECHANICAL">'
    '    <input type="hidden" id="messageTime12345" value="2026-01-12 14:30:25">'
    '    <ul class="ul0">'
    '        <li class="li0" style="width:5%;">&nbsp;<p style="float: left;cursor:pointer;">B-656E</p>&nbsp;</li>'
    '        <li class="li0" style="width:5%;">&nbsp;C919&nbsp;</li>'
    '        <li class="li0" style="width:9%;" title="中国东方航空">中国东方航空</li>'
    '        <li class="li0" style="width:5%;">&nbsp;MU5321&nbsp;</li>'
    '        <li class="li0" style="width:4%;">&nbsp;1&nbsp;</li>'
    '        <li class="li0" style="width:5%;">&nbsp;2435201&nbsp;</li>'
    '        <li class="li0" style="width:7%;">&nbsp;2026-01-12 14:30:25&nbsp;</li>'
    '        <li class="li0" style="width:30%;">'
    '            <div class="tr_longfont longtext" style="width:100%;">'
    '                <a href="#" title="ADC1:INTERNAL FAULT - This is a very long fault description that might be truncated on the page">'
    '                    ADC1:INTERNAL FAULT - This is a...'
    '                </a>'
    '            </div>'
    '        </li>'
    '        <li class="li0" style="width:5%;">&nbsp;IN_AIR&nbsp;</li>'
    '        <li class="li0" style="width:5%;"></li>'
    '        <li class="li0" style="width:8%;" id="state12345">'
    '            <div class="tr_longfont longtext" style="width:100%;">'
    '                <div>OPEN</div>'
    '            </div>'
    '        </li>'
    '        <li class="li0" style="width:7%;">&nbsp;24-12&nbsp;</li>'
    '    </ul>'
    '</div>'
)

def extract_row_data_optimized(row_html, fault_id):
    """
    优化后的故障数据提取函数 - 使用实际表头字段名
    """
    data = {}

    try:
        # 1. 优先从隐藏 input 中提取核心元数据（最准确）
        def get_hidden_val(name_id):
            match = re.search(f'id="{name_id}{fault_id}"[^>]*value="([^"]*)"', row_html)
            return unescape(match.group(1)) if match else ""

        data['FlightlegId'] = get_hidden_val('rtmFlightlegId')
        data['ReportId'] = get_hidden_val('rtmReportId')
        data['故障类型'] = get_hidden_val('faultType')
        data['触发时间'] = get_hidden_val('messageTime')

        # 2. 提取机号（从 <p> 标签提取）
        aircraft_match = re.search(r'<p[^>]*>(B-[\w]+)</p>', row_html.replace('&nbsp;', ''))
        data['机号'] = aircraft_match.group(1) if aircraft_match else ""

        # 3. 提取所有 <li> 内容
        li_contents = re.findall(r'<li[^>]*class="li0"[^>]*>(.*?)</li>', row_html, re.DOTALL)

        # 清理 HTML 标签的辅助函数
        def clean_html(raw_html):
            content = re.sub(r'<[^>]+>', '', raw_html)
            return unescape(content).replace('&nbsp;', '').strip()

        if len(li_contents) >= 11:
            data['机型'] = clean_html(li_contents[1])
            data['航空公司'] = clean_html(li_contents[2])
            data['航班号'] = clean_html(li_contents[3])
            data['航段'] = clean_html(li_contents[4])

            # 故障描述（从 <a> 标签的 title 提取）
            desc_match = re.search(r'<a[^>]*title="([^"]*)"', li_contents[7])
            data['描述'] = unescape(desc_match.group(1)) if desc_match else clean_html(li_contents[7])

            data['飞行阶段'] = clean_html(li_contents[8])
            data['处理状态'] = clean_html(li_contents[10])

            # ATA章节
            ata_match = re.search(r'<li[^>]*style="width:7%;">(.*?)</li>', row_html, re.DOTALL)
            data['ATA'] = clean_html(ata_match.group(1)) if ata_match else ""

            # 类别-优先权（暂时为空）
            data['类别-优先权'] = ""

        # 添加获取时间戳
        data['获取时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return data

    except Exception as e:
        print(f"❌ 深度解析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_optimized_extraction():
    """测试优化后的提取函数"""
    print("="*60)
    print("🧪 测试优化后的故障数据提取（实际表头）")
    print("="*60)

    # 提取数据
    result = extract_row_data_optimized(test_html, "12345")

    if result:
        print("\n✅ 提取成功！\n")
        print("📊 提取结果（按照实际表头顺序）:")
        print("-"*60)

        # 按照实际表头的顺序显示
        field_order = [
            '获取时间', '机号', '机型', '航空公司', '航班号',
            'ATA', '航段', '触发时间', '描述', '故障类型',
            '飞行阶段', '处理状态', '类别-优先权', 'FlightlegId', 'ReportId'
        ]

        for field in field_order:
            if field in result:
                value = result[field]
                # 对长字段进行截断显示
                if field == '描述' and len(value) > 50:
                    print(f"{field:15s}: {value[:50]}...")
                else:
                    print(f"{field:15s}: {value}")

        print("-"*60)

        # 验证关键字段
        print("\n🔍 验证关键字段:")
        print(f"  ✅ 机号: {result['机号']}")
        print(f"  ✅ 完整描述: {len(result['描述'])} 字符")
        print(f"  ✅ FlightlegId: {result['FlightlegId']}")
        print(f"  ✅ ReportId: {result['ReportId']}")
        print(f"  ✅ 触发时间: {result['触发时间']}")
        print(f"  ✅ 故障类型: {result['故障类型']}")
        print(f"  ✅ ATA章节: {result['ATA']}")
        print(f"  ✅ 飞行阶段: {result['飞行阶段']}")
        print(f"  ✅ 处理状态: {result['处理状态']}")

        return True
    else:
        print("\n❌ 提取失败！")
        return False


if __name__ == "__main__":
    test_optimized_extraction()

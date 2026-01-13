# -*- coding: utf-8 -*-
"""
故障数据HTML解析器

负责从复杂的HTML结构中提取故障数据
"""
import re
import time
from datetime import datetime
from html import unescape
from typing import List, Dict, Optional


class FaultParser:
    """故障数据HTML解析器"""

    def extract_fault_data(self, page) -> Optional[List[Dict]]:
        """
        从页面中提取故障数据（快速模式）

        Args:
            page: ChromiumPage 对象

        Returns:
            list: 故障数据列表
        """
        print("\n📊 开始提取故障数据...")

        try:
            # 找到数据容器
            data_con = page.ele('tag:div@@id=dataCon')
            if not data_con:
                print("   ❌ 未找到数据容器 #dataCon")
                return None

            print("   ✅ 找到数据容器")

            # 使用DOM方式提取所有行（更可靠）
            rows = data_con.eles('tag:div@@name=t_rtm_faultMainRowDiv')

            # 如果没找到行，多等两秒再试一次，防止由于网络波动导致的抓取失败
            if not rows:
                print("   ⏳ 首次未找到数据行，等待2秒后重试...")
                time.sleep(2)
                rows = data_con.eles('tag:div@@name=t_rtm_faultMainRowDiv')

            print(f"   ✅ 找到 {len(rows)} 行数据")

            if not rows:
                print("   ❌ 没有故障数据")
                return None

            # 批量提取数据（使用DOM但只提取一次）
            data_list = []
            for i, row in enumerate(rows):
                try:
                    # 直接从元素获取HTML，然后快速解析
                    row_html = row.html
                    # 从id属性提取故障ID
                    row_id = row.attr('id') or ''
                    fault_id = row_id.replace('t_rtm_faultMainRowDiv', '') if row_id else ''

                    data = self.extract_row_data_fast(row_html, fault_id)
                    if data:
                        data_list.append(data)
                        # 简洁输出（类似Leg Data）
                        print(f"   📝 第{i+1}行: {data['机号']} - {data['航班号']} - {data['故障描述'][:30]}...")
                except Exception as e:
                    print(f"   ⚠️ 提取第{i+1}行失败: {e}")
                    continue

            print(f"\n   ✅ 成功提取 {len(data_list)} 条故障记录")
            return data_list

        except Exception as e:
            print(f"   ❌ 提取数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def extract_row_data_fast(self, row_html: str, fault_id: str) -> Optional[Dict]:
        """
        针对复杂 HTML 结构优化的快速提取算法

        核心优化:
        1. 优先从隐藏 input 获取核心元数据（最准确）
        2. 从 <a> 标签 title 属性获取完整故障描述（解决截断问题）
        3. 增加唯一ID字段用于去重判断
        4. 更健壮的HTML清理逻辑

        Args:
            row_html: 行HTML字符串
            fault_id: 故障ID

        Returns:
            dict: 故障数据字典
        """
        data = {}

        try:
            # 提取原始数据（保持HTML结构对应的字段名）
            def get_hidden_val(name_id):
                match = re.search(f'id="{name_id}{fault_id}"[^>]*value="([^"]*)"', row_html)
                return unescape(match.group(1)) if match else ""

            # 从隐藏域提取
            data['FlightlegId'] = get_hidden_val('rtmFlightlegId')
            data['ReportId'] = get_hidden_val('rtmReportId')
            data['故障类型'] = get_hidden_val('faultType')
            data['时间'] = get_hidden_val('messageTime')

            # 提取机号
            aircraft_match = re.search(r'<p[^>]*>(B-[\w]+)</p>', row_html.replace('&nbsp;', ''))
            data['机号'] = aircraft_match.group(1) if aircraft_match else ""

            # 提取所有li内容
            li_contents = re.findall(r'<li[^>]*class="li0"[^>]*>(.*?)</li>', row_html, re.DOTALL)

            def clean_html(raw_html):
                content = re.sub(r'<[^>]+>', '', raw_html)
                return unescape(content).replace('&nbsp;', '').strip()

            if len(li_contents) >= 11:
                data['机型'] = clean_html(li_contents[1])
                data['航空公司'] = clean_html(li_contents[2])
                data['航班号'] = clean_html(li_contents[3])
                data['航段'] = clean_html(li_contents[4])
                data['故障码'] = clean_html(li_contents[5])
                # li_contents[6] 是时间

                # 故障描述（从title属性获取完整内容）
                desc_match = re.search(r'<a[^>]*title="([^"]*)"', li_contents[7])
                data['故障描述'] = unescape(desc_match.group(1)) if desc_match else clean_html(li_contents[7])

                data['阶段'] = clean_html(li_contents[8])
                # li_contents[9] 通常是空的
                data['状态'] = clean_html(li_contents[10])

                # ATA章节（倒数第二个li，7%宽度）
                ata_match = re.findall(r'<li[^>]*style="width:7%;">(.*?)</li>', row_html, re.DOTALL)
                if len(ata_match) >= 2:
                    data['ATA章节'] = clean_html(ata_match[1])  # 取最后一个7%的li
                else:
                    data['ATA章节'] = ""

            # 添加提取时间
            data['提取时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            return data

        except Exception as e:
            print(f"      ❌ 深度解析失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def extract_row_data(self, row) -> Optional[Dict]:
        """
        从单行中提取故障数据（DOM操作模式，作为备用）

        HTML 结构分析：
        - 机号: li[0] 中的文本
        - 机型: li[1]
        - 航空公司: li[2]
        - 航班号: li[3]
        - 航段: li[4]
        - 故障码: li[5]
        - 时间: li[6]
        - 故障描述: li[7] 中的 <a> 标签
        - 状态: li[8]
        - ATA章节: li[10]

        Args:
            row: 行元素

        Returns:
            dict: 故障数据字典
        """
        data = {}

        try:
            # 获取所有 li 元素
            lis = row.eles('tag:li@@class=li0')

            if len(lis) < 11:
                print(f"      ⚠️ 列数不足: {len(lis)}")
                return None

            # 提取各列数据
            # 机号 (li[0])
            aircraft_text = lis[0].text.strip()
            # 从文本中提取机号（包含B-XXXX格式）
            aircraft_match = re.search(r'B-\d{4}', aircraft_text)
            data['机号'] = aircraft_match.group(0) if aircraft_match else aircraft_text

            # 机型 (li[1])
            data['机型'] = lis[1].text.strip()

            # 航空公司 (li[2])
            data['航空公司'] = lis[2].text.strip()

            # 航班号 (li[3])
            data['航班号'] = lis[3].text.strip()

            # 航段 (li[4])
            data['航段'] = lis[4].text.strip()

            # 故障码 (li[5])
            data['故障码'] = lis[5].text.strip()

            # 时间 (li[6])
            data['时间'] = lis[6].text.strip()

            # 故障描述 (li[7] 中的 <a> 标签)
            fault_link = lis[7].ele('tag:a')
            if fault_link:
                data['故障描述'] = fault_link.text.strip()
                data['故障类型'] = fault_link.attr('title') or ''
            else:
                data['故障描述'] = lis[7].text.strip()
                data['故障类型'] = ''

            # 阶段 (li[8])
            data['阶段'] = lis[8].text.strip()

            # 状态 (li[9])
            state_div = lis[9].ele('tag:div')
            data['状态'] = state_div.text.strip() if state_div else lis[9].text.strip()

            # ATA章节 (li[10])
            data['ATA章节'] = lis[10].text.strip()

            # 添加提取时间
            data['提取时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            return data

        except Exception as e:
            print(f"      ❌ 提取行数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

"""
故障数据HTML解析器

负责从复杂的HTML结构中提取故障数据
"""

import re
from datetime import datetime
from html import unescape
from typing import Dict, List, Optional


class FaultParser:
    """故障数据HTML解析器"""

    def extract_fault_data(self, page) -> Optional[List[Dict]]:
        """
        从页面中提取故障数据（快速模式，支持主故障行和子故障行）

        Args:
            page: ChromiumPage 对象

        Returns:
            list: 故障数据列表（按时间排序，子行跟在父行后面）
        """
        print("\n📊 开始提取故障数据...")

        try:
            # 找到数据容器
            data_con = page.ele("tag:div@@id=dataCon")
            if not data_con:
                print("   ❌ 未找到数据容器 #dataCon")
                return None

            print("   ✅ 找到数据容器")

            # 使用DOM方式提取所有行（主故障行 + 子故障行）
            main_rows = data_con.eles("tag:div@@name=t_rtm_faultMainRowDiv")
            child_rows = data_con.eles("tag:div@@name=t_rtm_faultChildRowDiv")

            print(f"   ✅ 找到 {len(main_rows)} 个主故障行, {len(child_rows)} 个子故障行")

            total_rows = len(main_rows) + len(child_rows)
            if total_rows == 0:
                print("   ❌ 没有故障数据")
                return None

            # 先提取所有主故障行
            data_list = []
            parent_data_map = {}  # key: FlightlegId, value: parent_data

            for i, row in enumerate(main_rows):
                try:
                    row_html = row.html
                    row_id = row.attr("id") or ""
                    fault_id = row_id.replace("t_rtm_faultMainRowDiv", "") if row_id else ""

                    data = self.extract_row_data_fast(row_html, fault_id)
                    if data:
                        data_list.append(data)
                        # 提取FlightlegId用于后续匹配子行
                        flt_id_match = re.search(
                            r'id="rtmFlightlegId' + re.escape(fault_id) + r'"[^>]*value="(\d+)"',
                            row_html,
                        )
                        if flt_id_match:
                            flt_id = flt_id_match.group(1)
                            parent_data_map[flt_id] = {
                                "机号": data.get("机号", ""),
                                "机型": data.get("机型", ""),
                                "航空公司": data.get("航空公司", ""),
                                "航班号": data.get("航班号", ""),
                            }
                        print(
                            f"   📝 主行{i + 1}: {data['机号']} - {data['航班号']} - {data['故障描述'][:30]}..."
                        )
                except Exception as e:
                    print(f"   ⚠️ 提取主行{i + 1}失败: {e}")
                    continue

            # 再提取所有子故障行
            for i, row in enumerate(child_rows):
                try:
                    row_html = row.html
                    row_id = row.attr("id") or ""
                    fault_id = row_id.replace("t_rtm_faultChildRowDiv", "") if row_id else ""

                    # 从onclick事件中提取FlightlegId来匹配父行
                    parent_match = re.search(r"showFaultInfoNew\([^,]+,\s*(\d+),\s*this", row_html)
                    flt_id = parent_match.group(1) if parent_match else None
                    parent_data = parent_data_map.get(flt_id) if flt_id else None

                    data = self.extract_child_row_data_fast(row_html, fault_id, parent_data)
                    if data:
                        data_list.append(data)
                        print(
                            f"   📝 子行{i + 1}: {data['机号']} - {data['航班号']} - {data['故障描述'][:30]}..."
                        )
                except Exception as e:
                    print(f"   ⚠️ 提取子行{i + 1}失败: {e}")
                    continue

            # 按时间排序，确保子行紧跟在父行后面
            data_list = self._sort_by_time_and_group(data_list)

            print(f"\n   ✅ 成功提取 {len(data_list)} 条故障记录")
            return data_list

        except Exception as e:
            print(f"   ❌ 提取数据失败: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _sort_by_time_and_group(self, data_list: List[Dict]) -> List[Dict]:
        """
        按时间排序，并确保子故障行紧跟在父行后面

        排序逻辑：
        1. 先按FlightlegId分组
        2. 每组内按时间排序（父行在前，子行按时间紧随其后）
        3. 各组按父行时间排序

        Args:
            data_list: 原始数据列表

        Returns:
            排序后的数据列表
        """
        # 为每条记录添加排序键
        for idx, data in enumerate(data_list):
            # 提取时间用于排序
            time_str = data.get("时间", "00:00:00")
            if " " in time_str:
                # 格式: "2026-01-11 16:09:34"
                time_str = time_str.split(" ")[1]

            # 将时间转换为秒数
            try:
                h, m, s = map(int, time_str.split(":"))
                time_seconds = h * 3600 + m * 60 + s
            except:
                time_seconds = 0

            # 提取FlightlegId（从row_html中提取，如果没有则用索引）
            # 这里简化：使用航班号+日期作为分组依据
            group_key = f"{data.get('航班号', '')}_{data.get('日期', '')}"

            data["_sort_time"] = time_seconds
            data["_sort_group"] = group_key
            data["_sort_idx"] = idx

        # 排序：
        # 1. 先按分组（航班号）
        # 2. 同组内按时间
        # 但要确保主行（有故障类型的）在子行之前
        def sort_key(item):
            is_main = 1 if item.get("故障类型") else 0  # 主行优先
            return (
                item["_sort_group"],  # 按航班号分组
                item["_sort_time"],  # 同组内按时间
                is_main,  # 主行在前
                item["_sort_idx"],  # 保持原顺序
            )

        sorted_list = sorted(data_list, key=sort_key)

        # 清理临时字段
        for data in sorted_list:
            data.pop("_sort_time", None)
            data.pop("_sort_group", None)
            data.pop("_sort_idx", None)

        return sorted_list

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
            data["故障类型"] = get_hidden_val("faultType")
            data["时间"] = get_hidden_val("messageTime")

            # 提取机号
            aircraft_match = re.search(r"<p[^>]*>(B-[\w]+)</p>", row_html.replace("&nbsp;", ""))
            data["机号"] = aircraft_match.group(1) if aircraft_match else ""

            # 提取所有li内容
            li_contents = re.findall(r'<li[^>]*class="li0"[^>]*>(.*?)</li>', row_html, re.DOTALL)

            def clean_html(raw_html):
                content = re.sub(r"<[^>]+>", "", raw_html)
                return unescape(content).replace("&nbsp;", "").strip()

            if len(li_contents) >= 14:
                data["机型"] = clean_html(li_contents[1])
                data["航空公司"] = clean_html(li_contents[2])
                data["航班号"] = clean_html(li_contents[3])
                # li[4]: ATA章节
                data["ATA章节"] = clean_html(li_contents[4])
                # li[5]: 航段
                data["航段"] = clean_html(li_contents[5])
                # li_contents[6] 是时间

                # 故障描述（从title属性获取完整内容）
                desc_match = re.search(r'<a[^>]*title="([^"]*)"', li_contents[7])
                data["故障描述"] = (
                    unescape(desc_match.group(1)) if desc_match else clean_html(li_contents[7])
                )

                data["阶段"] = clean_html(li_contents[8])
                # li_contents[9] 通常是空的
                data["状态"] = clean_html(li_contents[10])
                # li_contents[11] 通常是空的
                # li_contents[12] 历史记录（不需要）
                # li[13]: 类别-优先权（最后一个li，宽度7%）
                data["类别-优先权"] = clean_html(li_contents[13])
            elif len(li_contents) >= 11:
                # 兼容旧版本HTML结构
                data["机型"] = clean_html(li_contents[1])
                data["航空公司"] = clean_html(li_contents[2])
                data["航班号"] = clean_html(li_contents[3])
                data["ATA章节"] = clean_html(li_contents[4])
                data["航段"] = clean_html(li_contents[5])
                # li_contents[6] 是时间

                # 故障描述（从title属性获取完整内容）
                desc_match = re.search(r'<a[^>]*title="([^"]*)"', li_contents[7])
                data["故障描述"] = (
                    unescape(desc_match.group(1)) if desc_match else clean_html(li_contents[7])
                )

                data["阶段"] = clean_html(li_contents[8])
                # li_contents[9] 通常是空的
                data["状态"] = clean_html(li_contents[10])
                data["类别-优先权"] = ""

            # 添加提取时间
            data["提取时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return data

        except Exception as e:
            print(f"      ❌ 深度解析失败: {e}")
            import traceback

            traceback.print_exc()
            return None

    def extract_child_row_data_fast(
        self, row_html: str, fault_id: str, parent_data: Optional[Dict]
    ) -> Optional[Dict]:
        """
        提取子故障行数据（从父行继承机号、机型、航空公司、航班号）

        子故障行特点：
        - 前4个 <li> 是空的（&nbsp;）
        - 需要继承父行的机号、机型、航空公司、航班号
        - li[4]: ATA章节
        - li[5]: 航段
        - li[6]: 时间
        - li[7]: 故障描述
        - li[8]: 飞行阶段
        - li[9]: 空
        - li[10]: 状态（可能为空）
        - li[11]: 空
        - li[12]: 历史记录
        - li[13]: 类别-优先权

        Args:
            row_html: 行HTML字符串
            fault_id: 故障ID
            parent_data: 父行数据（包含机号、机型、航空公司、航班号）

        Returns:
            dict: 故障数据字典
        """
        data = {}

        try:
            # 提取原始数据
            def get_hidden_val(name_id):
                match = re.search(f'id="{name_id}{fault_id}"[^>]*value="([^"]*)"', row_html)
                return unescape(match.group(1)) if match else ""

            # 从隐藏域提取
            fault_type = get_hidden_val("faultType")
            # 子故障行如果没有故障类型，默认为MMSG
            data["故障类型"] = fault_type if fault_type else "MMSG"
            data["时间"] = get_hidden_val("messageTime")

            # 从父行继承基本信息
            if parent_data:
                data["机号"] = parent_data.get("机号", "")
                data["机型"] = parent_data.get("机型", "")
                data["航空公司"] = parent_data.get("航空公司", "")
                data["航班号"] = parent_data.get("航班号", "")
            else:
                # 如果没有父行数据，尝试从最近的上下文推断
                # 从onclick事件中提取航班信息
                onclick_match = re.search(
                    r"showLegPage\('([^']*)',\s*'M?',\s*'([^/]*)/([^']*)'", row_html
                )
                if onclick_match:
                    data["机型"] = onclick_match.group(1)
                    aircraft_str = onclick_match.group(2)  # 例如: C909-196/B-656E
                    if "/" in aircraft_str:
                        data["航班号"] = aircraft_str.split("/")[0]  # C909-196
                        data["机号"] = aircraft_str.split("/")[1]  # B-656E
                    else:
                        data["机号"] = aircraft_str
                else:
                    data["机型"] = ""
                    data["航空公司"] = ""
                    data["航班号"] = ""
                    data["机号"] = ""

            # 提取所有li内容（包括没有class的li）
            # 使用更宽松的正则表达式，匹配所有 <li> 标签
            li_contents = re.findall(r"<li[^>]*>(.*?)</li>", row_html, re.DOTALL)

            def clean_html(raw_html):
                content = re.sub(r"<[^>]+>", "", raw_html)
                return unescape(content).replace("&nbsp;", "").strip()

            # 子故障行的li：前4个是空的，后续正常
            # li[0-3]: 空
            # li[4]: ATA章节 (77)
            # li[5]: 航段 (-11)
            # li[6]: 时间 (2026-01-11 16:09:34)
            # li[7]: 故障描述
            # li[8]: 飞行阶段 (In_Air)
            # li[9]: 空
            # li[10]: 状态
            # li[11]: 空
            # li[12]: 历史记录
            # li[13]: 类别-优先权 (M-ML)

            if len(li_contents) >= 14:
                # li[0-3]: 空的，跳过
                # li[4]: ATA章节
                data["ATA章节"] = clean_html(li_contents[4])
                # li[5]: 航段
                data["航段"] = clean_html(li_contents[5])
                # li[6]: 时间（已在隐藏域提取）

                # li[7]: 故障描述
                desc_match = re.search(r'<a[^>]*title="([^"]*)"', li_contents[7])
                data["故障描述"] = (
                    unescape(desc_match.group(1)) if desc_match else clean_html(li_contents[7])
                )

                # li[8]: 飞行阶段
                data["阶段"] = clean_html(li_contents[8])
                # li[9]: 空
                # li[10]: 状态
                data["状态"] = clean_html(li_contents[10])
                # li[11]: 空
                # li[12]: 历史记录（跳过）
                # li[13]: 类别-优先权
                data["类别-优先权"] = clean_html(li_contents[13])
            else:
                print(f"      ⚠️ 子行li数量不足: {len(li_contents)}，需要至少14个")
                # 调试：打印前几个li的内容
                for idx, li in enumerate(li_contents[:6]):
                    print(f"      li[{idx}]: {clean_html(li)[:50]}")

            # 添加提取时间
            data["提取时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return data

        except Exception as e:
            print(f"      ❌ 子行深度解析失败: {e}")
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
            lis = row.eles("tag:li@@class=li0")

            if len(lis) < 11:
                print(f"      ⚠️ 列数不足: {len(lis)}")
                return None

            # 提取各列数据
            # 机号 (li[0])
            aircraft_text = lis[0].text.strip()
            # 从文本中提取机号（包含B-XXXX格式）
            aircraft_match = re.search(r"B-\d{4}", aircraft_text)
            data["机号"] = aircraft_match.group(0) if aircraft_match else aircraft_text

            # 机型 (li[1])
            data["机型"] = lis[1].text.strip()

            # 航空公司 (li[2])
            data["航空公司"] = lis[2].text.strip()

            # 航班号 (li[3])
            data["航班号"] = lis[3].text.strip()

            # 航段 (li[4])
            data["航段"] = lis[4].text.strip()

            # 故障码 (li[5])
            data["故障码"] = lis[5].text.strip()

            # 时间 (li[6])
            data["时间"] = lis[6].text.strip()

            # 故障描述 (li[7] 中的 <a> 标签)
            fault_link = lis[7].ele("tag:a")
            if fault_link:
                data["故障描述"] = fault_link.text.strip()
                data["故障类型"] = fault_link.attr("title") or ""
            else:
                data["故障描述"] = lis[7].text.strip()
                data["故障类型"] = ""

            # 阶段 (li[8])
            data["阶段"] = lis[8].text.strip()

            # 状态 (li[9])
            state_div = lis[9].ele("tag:div")
            data["状态"] = state_div.text.strip() if state_div else lis[9].text.strip()

            # ATA章节 (li[10])
            data["ATA章节"] = lis[10].text.strip()

            # 添加提取时间
            data["提取时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return data

        except Exception as e:
            print(f"      ❌ 提取行数据失败: {e}")
            import traceback

            traceback.print_exc()
            return None

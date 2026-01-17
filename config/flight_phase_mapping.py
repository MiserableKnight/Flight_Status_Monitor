"""
飞行阶段映射配置
用于将故障数据中的飞行阶段缩写转换为中文描述
"""

# RTMU触发报文的飞行阶段映射
RTMU_PHASE_MAPPING = {
    "PO": "准备",
    "ES": "启发",
    "SL": "滑行",
    "TO": "起飞",
    "IC": "初始爬升",
    "CL": "爬升",
    "CR": "巡航",
    "DC": "下降",
    "AP": "进近",
    "LN": "着陆",
    "GA": "复飞",
    "IN": "滑入",
    "EO": "关车",
}

# CMS系统触发报文的飞行阶段映射
CMS_PHASE_MAPPING = {"Taxi": "滑行", "In_Air": "空中", "Ground": "地面"}

# 合并所有映射
PHASE_MAPPING = {**RTMU_PHASE_MAPPING, **CMS_PHASE_MAPPING}

# 故障类型映射
FAULT_TYPE_MAPPING = {"MMSG": "CMS", "FDE": "CAS"}


def get_fault_type_name(fault_type_code: str) -> str:
    """
    获取故障类型的中文名称

    Args:
        fault_type_code: 故障类型缩写（如 'MMSG', 'FDE' 等）

    Returns:
        str: 中文类型名称（如 'CMS'），如果找不到映射则返回原代码

    Examples:
        >>> get_fault_type_name('MMSG')
        'CMS'
        >>> get_fault_type_name('FDE')
        'CAS'
        >>> get_fault_type_name('UNKNOWN')
        'UNKNOWN'
    """
    if not fault_type_code:
        return ""

    return FAULT_TYPE_MAPPING.get(fault_type_code, fault_type_code)


def get_phase_name(phase_code: str, suffix: str = "阶段") -> str:
    """
    获取飞行阶段的中文名称

    Args:
        phase_code: 飞行阶段缩写（如 'AP', 'Taxi' 等）
        suffix: 后缀文字，默认为 '阶段'

    Returns:
        str: 中文阶段名称（如 '进近阶段'），如果找不到映射则返回原代码

    Examples:
        >>> get_phase_name('AP')
        '进近阶段'
        >>> get_phase_name('TO')
        '起飞阶段'
        >>> get_phase_name('UNKNOWN')
        'UNKNOWN'
    """
    if not phase_code:
        return ""

    # 查找映射
    chinese_name = PHASE_MAPPING.get(phase_code)

    if chinese_name:
        return f"{chinese_name}{suffix}"
    else:
        # 如果找不到映射，返回原代码
        return phase_code


def get_phase_name_without_suffix(phase_code: str) -> str:
    """
    获取飞行阶段的中文名称（不带后缀）

    Args:
        phase_code: 飞行阶段缩写（如 'AP', 'Taxi' 等）

    Returns:
        str: 中文阶段名称（如 '进近'），如果找不到映射则返回原代码
    """
    if not phase_code:
        return ""

    return PHASE_MAPPING.get(phase_code, phase_code)

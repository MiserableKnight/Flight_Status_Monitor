"""
数据相关异常类

处理数据提取、解析、验证、文件操作等数据层异常。
"""

from typing import Any, Optional

from .base import DataException


class DataExtractionError(DataException):
    """
    数据提取失败异常

    当从网页提取数据失败时抛出。
    """

    def __init__(
        self,
        aircraft: str,
        reason: str,
        flight: Optional[str] = None,
        element_selector: Optional[str] = None,
    ):
        """
        初始化数据提取异常

        Args:
            aircraft: 飞机号
            reason: 失败原因
            flight: 航班号（可选）
            element_selector: 失败的CSS选择器或XPath（可选）
        """
        context = {}
        if element_selector is not None:
            context["element_selector"] = element_selector

        message = f"数据提取失败 - {aircraft}"
        if flight:
            message += f" ({flight})"
        message += f": {reason}"

        super().__init__(message, aircraft=aircraft, flight=flight, context=context)


class DataValidationError(DataException):
    """
    数据验证失败异常

    当数据不符合预期格式或规则时抛出。
    """

    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
        aircraft: Optional[str] = None,
        flight: Optional[str] = None,
    ):
        """
        初始化数据验证异常

        Args:
            field: 验证失败的字段名
            value: 实际值
            reason: 验证失败原因
            aircraft: 飞机号（可选）
            flight: 航班号（可选）
        """
        context = {
            "field": field,
            "value": str(value),
            "reason": reason,
        }

        message = f"数据验证失败 - {field}: {value} ({reason})"
        if aircraft:
            message = f"{aircraft} - {message}"
        if flight:
            message += f" (航班: {flight})"

        super().__init__(message, aircraft=aircraft, flight=flight, context=context)


class DataParseError(DataException):
    """
    数据解析失败异常

    当解析CSV、JSON或其他格式数据失败时抛出。
    """

    def __init__(
        self,
        source: str,
        reason: str,
        line_number: Optional[int] = None,
        raw_data: Optional[str] = None,
    ):
        """
        初始化数据解析异常

        Args:
            source: 数据源（文件路径或URL）
            reason: 解析失败原因
            line_number: 错误行号（可选）
            raw_data: 原始数据片段（可选）
        """
        context = {"source": source, "reason": reason}
        if line_number is not None:
            context["line_number"] = line_number
        if raw_data is not None:
            context["raw_data_preview"] = raw_data[:100]  # 限制长度

        message = f"数据解析失败 - {source}: {reason}"
        if line_number is not None:
            message += f" (行 {line_number})"

        super().__init__(message, context=context)


class DataFileError(DataException):
    """
    数据文件操作异常

    当文件读写、删除等操作失败时抛出。
    """

    def __init__(
        self,
        file_path: str,
        operation: str,
        reason: str,
        aircraft: Optional[str] = None,
    ):
        """
        初始化数据文件异常

        Args:
            file_path: 文件路径
            operation: 操作类型（read/write/delete等）
            reason: 失败原因
            aircraft: 相关飞机号（可选）
        """
        context = {
            "file_path": file_path,
            "operation": operation,
            "reason": reason,
        }

        message = f"文件{operation}失败 - {file_path}: {reason}"

        super().__init__(message, aircraft=aircraft, context=context)


class DataFreshnessError(DataException):
    """
    数据新鲜度异常

    当数据过于陈旧不满足监控要求时抛出。
    """

    def __init__(
        self,
        data_type: str,
        last_update_time: str,
        current_time: str,
        max_age_minutes: int,
        aircraft: Optional[str] = None,
    ):
        """
        初始化数据新鲜度异常

        Args:
            data_type: 数据类型（leg/fault）
            last_update_time: 最后更新时间
            current_time: 当前时间
            max_age_minutes: 允许的最大数据年龄（分钟）
            aircraft: 飞机号（可选）
        """
        context = {
            "data_type": data_type,
            "last_update": last_update_time,
            "current_time": current_time,
            "max_age_minutes": max_age_minutes,
        }

        message = (
            f"数据过时 - {data_type} 数据最后更新: {last_update_time} (超过 {max_age_minutes} 分钟)"
        )

        super().__init__(message, aircraft=aircraft, context=context)

# -*- coding: utf-8 -*-
"""
日志记录模块
提供统一的日志记录功能，自动清理过期日志
"""
import os
from datetime import datetime, timedelta
from typing import Callable


def get_logger(log_dir: str = "logs", hours: int = 24) -> Callable:
    """
    获取一个日志记录器函数

    Args:
        log_dir: 日志文件存储目录
        hours: 日志保留时间（小时）

    Returns:
        Callable: 日志记录函数

    Example:
        >>> log = get_logger()
        >>> log("这是一条信息")
        >>> log("这是一条警告", "WARNING")
        >>> log("这是一条错误", "ERROR")
        >>> log("操作成功", "SUCCESS")
    """
    # 创建日志目录
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 清理过期日志
    cleanup_old_logs(log_dir, hours)

    # 获取当前日志文件名 (YYYY-MM-DD.log)
    log_filename = datetime.now().strftime("%Y-%m-%d.log")
    log_path = os.path.join(log_dir, log_filename)

    def logger(message: str, level: str = "INFO"):
        """
        记录日志消息

        Args:
            message: 日志消息
            level: 日志级别 (INFO, WARNING, ERROR, SUCCESS)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"

        # 输出到控制台
        print(log_line)

        # 写入日志文件
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception as e:
            print(f"❌ 写入日志失败: {e}")

    return logger


def cleanup_old_logs(log_dir: str, hours: int = 24):
    """
    清理超过指定时间的旧日志文件

    Args:
        log_dir: 日志文件目录
        hours: 保留时间（小时）
    """
    if not os.path.exists(log_dir):
        return

    cutoff_time = datetime.now() - timedelta(hours=hours)

    for filename in os.listdir(log_dir):
        if not filename.endswith(".log"):
            continue

        filepath = os.path.join(log_dir, filename)

        # 获取文件修改时间
        try:
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))

            # 如果文件过期则删除
            if file_mtime < cutoff_time:
                os.remove(filepath)
                print(f"[CLEANUP] 已删除过期日志: {filename}")
        except Exception as e:
            print(f"[ERROR] 删除日志文件失败 {filename}: {e}")


# 默认日志记录器实例
default_logger = get_logger()


if __name__ == "__main__":
    # 测试代码
    print("🧪 日志模块测试")
    print("="*60)

    log = get_logger()

    log("这是一条普通信息")
    log("这是一条警告信息", "WARNING")
    log("这是一条错误信息", "ERROR")
    log("操作成功完成", "SUCCESS")

    print("\n✅ 测试完成，请查看 logs 目录")

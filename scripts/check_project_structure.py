#!/usr/bin/env python3
"""
检查项目结构是否与 README.md 同步

在 git commit 前运行此脚本，确保 README.md 中的项目结构
与实际项目结构保持一致。
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple

# 需要忽略的文件和目录
IGNORED_PATTERNS = [
    "__pycache__",
    "*.pyc",
    ".git",
    ".venv",
    "venv",
    "ENV",
    "env",
    ".pytest_cache",
    ".ruff_cache",
    "*.egg-info",
    "build",
    "dist",
    ".vscode",
    ".idea",
    "*.log",
    "*.tmp",
    ".DS_Store",
]

# 需要忽略的特定路径
IGNORED_PATHS = {
    ".git",
    ".venv",
    "venv",
    "ENV",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".vscode",
    ".idea",
    "node_modules",
}


def is_ignored(path: str) -> bool:
    """检查路径是否应该被忽略"""
    path_parts = Path(path).parts

    # 检查是否在忽略列表中
    for part in path_parts:
        if part in IGNORED_PATHS:
            return True

    # 检查文件扩展名
    for pattern in IGNORED_PATTERNS:
        if pattern.startswith("*"):
            if str(path).endswith(pattern[1:]):
                return True
        elif pattern in str(path):
            return True

    return False


def get_actual_structure(root_dir: Path) -> Set[str]:
    """
    获取实际的项目结构

    Args:
        root_dir: 项目根目录

    Returns:
        文件和目录的集合
    """
    structure = set()

    for item in root_dir.iterdir():
        if is_ignored(item.name):
            continue

        structure.add(item.name)

        # 如果是目录，递归添加内容
        if item.is_dir():
            try:
                for sub_item in item.iterdir():
                    if is_ignored(sub_item.name):
                        continue

                    # 添加二级路径
                    structure.add(f"{item.name}/{sub_item.name}")

                    # 对特定目录添加三级内容
                    if sub_item.is_dir() and sub_item.name in [
                        "config",
                        "tests",
                        "docs",
                        "bin",
                        "fetchers",
                        "processors",
                        "notifiers",
                        "schedulers",
                        "core",
                        "interfaces",
                    ]:
                        for deep_item in sub_item.iterdir():
                            if is_ignored(deep_item.name):
                                continue
                            structure.add(f"{item.name}/{sub_item.name}/{deep_item.name}")
            except PermissionError:
                pass

    return structure


def parse_readme_structure(readme_path: Path) -> Set[str]:
    """
    从 README.md 中解析项目结构

    Args:
        readme_path: README.md 文件路径

    Returns:
        从 README 中提取的文件和目录集合
    """
    if not readme_path.exists():
        return set()

    content = readme_path.read_text(encoding="utf-8")

    # 查找项目结构的代码块
    structure_block_match = re.search(r"```[\s\S]*?Flight_Status_Monitor/([\s\S]*?)```", content)

    if not structure_block_match:
        return set()

    structure_text = structure_block_match.group(1)
    structure = set()

    # 解析树形结构
    for line in structure_text.split("\n"):
        # 跳过空行
        if not line.strip():
            continue

        # 移除所有树形符号前缀
        path = line.strip()

        # 移除所有可能的树形符号
        for prefix in ["│   ", "    ", "├── ", "└── ", "│── "]:
            while path.startswith(prefix):
                path = path[len(prefix) :]

        # 移除注释（# 开头的内容）
        path = path.split("#")[0].strip()

        # 只保留文件名/目录名（不是路径）
        if path and "/" not in path and not path.startswith("Flight_Status_Monitor"):
            # 过滤掉非文件名字符
            if path and not any(c in path for c in ["│", "├", "└", "─"]):
                structure.add(path)

    return structure


def compare_structures(actual: Set[str], documented: Set[str]) -> Tuple[List[str], List[str]]:
    """
    比较实际结构和文档结构

    Args:
        actual: 实际的项目结构
        documented: README 中记录的结构

    Returns:
        (新增的文件/目录, 缺失的文件/目录)
    """
    added = sorted(actual - documented)
    removed = sorted(documented - actual)

    return added, removed


def print_warning(added: List[str], removed: List[str]) -> None:
    """打印警告信息"""
    print("\n" + "=" * 70)
    print("⚠️  警告: README.md 中的项目结构与实际项目结构不一致！")
    print("=" * 70)

    if added:
        print(f"\n📁 新增的文件/目录（共 {len(added)} 个，未在 README 中记录）:")
        for item in added[:15]:  # 最多显示 15 个
            print(f"  + {item}")
        if len(added) > 15:
            print(f"  ... 还有 {len(added) - 15} 个")

    if removed:
        print(f"\n🗑️  缺失的文件/目录（共 {len(removed)} 个，README 中有但实际不存在）:")
        for item in removed[:15]:  # 最多显示 15 个
            print(f"  - {item}")
        if len(removed) > 15:
            print(f"  ... 还有 {len(removed) - 15} 个")

    print("\n💡 建议:")
    print("  1. 运行以下命令生成新的项目结构:")
    print("     python scripts/check_project_structure.py --generate")
    print("  2. 将生成的结构复制到 README.md 中替换现有结构")
    print("=" * 70 + "\n")


def generate_structure_tree(root_dir: Path) -> str:
    """生成项目结构的树形图"""
    lines = ["Flight_Status_Monitor/"]

    # 定义目录顺序（重要目录在前）
    priority_dirs = [
        "bin",
        "config",
        "core",
        "fetchers",
        "processors",
        "notifiers",
        "schedulers",
        "interfaces",
        "data",
        "logs",
        "tests",
        "docs",
    ]

    # 获取一级目录/文件
    items = []
    for item in root_dir.iterdir():
        if is_ignored(item.name):
            continue
        items.append(item)

    # 自定义排序：优先目录在前，然后按字母顺序
    def sort_key(item):
        if not item.is_dir():
            return (2, item.name)
        if item.name in priority_dirs:
            return (0, priority_dirs.index(item.name))
        return (1, item.name)

    items.sort(key=sort_key)

    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        prefix = "└── " if is_last else "├── "
        lines.append(f"{prefix}{item.name}")

        # 如果是目录，添加二级内容
        if item.is_dir():
            try:
                sub_items = []
                for sub_item in item.iterdir():
                    if is_ignored(sub_item.name):
                        continue
                    sub_items.append(sub_item)

                # 二级文件排序（目录优先）
                sub_items.sort(key=lambda x: (not x.is_dir(), x.name))

                for j, sub_item in enumerate(sub_items):
                    sub_is_last = j == len(sub_items) - 1
                    sub_prefix = "    " if is_last else "│   "
                    sub_prefix += "└── " if sub_is_last else "├── "
                    lines.append(f"{sub_prefix}{sub_item.name}")

                    # 对特定目录添加三级内容
                    if sub_item.is_dir() and sub_item.name in [
                        "config",
                        "tests",
                        "docs",
                        "bin",
                        "fetchers",
                        "processors",
                        "notifiers",
                        "schedulers",
                        "core",
                        "interfaces",
                    ]:
                        try:
                            deep_items = []
                            for deep_item in sub_item.iterdir():
                                if is_ignored(deep_item.name):
                                    continue
                                deep_items.append(deep_item)

                            deep_items.sort(key=lambda x: (not x.is_dir(), x.name))

                            for k, deep_item in enumerate(deep_items):
                                deep_is_last = k == len(deep_items) - 1
                                deep_prefix = sub_prefix[:-4] + ("    " if sub_is_last else "│   ")
                                deep_prefix += "└── " if deep_is_last else "├── "
                                lines.append(f"{deep_prefix}{deep_item.name}")
                        except PermissionError:
                            pass

            except PermissionError:
                pass

    return "\n".join(lines)


def main():
    """主函数"""
    # 获取项目根目录
    root_dir = Path(__file__).parent.parent
    readme_path = root_dir / "README.md"

    # 生成模式
    if "--generate" in sys.argv:
        tree = generate_structure_tree(root_dir)
        print("\n" + "=" * 70)
        print("📋 项目结构（可直接复制到 README.md）:")
        print("=" * 70)
        print("\n```\n" + tree + "\n```\n")
        return 0

    # 检查模式
    actual_structure = get_actual_structure(root_dir)
    documented_structure = parse_readme_structure(readme_path)

    # 比较结构
    added, removed = compare_structures(actual_structure, documented_structure)

    # 如果有差异，显示警告
    if added or removed:
        print_warning(added, removed)

        # 在 CI/CD 环境中返回错误码
        if os.environ.get("CI") or "--strict" in sys.argv:
            return 1

        # 本地开发时只警告，不阻止提交
        print("⚠️  提交将继续，但建议尽快更新 README.md\n")
        return 0
    else:
        print("✅ README.md 中的项目结构与实际项目结构一致")
        return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Wrapper script to ensure venv Python is used for pre-commit hooks
"""

import sys
from pathlib import Path

# Find venv Python
project_root = Path(__file__).parent.parent
venv_python = project_root / "venv" / "Scripts" / "python.exe"

if not venv_python.exists():
    print(f"Error: Virtual environment not found at {venv_python}", file=sys.stderr)
    print("Please run: python -m venv venv", file=sys.stderr)
    sys.exit(1)

# Run the actual checker with the venv Python
import subprocess

result = subprocess.run(
    [str(venv_python), str(Path(__file__).parent / "check_project_structure.py")] + sys.argv[1:],
    cwd=project_root,
)

sys.exit(result.returncode)

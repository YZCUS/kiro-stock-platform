#!/usr/bin/env python3
"""
最終 models/ 清理 - 遷移所有引用到 domain/models
"""
import os
import re
from pathlib import Path

# Import 遷移映射
MIGRATIONS = {
    "from domain.models.base import": "from domain.models.base import",
    "from domain.models": "from domain.models",
    "from domain.models import": "from domain.models import",
}


def migrate_file(filepath: Path):
    """遷移單個文件"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        for old, new in MIGRATIONS.items():
            content = content.replace(old, new)

        if content != original:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ {filepath}")
            return True

        return False

    except Exception as e:
        print(f"✗ {filepath}: {e}")
        return False


def main():
    backend_dir = Path("/home/opc/projects/kiro-stock-platform/backend")

    # 遷移所有目錄
    dirs_to_migrate = [
        "domain",
        "infrastructure",
        "api",
        "tests",
        "scripts",
        "alembic",
        "app",
        "core",
    ]

    count = 0
    for dir_name in dirs_to_migrate:
        dir_path = backend_dir / dir_name
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            if migrate_file(py_file):
                count += 1

    print(f"\n總共遷移 {count} 個文件")
    print("\n下一步: 刪除 backend/models/")


if __name__ == "__main__":
    main()

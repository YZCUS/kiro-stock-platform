#!/usr/bin/env python3
"""
自動遷移 models.domain → domain.models
"""
import os
import re
from pathlib import Path

# 需要遷移的 import 映射
IMPORT_MAPPINGS = {
    'from domain.models.stock': 'from domain.models.stock',
    'from domain.models.price_history': 'from domain.models.price_history',
    'from domain.models.technical_indicator': 'from domain.models.technical_indicator',
    'from domain.models.trading_signal': 'from domain.models.trading_signal',
    'from domain.models.system_log': 'from domain.models.system_log',
    'from domain.models.user_watchlist': 'from domain.models.user_watchlist',
    'from domain.models import': 'from domain.models import',
}

def migrate_file(filepath: Path):
    """遷移單個文件的 imports"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 替換所有映射
        for old_import, new_import in IMPORT_MAPPINGS.items():
            content = content.replace(old_import, new_import)

        # 如果有變更，寫回文件
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 已遷移: {filepath}")
            return True

        return False

    except Exception as e:
        print(f"✗ 錯誤 {filepath}: {e}")
        return False

def main():
    backend_dir = Path('/home/opc/projects/kiro-stock-platform/backend')

    # 需要遷移的目錄
    target_dirs = [
        'domain',
        'infrastructure',
        'alembic',
        'tests',
    ]

    migrated_count = 0

    for target_dir in target_dirs:
        dir_path = backend_dir / target_dir
        if not dir_path.exists():
            continue

        # 遍歷所有 Python 文件
        for py_file in dir_path.rglob('*.py'):
            if migrate_file(py_file):
                migrated_count += 1

    print(f"\n總共遷移了 {migrated_count} 個文件")

    # 提醒用戶
    print("\n下一步:")
    print("1. 檢查遷移結果: git diff")
    print("2. 運行測試: python -m pytest tests/")
    print("3. 刪除 models/domain/: rm -rf backend/models/domain")
    print("4. 刪除 models/schemas/: rm -rf backend/models/schemas")
    print("5. 刪除 models/: rm -rf backend/models")

if __name__ == '__main__':
    main()

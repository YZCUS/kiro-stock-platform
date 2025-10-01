#!/usr/bin/env python3
"""
自動遷移 services 文件使用 repositories 而不是 CRUD
"""
import os
import re
from pathlib import Path

# CRUD 到 Repository 的映射
CRUD_TO_REPO_MAP = {
    'crud_stock': {
        'import': 'from infrastructure.persistence.stock_repository import StockRepository',
        'crud_var': 'stock_crud',
        'repo_class': 'StockRepository',
        'repo_var': 'stock_repo'
    },
    'crud_price_history': {
        'import': 'from infrastructure.persistence.price_history_repository import PriceHistoryRepository',
        'crud_var': 'price_history_crud',
        'repo_class': 'PriceHistoryRepository',
        'repo_var': 'price_repo'
    },
    'crud_technical_indicator': {
        'import': 'from infrastructure.persistence.technical_indicator_repository import TechnicalIndicatorRepository',
        'crud_var': 'technical_indicator_crud',
        'repo_class': 'TechnicalIndicatorRepository',
        'repo_var': 'indicator_repo'
    },
    'crud_trading_signal': {
        'import': 'from infrastructure.persistence.trading_signal_repository import TradingSignalRepository',
        'crud_var': 'trading_signal_crud',
        'repo_class': 'TradingSignalRepository',
        'repo_var': 'signal_repo'
    }
}

# 需要遷移的服務文件
SERVICE_FILES = [
    'backend/services/infrastructure/storage.py',
    'backend/services/infrastructure/sync.py',
    'backend/services/infrastructure/scheduler.py',
    'backend/services/data/collection.py',
    'backend/services/data/validation.py',
    'backend/services/data/cleaning.py',
    'backend/services/data/backfill.py',
    'backend/services/analysis/signal_detector.py',
    'backend/services/analysis/technical_analysis.py',
    'backend/services/trading/buy_sell_generator.py',
    'backend/services/trading/signal_notification.py',
]

def migrate_file(filepath):
    """遷移單個文件"""
    if not os.path.exists(filepath):
        print(f"⚠ File not found: {filepath}")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    imports_added = set()
    replacements_made = []

    # 步驟 1: 替換 import 語句
    for crud_name, mapping in CRUD_TO_REPO_MAP.items():
        old_import = f"from models.repositories.{crud_name} import {mapping['crud_var']}"
        if old_import in content:
            # 移除舊 import
            content = content.replace(old_import, '')
            # 添加新 import (稍後統一添加)
            imports_added.add(mapping['import'])
            replacements_made.append(f"Import: {old_import} → {mapping['import']}")

    # 步驟 2: 替換 CRUD 調用
    for crud_name, mapping in CRUD_TO_REPO_MAP.items():
        crud_var = mapping['crud_var']
        repo_class = mapping['repo_class']
        repo_var = mapping['repo_var']

        # 查找所有 crud 調用
        # 模式: crud_var.method_name(
        pattern = f"{crud_var}\\.([a-zA-Z_][a-zA-Z0-9_]*)\\("
        matches = re.finditer(pattern, content)

        for match in matches:
            method_name = match.group(1)
            # 檢查這個方法調用前是否已經有 repo 初始化
            # 這個簡化版本只是替換調用，不檢查上下文
            old_call = f"{crud_var}.{method_name}("
            new_call = f"{repo_var}.{method_name}("
            if old_call in content:
                content = content.replace(old_call, new_call)
                replacements_made.append(f"Call: {old_call} → {new_call}")

    # 步驟 3: 在適當位置添加新的 imports
    if imports_added:
        # 找到現有 imports 的位置
        import_section_match = re.search(r'(from [^\n]+ import [^\n]+\n)+', content)
        if import_section_match:
            insert_pos = import_section_match.end()
            new_imports = '\n# ✅ Clean Architecture: 使用 repository implementations\n'
            new_imports += '\n'.join(sorted(imports_added)) + '\n'
            content = content[:insert_pos] + new_imports + content[insert_pos:]

    # 步驟 4: 添加 repository 初始化 (在函數開頭)
    # 這個版本簡化，假設每個函數都會自己初始化需要的 repo
    # 實際使用時可能需要手動調整

    # 只有在內容改變時才寫回文件
    if content != original_content:
        # 備份原文件
        backup_path = filepath + '.bak'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)

        # 寫入新內容
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✓ Migrated: {filepath}")
        print(f"  Backup: {backup_path}")
        print(f"  Changes:")
        for change in replacements_made[:5]:  # 只顯示前5個變更
            print(f"    - {change}")
        if len(replacements_made) > 5:
            print(f"    ... and {len(replacements_made) - 5} more changes")
        return True
    else:
        print(f"- No changes needed: {filepath}")
        return False

def main():
    print("=" * 80)
    print("AUTOMATED CRUD TO REPOSITORY MIGRATION")
    print("=" * 80)
    print()

    migrated_count = 0
    failed_count = 0

    for filepath in SERVICE_FILES:
        try:
            if migrate_file(filepath):
                migrated_count += 1
        except Exception as e:
            print(f"✗ Error migrating {filepath}: {e}")
            failed_count += 1

    print()
    print("=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"Total files: {len(SERVICE_FILES)}")
    print(f"Migrated: {migrated_count}")
    print(f"Failed: {failed_count}")
    print(f"No changes: {len(SERVICE_FILES) - migrated_count - failed_count}")
    print()
    print("⚠ IMPORTANT: Manual review required!")
    print("  1. Check repository initialization in functions")
    print("  2. Verify method signatures match")
    print("  3. Test all modified files")
    print("  4. Remove .bak files after verification")
    print()

if __name__ == '__main__':
    main()

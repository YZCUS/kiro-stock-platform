#!/usr/bin/env python3
"""
Airflow DAG 驗證腳本
驗證所有 DAG 的語法和依賴是否正確
"""
import os
import sys
import importlib.util
import traceback
from pathlib import Path
from typing import List, Dict, Any


def load_dag_file(dag_file: Path) -> Dict[str, Any]:
    """載入並驗證單個 DAG 文件"""
    result = {
        'file': str(dag_file),
        'success': False,
        'error': None,
        'dags': [],
        'imports': []
    }

    try:
        # 創建模組規格
        spec = importlib.util.spec_from_file_location(
            dag_file.stem, dag_file
        )
        if spec is None or spec.loader is None:
            result['error'] = "無法創建模組規格"
            return result

        # 載入模組
        module = importlib.util.module_from_spec(spec)

        # 設置 sys.path 以支援相對導入
        dag_dir = str(dag_file.parent)
        if dag_dir not in sys.path:
            sys.path.insert(0, dag_dir)

        try:
            spec.loader.exec_module(module)
        finally:
            # 清理 sys.path
            if dag_dir in sys.path:
                sys.path.remove(dag_dir)

        # 查找 DAG 對象
        dags = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if hasattr(attr, '__class__') and attr.__class__.__name__ == 'DAG':
                dags.append({
                    'dag_id': attr.dag_id,
                    'description': getattr(attr, 'description', ''),
                    'schedule_interval': getattr(attr, 'schedule_interval', None),
                    'tags': getattr(attr, 'tags', [])
                })

        result['dags'] = dags
        result['success'] = True

    except ImportError as e:
        result['error'] = f"導入錯誤: {str(e)}"
    except SyntaxError as e:
        result['error'] = f"語法錯誤: {str(e)}"
    except Exception as e:
        result['error'] = f"其他錯誤: {str(e)}\n{traceback.format_exc()}"

    return result


def validate_all_dags(dags_dir: Path) -> Dict[str, Any]:
    """驗證所有 DAG 文件"""
    print(f"🔍 驗證 DAG 目錄: {dags_dir}")

    # 查找所有 DAG 文件
    dag_files = []
    for pattern in ['**/*.py']:
        dag_files.extend(dags_dir.glob(pattern))

    # 排除測試文件和 __pycache__
    dag_files = [
        f for f in dag_files
        if not f.name.startswith('test_')
        and '__pycache__' not in str(f)
        and not f.name.startswith('__')
    ]

    print(f"找到 {len(dag_files)} 個 DAG 文件")

    results = {
        'total_files': len(dag_files),
        'successful_files': 0,
        'failed_files': 0,
        'total_dags': 0,
        'file_results': [],
        'errors': []
    }

    # 驗證每個文件
    for dag_file in dag_files:
        print(f"  驗證: {dag_file.relative_to(dags_dir)}")

        file_result = load_dag_file(dag_file)
        results['file_results'].append(file_result)

        if file_result['success']:
            results['successful_files'] += 1
            results['total_dags'] += len(file_result['dags'])

            if file_result['dags']:
                for dag_info in file_result['dags']:
                    print(f"    ✅ DAG: {dag_info['dag_id']}")
            else:
                print(f"    ⚠️  文件中沒有找到 DAG 對象")
        else:
            results['failed_files'] += 1
            results['errors'].append({
                'file': file_result['file'],
                'error': file_result['error']
            })
            print(f"    ❌ 錯誤: {file_result['error']}")

    return results


def check_dag_dependencies(results: Dict[str, Any]) -> None:
    """檢查 DAG 之間的依賴關係"""
    print("\n🔗 檢查 DAG 依賴關係...")

    all_dag_ids = set()
    for file_result in results['file_results']:
        if file_result['success']:
            for dag_info in file_result['dags']:
                all_dag_ids.add(dag_info['dag_id'])

    print(f"發現 {len(all_dag_ids)} 個 DAG:")
    for dag_id in sorted(all_dag_ids):
        print(f"  - {dag_id}")

    # 檢查 DAG ID 唯一性
    dag_id_count = {}
    for file_result in results['file_results']:
        if file_result['success']:
            for dag_info in file_result['dags']:
                dag_id = dag_info['dag_id']
                if dag_id not in dag_id_count:
                    dag_id_count[dag_id] = []
                dag_id_count[dag_id].append(file_result['file'])

    duplicates = {k: v for k, v in dag_id_count.items() if len(v) > 1}
    if duplicates:
        print("\n⚠️  發現重複的 DAG ID:")
        for dag_id, files in duplicates.items():
            print(f"  DAG ID '{dag_id}' 出現在:")
            for file in files:
                print(f"    - {file}")
    else:
        print("\n✅ 所有 DAG ID 都是唯一的")


def generate_validation_report(results: Dict[str, Any]) -> None:
    """生成驗證報告"""
    print("\n" + "="*60)
    print("📊 DAG 驗證報告")
    print("="*60)

    print(f"\n📁 總文件數: {results['total_files']}")
    print(f"✅ 成功載入: {results['successful_files']}")
    print(f"❌ 載入失敗: {results['failed_files']}")
    print(f"📦 總 DAG 數: {results['total_dags']}")

    if results['failed_files'] > 0:
        print(f"\n❌ 失敗的文件 ({results['failed_files']} 個):")
        for error in results['errors']:
            print(f"\n  📄 {error['file']}:")
            print(f"    錯誤: {error['error']}")

    success_rate = (results['successful_files'] / results['total_files']) * 100
    print(f"\n📊 成功率: {success_rate:.1f}%")

    if results['failed_files'] == 0:
        print("\n🎉 所有 DAG 文件都通過驗證！")
    else:
        print(f"\n⚠️  有 {results['failed_files']} 個文件需要修復")


def suggest_fixes(results: Dict[str, Any]) -> None:
    """建議修復方案"""
    if results['failed_files'] == 0:
        return

    print("\n" + "="*60)
    print("🔧 修復建議")
    print("="*60)

    common_errors = {}
    for error in results['errors']:
        error_type = error['error'].split(':')[0]
        if error_type not in common_errors:
            common_errors[error_type] = []
        common_errors[error_type].append(error['file'])

    for error_type, files in common_errors.items():
        print(f"\n{error_type} ({len(files)} 個文件):")

        if "導入錯誤" in error_type:
            print("  💡 可能的解決方案:")
            print("     - 檢查 requirements.txt 中是否聲明了所需依賴")
            print("     - 運行: python3 scripts/check_dependencies.py")
            print("     - 確保模組路徑正確")

        elif "語法錯誤" in error_type:
            print("  💡 可能的解決方案:")
            print("     - 檢查 Python 語法")
            print("     - 運行: python -m py_compile <文件名>")
            print("     - 使用 IDE 檢查語法錯誤")

        print("  📁 相關文件:")
        for file in files:
            print(f"     - {file}")


def main():
    """主函數"""
    # 確定 DAGs 目錄
    script_dir = Path(__file__).parent
    airflow_dir = script_dir.parent
    dags_dir = airflow_dir / "dags"

    if not dags_dir.exists():
        print(f"❌ DAGs 目錄不存在: {dags_dir}")
        sys.exit(1)

    print("🏗️  Airflow DAG 驗證工具")
    print(f"DAGs 目錄: {dags_dir}")

    try:
        # 執行 DAG 驗證
        results = validate_all_dags(dags_dir)

        # 檢查依賴關係
        check_dag_dependencies(results)

        # 生成報告
        generate_validation_report(results)

        # 提供修復建議
        suggest_fixes(results)

        # 根據結果設置退出碼
        if results['failed_files'] > 0:
            print(f"\n⚠️  有 {results['failed_files']} 個文件驗證失敗")
            sys.exit(1)
        else:
            print("\n🎉 所有 DAG 驗證通過！")
            sys.exit(0)

    except Exception as e:
        print(f"❌ 驗證過程中發生錯誤: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Airflow DAG 依賴檢查腳本
檢查所有 DAG 文件中使用的外部依賴是否在 requirements.txt 中聲明
"""
import os
import re
import sys
from pathlib import Path
from typing import Set, Dict, List


def extract_imports_from_file(file_path: Path) -> Set[str]:
    """從 Python 文件中提取導入的模組"""
    imports = set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 匹配 import 語句
        import_patterns = [
            r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # import module
            r'^from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import',  # from module import ...
        ]

        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('#') or not line:
                continue

            for pattern in import_patterns:
                match = re.match(pattern, line)
                if match:
                    module_name = match.group(1)
                    # 排除標準庫和相對導入
                    if not is_standard_library(module_name) and not is_relative_import(module_name):
                        imports.add(module_name)

    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")

    return imports


def is_standard_library(module_name: str) -> bool:
    """檢查是否為 Python 標準庫模組"""
    standard_libs = {
        'os', 'sys', 'datetime', 'time', 'json', 'uuid', 'logging', 're',
        'pathlib', 'typing', 'collections', 'functools', 'itertools',
        'subprocess', 'urllib', 'http', 'email', 'xml', 'html', 'csv',
        'sqlite3', 'pickle', 'hashlib', 'base64', 'shutil', 'tempfile',
        'glob', 'fnmatch', 'math', 'random', 'statistics', 'decimal',
        'fractions', 'operator', 'copy', 'pprint', 'reprlib', 'enum',
        'contextlib', 'weakref', 'gc', 'inspect', 'dis', 'traceback'
    }
    return module_name in standard_libs


def is_relative_import(module_name: str) -> bool:
    """檢查是否為相對導入或項目內部模組"""
    return module_name.startswith('.') or module_name in ['airflow', 'common']


def load_requirements(requirements_file: Path) -> Set[str]:
    """從 requirements.txt 載入已聲明的依賴"""
    requirements = set()

    if not requirements_file.exists():
        return requirements

    try:
        with open(requirements_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 提取包名（移除版本號和其他修飾符）
                    package_name = re.split(r'[=<>!]', line)[0].strip()
                    if package_name:
                        requirements.add(package_name)
    except Exception as e:
        print(f"Error reading requirements file: {e}")

    return requirements


def get_package_mapping() -> Dict[str, str]:
    """
    返回導入名稱到包名的映射
    有些包的導入名稱和安裝名稱不同
    """
    return {
        'redis': 'redis',
        'requests': 'requests',
        'pendulum': 'pendulum',
        'pytest': 'pytest',
        'black': 'black',
        'flake8': 'flake8',
        'psycopg2': 'psycopg2-binary',
        'sqlalchemy': 'SQLAlchemy',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'yfinance': 'yfinance',
        'matplotlib': 'matplotlib',
        'seaborn': 'seaborn',
        'sklearn': 'scikit-learn',
        'cv2': 'opencv-python',
        'PIL': 'Pillow',
        'yaml': 'PyYAML',
    }


def check_airflow_dependencies(airflow_dir: Path) -> Dict[str, any]:
    """檢查 Airflow DAG 依賴"""
    print("🔍 檢查 Airflow DAG 依賴...")

    # 查找所有 Python 文件
    python_files = list(airflow_dir.rglob("*.py"))
    print(f"找到 {len(python_files)} 個 Python 文件")

    # 提取所有導入
    all_imports = set()
    file_imports = {}

    for py_file in python_files:
        if py_file.name.startswith('__'):
            continue

        imports = extract_imports_from_file(py_file)
        if imports:
            file_imports[str(py_file.relative_to(airflow_dir))] = imports
            all_imports.update(imports)

    # 載入 requirements.txt
    requirements_file = airflow_dir / "requirements.txt"
    declared_requirements = load_requirements(requirements_file)

    # 檢查缺失的依賴
    package_mapping = get_package_mapping()
    missing_deps = set()

    for import_name in all_imports:
        package_name = package_mapping.get(import_name, import_name)
        if package_name not in declared_requirements:
            missing_deps.add((import_name, package_name))

    return {
        'python_files': len(python_files),
        'all_imports': all_imports,
        'file_imports': file_imports,
        'declared_requirements': declared_requirements,
        'missing_dependencies': missing_deps,
        'requirements_file_exists': requirements_file.exists()
    }


def generate_dependency_report(results: Dict[str, any]) -> None:
    """生成依賴報告"""
    print("\n" + "="*60)
    print("📊 Airflow DAG 依賴分析報告")
    print("="*60)

    print(f"\n📁 掃描的 Python 文件數量: {results['python_files']}")
    print(f"📦 發現的外部導入數量: {len(results['all_imports'])}")
    print(f"📋 requirements.txt 中的依賴數量: {len(results['declared_requirements'])}")

    if not results['requirements_file_exists']:
        print("\n❌ requirements.txt 文件不存在！")
        return

    print("\n📦 所有外部導入:")
    for imp in sorted(results['all_imports']):
        print(f"  - {imp}")

    print("\n📋 已聲明的依賴:")
    for dep in sorted(results['declared_requirements']):
        print(f"  - {dep}")

    if results['missing_dependencies']:
        print(f"\n❌ 缺失的依賴 ({len(results['missing_dependencies'])} 個):")
        for import_name, package_name in sorted(results['missing_dependencies']):
            print(f"  - {import_name} (需要安裝: {package_name})")

        print("\n🔧 建議在 requirements.txt 中添加:")
        for import_name, package_name in sorted(results['missing_dependencies']):
            print(f"  {package_name}")
    else:
        print("\n✅ 所有依賴都已正確聲明！")

    print("\n📂 各文件的導入詳情:")
    for file_path, imports in results['file_imports'].items():
        if imports:
            print(f"\n  📄 {file_path}:")
            for imp in sorted(imports):
                status = "❌" if any(imp == missing[0] for missing in results['missing_dependencies']) else "✅"
                print(f"    {status} {imp}")


def suggest_fixes(results: Dict[str, any]) -> None:
    """建議修復方案"""
    if not results['missing_dependencies']:
        return

    print("\n" + "="*60)
    print("🔧 修復建議")
    print("="*60)

    requirements_additions = []
    for import_name, package_name in sorted(results['missing_dependencies']):
        # 查找常用版本
        version_suggestions = {
            'redis': '5.0.1',
            'requests': '2.31.0',
            'pendulum': '2.1.2',
            'pytest': '7.4.0',
            'psycopg2-binary': '2.9.7',
            'SQLAlchemy': '2.0.23',
        }

        version = version_suggestions.get(package_name, 'latest')
        if version == 'latest':
            requirements_additions.append(package_name)
        else:
            requirements_additions.append(f"{package_name}=={version}")

    print("1. 更新 airflow/requirements.txt，添加以下依賴:")
    for req in requirements_additions:
        print(f"   {req}")

    print("\n2. 重新構建 Docker 映像:")
    print("   docker-compose build airflow")

    print("\n3. 重啟 Airflow 服務:")
    print("   docker-compose restart airflow")


def main():
    """主函數"""
    # 確定 Airflow 目錄
    script_dir = Path(__file__).parent
    airflow_dir = script_dir.parent

    if not airflow_dir.exists():
        print(f"❌ Airflow 目錄不存在: {airflow_dir}")
        sys.exit(1)

    print(f"🏗️  檢查 Airflow 目錄: {airflow_dir}")

    # 執行依賴檢查
    try:
        results = check_airflow_dependencies(airflow_dir)
        generate_dependency_report(results)
        suggest_fixes(results)

        # 根據結果設置退出碼
        if results['missing_dependencies']:
            print(f"\n⚠️  發現 {len(results['missing_dependencies'])} 個缺失的依賴")
            sys.exit(1)
        else:
            print("\n🎉 所有依賴檢查通過！")
            sys.exit(0)

    except Exception as e:
        print(f"❌ 檢查過程中發生錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
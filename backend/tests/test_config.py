#!/usr/bin/env python3
"""
測試配置文件
"""
import sys
from pathlib import Path

# 獲取測試目錄的絕對路徑
TEST_DIR = Path(__file__).parent

# 獲取後端項目根目錄（相對於測試目錄的上級）
BACKEND_ROOT = TEST_DIR.parent

# 獲取項目根目錄（相對於後端目錄的上級）
PROJECT_ROOT = BACKEND_ROOT.parent

def setup_test_path():
    """設置測試環境的Python路徑"""
    backend_path = str(BACKEND_ROOT)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

def get_test_data_dir():
    """獲取測試數據目錄"""
    return TEST_DIR / "data"

def get_backend_root():
    """獲取後端根目錄"""
    return BACKEND_ROOT

def get_project_root():
    """獲取項目根目錄"""
    return PROJECT_ROOT
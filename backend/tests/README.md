# 測試框架使用指南

## 概覽

本測試框架提供了統一的路徑配置管理和完整的測試套件，支持單元測試和整合測試。

## 目錄結構

```
tests/
├── README.md                    # 本文件
├── test_config.py              # 測試路徑配置
├── run_tests.py                # 統一測試執行器
├── coverage_summary.md         # 測試覆蓋率報告
└── unit/                       # 單元測試目錄
    ├── test_api_*.py           # API層測試
    ├── test_core_*.py          # 核心配置測試
    ├── test_*_manager.py       # 服務管理測試
    ├── test_buy_sell_signals.py # 買賣點標示測試
    ├── test_trading_signal_detector.py # 交易信號偵測測試
    ├── test_indicator_storage.py # 指標存儲測試
    ├── test_technical_analysis_integration.py # 技術分析整合測試
    ├── test_scheduler.py       # 排程器測試
    ├── test_storage.py         # 存儲服務測試
    ├── test_sync.py           # 同步服務測試
    └── ...
```

## 路徑配置系統

### 配置文件 (`test_config.py`)

提供統一的路徑管理功能：

```python
from test_config import setup_test_path, get_backend_root, get_project_root

# 設置測試環境路徑
setup_test_path()

# 獲取路徑信息
backend_root = get_backend_root()
project_root = get_project_root()
```

### 新建測試文件模板

創建新測試文件時，請使用以下模板：

```python
#!/usr/bin/env python3
"""
你的測試文件說明
"""
import sys
import unittest
from pathlib import Path

# 添加測試配置路徑（相對於當前文件）
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_config import setup_test_path

# 設置測試環境路徑
setup_test_path()

# 現在可以安全地導入項目模塊
from services.your_service import YourService


class YourTestCase(unittest.TestCase):
    """你的測試類"""

    def setUp(self):
        """測試設置"""
        pass

    def test_your_function(self):
        """測試你的功能"""
        pass


if __name__ == "__main__":
    unittest.main()
```

## 運行測試

### 運行所有測試

```bash
# 在 backend 目錄下執行
python3 tests/run_tests.py
```

### 運行單個測試文件

```bash
# 運行特定測試文件
python3 tests/unit/test_scheduler.py
```

### 運行特定測試文件

```bash
# 運行核心配置測試
python3 tests/unit/test_core_config.py

# 運行API測試
python3 tests/unit/test_api_signals.py
```

## 測試規範

### 1. 命名規範

- 測試文件：`test_<模塊名>.py`
- 測試類：`Test<功能名>`
- 測試方法：`test_<具體功能>`

### 2. 路徑設置

- **必須**使用 `test_config.py` 進行路徑配置
- **禁止**使用絕對路徑
- **推薦**使用相對路徑和 `Path` 對象

### 3. 測試結構

```python
class TestYourService(unittest.TestCase):
    """服務測試"""

    def setUp(self):
        """每個測試前的設置"""
        pass

    def tearDown(self):
        """每個測試後的清理"""
        pass

    def test_normal_case(self):
        """測試正常情況"""
        pass

    def test_edge_case(self):
        """測試邊界情況"""
        pass

    def test_error_case(self):
        """測試錯誤情況"""
        pass
```

### 4. Mock使用

```python
from unittest.mock import Mock, AsyncMock, patch

# 同步Mock
with patch('services.your_service.external_dependency') as mock_dep:
    mock_dep.return_value = expected_result
    result = your_function()

# 異步Mock
@patch('services.your_service.async_dependency')
async def test_async_function(self, mock_async_dep):
    mock_async_dep.return_value = expected_result
    result = await your_async_function()
```

## 最佳實踐

### 1. 測試隔離

- 每個測試方法應該獨立運行
- 使用 `setUp()` 和 `tearDown()` 管理測試狀態
- 適當使用 Mock 隔離外部依賴

### 2. 測試覆蓋

- 正常流程測試
- 邊界條件測試
- 錯誤處理測試
- 異步操作測試

### 3. 斷言使用

```python
# 基本斷言
self.assertEqual(actual, expected)
self.assertTrue(condition)
self.assertIsNotNone(value)

# 異常斷言
with self.assertRaises(ValueError):
    risky_function()

# 近似值斷言
self.assertAlmostEqual(actual, expected, places=2)
```

### 4. 異步測試

```python
import asyncio

class TestAsyncService(unittest.TestCase):

    async def test_async_method(self):
        """異步方法測試"""
        result = await async_function()
        self.assertEqual(result, expected)

# 運行異步測試
async def run_async_tests():
    test = TestAsyncService()
    await test.test_async_method()

if __name__ == "__main__":
    asyncio.run(run_async_tests())
```

## 故障排除

### 常見問題

1. **ModuleNotFoundError**:
   - 檢查是否正確使用了 `test_config.py`
   - 確認路徑設置是否正確

2. **路徑問題**:
   - 使用相對路徑和 `Path` 對象
   - 避免硬編碼絕對路徑

3. **依賴問題**:
   - 確保所需的依賴包已安裝
   - 適當使用 Mock 隔離外部依賴

### 調試技巧

```python
# 打印路徑信息
from test_config import get_backend_root, get_project_root
print(f"Backend root: {get_backend_root()}")
print(f"Project root: {get_project_root()}")

# 打印 sys.path
import sys
print("Python path:", sys.path)
```

## 貢獻指南

1. 新增測試文件時使用提供的模板
2. 確保所有測試都能獨立運行
3. 遵循命名規範和代碼風格
4. 為複雜功能添加適當的測試文檔
5. 運行完整測試套件確保無回歸問題
# 前端修復測試指南

## 測試概述

這份指南說明如何運行和驗證前端修復的測試，確保所有修復都按預期工作。

## 🧪 新增的測試文件

### 1. WebSocket Hooks 測試
**文件**: `src/hooks/__tests__/useWebSocket.test.tsx`

**測試內容**:
- ✅ 事件監聽器的正確註冊和清理
- ✅ 依賴數組修復後的重新訂閱行為
- ✅ 連接狀態管理
- ✅ 錯誤處理
- ✅ 股票訂閱和多股票訂閱

**關鍵測試場景**:
```typescript
// 測試依賴變化時的重新註冊
it('事件處理器應該在dispatch變化時重新創建', () => {
  // 驗證依賴修復後的行為
});

// 測試股票訂閱的依賴管理
it('handleWelcome應該在stockId或symbol變化時重新創建', () => {
  // 驗證 useCallback 和依賴數組的修復
});
```

### 2. useStocks 優化測試
**文件**: `src/hooks/__tests__/useStocks.test.tsx` (擴展版)

**新增測試內容**:
- ✅ `useBackfillStockData` 緩存失效優化
- ✅ 精確 queryKey vs predicate 函數對比
- ✅ 不同股票和參數的緩存失效
- ✅ 性能對比測試

**關鍵測試場景**:
```typescript
// 測試優化後的緩存失效
it('應該使用精確的 queryKey 進行緩存失效而不是 predicate', async () => {
  // 驗證不使用 predicate 函數
  invalidateCallsArgs.forEach(([args]) => {
    expect(args).not.toHaveProperty('predicate');
  });
});
```

### 3. Layout 組件測試
**文件**: `src/app/__tests__/layout.test.tsx`

**測試內容**:
- ✅ 基本佈局結構
- ✅ ErrorBoundary 包裝驗證
- ✅ 所有導航連結（包括系統狀態）
- ✅ WebSocket 狀態指示器
- ✅ 組件集成測試
- ✅ 與 `layout 2.tsx` 缺失功能對比

**關鍵驗證**:
```typescript
// 驗證保留的是功能完整的版本
it('應該包含系統狀態導航連結（layout 2.tsx 中缺失）', () => {
  expect(screen.getByText('系統狀態')).toBeInTheDocument();
});
```

## 🚀 運行測試

### 方法1：使用專用測試腳本
```bash
# 在前端目錄中運行
cd frontend
node scripts/test-fixes.js
```

### 方法2：使用 Jest 直接運行
```bash
# 運行 WebSocket 測試
npm test -- src/hooks/__tests__/useWebSocket.test.tsx

# 運行 useStocks 測試
npm test -- src/hooks/__tests__/useStocks.test.tsx

# 運行 Layout 測試
npm test -- src/app/__tests__/layout.test.tsx

# 運行所有新增測試
npm test -- --testPathPattern="(useWebSocket|layout)\.test\.tsx$"
```

### 方法3：使用覆蓋率測試
```bash
# 生成覆蓋率報告
npm test -- --coverage --testPathPattern="(useWebSocket|useStocks|layout)\.test\.tsx$"
```

## 📊 預期測試結果

### 成功指標
- **WebSocket Tests**: 所有 19 個測試通過
- **useStocks Tests**: 所有 15 個測試通過（包括新增的 8 個優化測試）
- **Layout Tests**: 所有 12 個測試通過

### 覆蓋率目標
- **useWebSocket.ts**: > 90% 行覆蓋率
- **useStocks.ts**: > 85% 行覆蓋率
- **layout.tsx**: > 80% 行覆蓋率

## 🔍 測試驗證點

### WebSocket 依賴修復驗證
```bash
# 應該看到這些測試通過：
✅ 應該正確註冊和清理事件監聽器
✅ 事件處理器應該在dispatch變化時重新創建
✅ handleWelcome應該在stockId或symbol變化時重新創建
```

### React Query 優化驗證
```bash
# 應該看到這些測試通過：
✅ 應該使用精確的 queryKey 進行緩存失效而不是 predicate
✅ 性能對比：新方法 vs 舊方法
✅ 應該正確處理不同股票和參數的緩存失效
```

### Layout 功能完整性驗證
```bash
# 應該看到這些測試通過：
✅ 應該包含 ErrorBoundary（layout 2.tsx 中缺失）
✅ 應該包含系統狀態導航連結（layout 2.tsx 中缺失）
✅ 應該驗證清理重複文件的決策是正確的
```

## 🐛 常見測試問題和解決方案

### 1. Mock 問題
如果遇到 mock 相關錯誤：
```bash
# 清除 Jest 緩存
npm test -- --clearCache

# 或者重新安裝依賴
npm install
```

### 2. 依賴問題
確保安裝了必要的測試依賴：
```json
{
  "devDependencies": {
    "@testing-library/react": "^13.x.x",
    "@testing-library/jest-dom": "^5.x.x",
    "@testing-library/user-event": "^14.x.x",
    "jest": "^29.x.x",
    "jest-environment-jsdom": "^29.x.x"
  }
}
```

### 3. 路徑問題
如果遇到模組解析問題，檢查 `jest.config.js`：
```javascript
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1'
  }
};
```

## 📈 性能基準測試

運行性能對比測試來驗證優化效果：

```bash
# 運行性能測試
npm test -- src/hooks/__tests__/useStocks.test.tsx --verbose

# 查看控制台輸出中的性能數據
# 應該看到類似的輸出：
# "優化後的緩存失效執行時間: X.XXms"
```

## 🎯 測試最佳實踐

### 1. 隔離性
- 每個測試都有獨立的 mock 設置
- 使用 `beforeEach` 清理狀態

### 2. 可讀性
- 測試名稱使用中文，清楚表達測試意圖
- 包含詳細的註釋說明

### 3. 完整性
- 測試正常情況和錯誤情況
- 驗證邊界條件和依賴變化

## 🔄 持續集成

建議在 CI/CD 流水線中加入這些測試：

```yaml
# .github/workflows/frontend-tests.yml
- name: Run Frontend Fix Tests
  run: |
    cd frontend
    npm test -- --testPathPattern="(useWebSocket|useStocks|layout)\.test\.tsx$" --coverage
```

## 📝 測試報告解讀

運行測試後，注意以下關鍵指標：

### 通過率
- 目標：100% 測試通過
- 如果有失敗，檢查錯誤消息並修復

### 覆蓋率
- **Line Coverage**: > 85%
- **Function Coverage**: > 90%
- **Branch Coverage**: > 80%

### 性能指標
- 優化後的緩存失效應該更快
- WebSocket 重新訂閱應該正確觸發

## 🎉 驗證完成

當所有測試通過時，表示：

1. ✅ **WebSocket 依賴問題已修復** - 事件監聽器正確管理
2. ✅ **React Query 優化已生效** - 緩存失效更精確高效
3. ✅ **Layout 組件功能完整** - 保留了最完整的版本
4. ✅ **修復沒有引入新問題** - 向後兼容性良好

這些測試為前端修復提供了堅實的質量保證！
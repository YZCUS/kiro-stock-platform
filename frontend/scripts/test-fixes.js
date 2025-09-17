#!/usr/bin/env node
/**
 * 前端修復測試執行器
 *
 * 專門運行針對修復問題的測試
 */
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

console.log('🧪 執行前端修復測試...\n');

// 測試配置
const testConfig = {
  // WebSocket hooks 測試
  websocket: {
    name: 'WebSocket Hooks 測試',
    path: 'src/hooks/__tests__/useWebSocket.test.tsx',
    description: '測試 WebSocket 依賴修復後的行為'
  },

  // useStocks 優化測試
  useStocks: {
    name: 'useStocks 優化測試',
    path: 'src/hooks/__tests__/useStocks.test.tsx',
    description: '測試 React Query 緩存失效優化'
  },

  // Layout 組件測試
  layout: {
    name: 'Layout 組件測試',
    path: 'src/app/__tests__/layout.test.tsx',
    description: '測試清理重複文件後的 Layout 組件'
  }
};

/**
 * 運行特定測試文件
 */
function runTest(testKey, config) {
  console.log(`\n📋 ${config.name}`);
  console.log(`📝 ${config.description}`);
  console.log('─'.repeat(60));

  try {
    // 檢查測試文件是否存在
    const testPath = path.join(process.cwd(), config.path);
    if (!fs.existsSync(testPath)) {
      console.log(`❌ 測試文件不存在: ${config.path}`);
      return false;
    }

    // 執行測試
    const command = `npx jest "${config.path}" --verbose --coverage --collectCoverageFrom="${config.path.replace('__tests__/', '').replace('.test.tsx', '.tsx')}"`;

    const result = execSync(command, {
      stdio: 'pipe',
      encoding: 'utf-8',
      cwd: process.cwd()
    });

    console.log(result);
    console.log(`✅ ${config.name} - 通過`);
    return true;

  } catch (error) {
    console.log(`❌ ${config.name} - 失敗`);
    console.log('錯誤輸出:');
    console.log(error.stdout || error.stderr || error.message);
    return false;
  }
}

/**
 * 運行所有相關測試
 */
function runAllTests() {
  console.log('🎯 針對前端修復的測試執行');
  console.log('=' * 60);

  const results = {};

  // 執行所有測試
  for (const [key, config] of Object.entries(testConfig)) {
    results[key] = runTest(key, config);
  }

  return results;
}

/**
 * 生成測試報告
 */
function generateReport(results) {
  console.log('\n' + '='.repeat(60));
  console.log('📊 測試報告');
  console.log('='.repeat(60));

  const passed = Object.values(results).filter(Boolean).length;
  const total = Object.keys(results).length;
  const percentage = Math.round((passed / total) * 100);

  console.log(`\n總測試套件: ${total}`);
  console.log(`通過: ${passed}`);
  console.log(`失敗: ${total - passed}`);
  console.log(`通過率: ${percentage}%\n`);

  // 詳細結果
  for (const [key, config] of Object.entries(testConfig)) {
    const status = results[key] ? '✅ 通過' : '❌ 失敗';
    console.log(`  ${config.name}: ${status}`);
  }

  if (passed === total) {
    console.log('\n🎉 所有前端修復測試都通過了！');
    console.log('\n✨ 修復效果驗證：');
    console.log('  • WebSocket 依賴問題已修復');
    console.log('  • React Query 緩存優化已生效');
    console.log('  • Layout 組件功能完整');
  } else {
    console.log('\n⚠️  部分測試失敗，請檢查上述錯誤信息');
  }

  return passed === total;
}

/**
 * 生成覆蓋率摘要
 */
function generateCoverageSummary() {
  console.log('\n' + '='.repeat(60));
  console.log('📈 測試覆蓋率摘要');
  console.log('='.repeat(60));

  try {
    // 執行整體覆蓋率測試
    const coverageCommand = `npx jest --coverage --testPathPattern="(useWebSocket|useStocks|layout)\\.test\\.(tsx|ts)$" --silent`;

    const coverageResult = execSync(coverageCommand, {
      stdio: 'pipe',
      encoding: 'utf-8',
      cwd: process.cwd()
    });

    // 提取覆蓋率信息
    const coverageLines = coverageResult.split('\n');
    const summaryStartIndex = coverageLines.findIndex(line => line.includes('Coverage summary'));

    if (summaryStartIndex !== -1) {
      console.log('\n修復相關文件的覆蓋率:');
      for (let i = summaryStartIndex; i < Math.min(summaryStartIndex + 10, coverageLines.length); i++) {
        if (coverageLines[i].trim()) {
          console.log(coverageLines[i]);
        }
      }
    }

  } catch (error) {
    console.log('無法生成覆蓋率摘要:', error.message);
  }
}

/**
 * 主執行函數
 */
function main() {
  try {
    // 檢查是否在正確的目錄中
    if (!fs.existsSync('package.json')) {
      console.error('❌ 請在前端項目根目錄中運行此腳本');
      process.exit(1);
    }

    // 檢查 Jest 配置
    const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf-8'));
    if (!packageJson.devDependencies?.jest && !packageJson.dependencies?.jest) {
      console.warn('⚠️  未檢測到 Jest，請確保已安裝測試依賴');
    }

    // 運行測試
    const results = runAllTests();

    // 生成報告
    const allPassed = generateReport(results);

    // 生成覆蓋率摘要
    generateCoverageSummary();

    // 退出代碼
    process.exit(allPassed ? 0 : 1);

  } catch (error) {
    console.error('❌ 執行測試時發生錯誤:', error.message);
    process.exit(1);
  }
}

// 如果直接執行此腳本
if (require.main === module) {
  main();
}

module.exports = {
  runTest,
  runAllTests,
  generateReport,
  testConfig
};
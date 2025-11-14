module.exports = {
  ci: {
    collect: {
      // 要測試的 URL
      url: [
        'http://localhost:3000/',                    // 首頁
        'http://localhost:3000/login',               // 登入頁
        'http://localhost:3000/register',            // 註冊頁
        'http://localhost:3000/stocks',              // 股票列表
        'http://localhost:3000/dashboard',           // 儀表板
        'http://localhost:3000/strategies',          // 策略頁面
      ],
      // 測試次數（取平均值）
      numberOfRuns: 3,
      // 啟動本地伺服器的配置
      startServerCommand: 'cd frontend && npm run build && npm start',
      startServerReadyPattern: 'Ready on',
      startServerReadyTimeout: 60000,
      // Chrome 啟動選項
      settings: {
        preset: 'desktop', // 或 'mobile'
        // Chrome flags
        chromeFlags: '--no-sandbox --disable-dev-shm-usage',
        // 禁用某些審計（如果需要）
        // skipAudits: ['uses-http2'],
      },
    },
    assert: {
      // 性能評分閾值
      assertions: {
        // 分類評分
        'categories:performance': ['error', { minScore: 0.8 }],  // 性能 >= 80
        'categories:accessibility': ['warn', { minScore: 0.85 }], // 無障礙性 >= 85
        'categories:best-practices': ['warn', { minScore: 0.9 }], // 最佳實踐 >= 90
        'categories:seo': ['warn', { minScore: 0.9 }],            // SEO >= 90

        // 核心 Web Vitals
        'first-contentful-paint': ['error', { maxNumericValue: 2000 }],      // FCP < 2s
        'largest-contentful-paint': ['error', { maxNumericValue: 2500 }],    // LCP < 2.5s
        'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],      // CLS < 0.1
        'total-blocking-time': ['warn', { maxNumericValue: 300 }],           // TBT < 300ms
        'speed-index': ['warn', { maxNumericValue: 3000 }],                  // SI < 3s
        'interactive': ['warn', { maxNumericValue: 3500 }],                  // TTI < 3.5s

        // 資源優化
        'unused-javascript': ['warn', { maxLength: 0 }],
        'unused-css-rules': ['warn', { maxLength: 0 }],
        'modern-image-formats': ['warn', { maxLength: 0 }],
        'uses-responsive-images': ['warn', { maxLength: 0 }],
        'offscreen-images': ['warn', { maxLength: 0 }],

        // 最佳實踐
        'uses-http2': 'off',  // 如果使用 HTTP/1.1 可以關閉
        'uses-long-cache-ttl': 'off',  // 開發環境可以關閉
      },
    },
    upload: {
      // 上傳結果到 Lighthouse CI Server (可選)
      target: 'temporary-public-storage',
      // 或使用自己的 LHCI Server
      // target: 'lhci',
      // serverBaseUrl: 'https://your-lhci-server.com',
      // token: process.env.LHCI_TOKEN,
    },
  },
};

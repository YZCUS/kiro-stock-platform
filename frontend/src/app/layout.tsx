/**
 * 根Layout組件
 */
import './globals.css';
import { Providers } from '../store/providers';
import Toast from '../components/ui/Toast';
import WebSocketStatus from '../components/ui/WebSocketStatus';
import ErrorBoundary from '../components/ErrorBoundary';

export const metadata = {
  title: '股票分析平台',
  description: '自動化股票數據收集與技術分析平台',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-TW">
      <body className="min-h-screen bg-gray-50">
        <ErrorBoundary>
          <Providers>
            {/* 導航列 */}
          <nav className="bg-white shadow-sm border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex items-center">
                  <a href="/" className="text-xl font-bold text-gray-900">
                    股票分析平台
                  </a>
                </div>
                <div className="flex items-center space-x-8">
                  <a
                    href="/"
                    className="text-gray-900 hover:text-gray-600 px-3 py-2 text-sm font-medium"
                  >
                    首頁
                  </a>
                  <a
                    href="/stocks"
                    className="text-gray-900 hover:text-gray-600 px-3 py-2 text-sm font-medium"
                  >
                    股票管理
                  </a>
                  <a
                    href="/charts"
                    className="text-gray-900 hover:text-gray-600 px-3 py-2 text-sm font-medium"
                  >
                    圖表分析
                  </a>
                  <a
                    href="/dashboard"
                    className="text-gray-900 hover:text-gray-600 px-3 py-2 text-sm font-medium"
                  >
                    即時儀表板
                  </a>
                  <a
                    href="/signals"
                    className="text-gray-900 hover:text-gray-600 px-3 py-2 text-sm font-medium"
                  >
                    交易信號
                  </a>
                  <a
                    href="/system"
                    className="text-gray-900 hover:text-gray-600 px-3 py-2 text-sm font-medium"
                  >
                    系統狀態
                  </a>

                  {/* WebSocket 狀態指示器 */}
                  <div className="border-l border-gray-300 pl-4">
                    <WebSocketStatus />
                  </div>
                </div>
              </div>
            </div>
          </nav>

          {/* 主內容 */}
          <main>
            {children}
          </main>

          {/* 頁腳 */}
          <footer className="bg-white border-t border-gray-200 mt-12">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <div className="text-center text-gray-600">
                <p>&copy; 2025 股票分析平台. 版權所有.</p>
              </div>
            </div>
          </footer>

            {/* Toast 通知 */}
            <Toast />
          </Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}
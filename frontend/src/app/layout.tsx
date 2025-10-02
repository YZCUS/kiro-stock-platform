/**
 * 根Layout組件 - Enhanced with shadcn/ui
 */
import './globals.css';
import Link from 'next/link';
import { Providers } from '../store/providers';
import Toast from '../components/ui/Toast';
import WebSocketStatus from '../components/ui/WebSocketStatus';
import ErrorBoundary from '../components/ErrorBoundary';
import { Button } from '@/components/ui/button';
import { BarChart3 } from 'lucide-react';

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
      <body className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        <ErrorBoundary>
          <Providers>
            {/* Navigation */}
            <nav className="bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-200 sticky top-0 z-50">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16">
                  <div className="flex items-center">
                    <Link href="/" className="flex items-center gap-2 text-xl font-bold text-gray-900 hover:text-blue-600 transition-colors">
                      <BarChart3 className="w-6 h-6" />
                      股票分析平台
                    </Link>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Button variant="ghost" size="sm" asChild>
                      <Link href="/">首頁</Link>
                    </Button>
                    <Button variant="ghost" size="sm" asChild>
                      <Link href="/stocks">股票管理</Link>
                    </Button>
                    <Button variant="ghost" size="sm" asChild>
                      <Link href="/charts">圖表分析</Link>
                    </Button>
                    <Button variant="ghost" size="sm" asChild>
                      <Link href="/dashboard">即時儀表板</Link>
                    </Button>
                    <Button variant="ghost" size="sm" asChild>
                      <Link href="/signals">交易信號</Link>
                    </Button>
                    <Button variant="ghost" size="sm" asChild>
                      <Link href="/system">系統狀態</Link>
                    </Button>

                    {/* WebSocket Status */}
                    <div className="border-l border-gray-300 ml-4 pl-4">
                      <WebSocketStatus />
                    </div>
                  </div>
                </div>
              </div>
            </nav>

            {/* Main Content */}
            <main className="min-h-[calc(100vh-8rem)]">
              {children}
            </main>

            {/* Footer */}
            <footer className="bg-white/80 backdrop-blur-md border-t border-gray-200 mt-12">
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
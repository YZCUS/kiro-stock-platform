/**
 * 根Layout組件 - Enhanced with shadcn/ui
 */
import './globals.css';
import { Providers } from '../store/providers';
import Toast from '../components/ui/Toast';
import ErrorBoundary from '../components/ErrorBoundary';
import Navigation from '../components/Navigation';
import AuthInit from '../components/AuthInit';

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
            <AuthInit />
            <Navigation />

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
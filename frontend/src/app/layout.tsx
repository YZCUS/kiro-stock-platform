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
      <body className="min-h-screen bg-white text-gray-950">
        <ErrorBoundary>
          <Providers>
            <AuthInit />
            <Navigation />

            <main className="min-h-[calc(100vh-7rem)] bg-gray-50/60">
              {children}
            </main>

            <footer className="border-t border-gray-200 bg-white">
              <div className="mx-auto max-w-7xl px-4 py-4 text-center text-sm text-gray-500 sm:px-6 lg:px-8">
                股票分析平台
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

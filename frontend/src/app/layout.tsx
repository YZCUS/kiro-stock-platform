/**
 * 根Layout組件 - Enhanced with shadcn/ui
 */
import "./globals.css";
import { Providers } from "../store/providers";
import Toast from "../components/ui/Toast";
import ErrorBoundary from "../components/ErrorBoundary";
import Navigation from "../components/Navigation";
import AuthInit from "../components/AuthInit";

export const metadata = {
  title: "股票分析平台",
  description: "自動化股票數據收集與技術分析平台",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-TW">
      <body className="min-h-screen overflow-x-hidden bg-background text-foreground">
        <ErrorBoundary>
          <Providers>
            <AuthInit />
            <Navigation />

            <main
              id="main-content"
              className="min-h-screen bg-background pt-16 lg:pl-64"
            >
              {children}
            </main>

            <Toast />
          </Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}

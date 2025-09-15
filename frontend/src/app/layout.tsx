import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Providers from '../components/Providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
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
            <body className={inter.className}>
                <Providers>
                    <div id="root">
                        {children}
                    </div>
                </Providers>
            </body>
        </html>
    );
}
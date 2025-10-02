import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '即時儀表板 | 股票分析平台',
  description: '即時監控股票市場動態，WebSocket 即時更新價格與技術指標',
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

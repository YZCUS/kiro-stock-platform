import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '股票管理 | 股票分析平台',
  description: '管理和監控台股與美股列表，追蹤股票即時資訊與歷史數據',
};

export default function StocksLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

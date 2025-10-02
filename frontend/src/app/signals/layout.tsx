import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '交易信號 | 股票分析平台',
  description: '監控股票交易信號，包含黃金交叉、死亡交叉等買賣點提示',
};

export default function SignalsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

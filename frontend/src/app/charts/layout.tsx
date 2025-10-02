import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '圖表分析 | 股票分析平台',
  description: '查看股票 K 線圖表、技術指標分析，包含 RSI、MACD、布林通道、KD 指標等',
};

export default function ChartsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

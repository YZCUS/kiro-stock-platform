import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '系統狀態 | 股票分析平台',
  description: '查看系統健康狀態、服務狀態與系統資源使用情況',
};

export default function SystemLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

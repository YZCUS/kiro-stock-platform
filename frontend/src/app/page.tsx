/**
 * 首頁 - Dynamic Client Component with real-time data
 */
import React from 'react';
import type { Metadata } from 'next';
import HomePage from '@/components/Home/HomePage';

export const metadata: Metadata = {
  title: '首頁 | 股票分析平台',
  description: '自動化股票數據收集與技術分析平台 - 支援台股和美股，提供 RSI、MACD、布林通道等技術指標分析',
};

export default function Page() {
  return <HomePage />;
}
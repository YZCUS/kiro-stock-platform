/**
 * 首頁
 */
'use client';

import React from 'react';

export default function HomePage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          股票分析平台
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          自動化股票數據收集與技術分析平台
        </p>
      </div>

      {/* 功能卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div className="bg-white shadow rounded-lg p-6">
          <div className="text-center">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">自動數據收集</h3>
            <p className="text-gray-600">
              每日自動從Yahoo Finance收集台股和美股數據
            </p>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="text-center">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">技術指標分析</h3>
            <p className="text-gray-600">
              RSI、MACD、布林通道等多種技術指標計算
            </p>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="text-center">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5v-5zM9 17h5v5l-5-5zM7 7h.01M7 3a4 4 0 000 8v0a1 1 0 001 1h2.586l4.707 4.707C16.077 17.492 17 16.92 17 16V4c0-.92-.923-1.492-1.707-.707L11.586 7H9a1 1 0 00-1 1v0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">交易信號偵測</h3>
            <p className="text-gray-600">
              自動偵測黃金交叉、死亡交叉等交易信號
            </p>
          </div>
        </div>
      </div>

      {/* 系統狀態 */}
      <div className="bg-white shadow rounded-lg p-6 mb-8">
        <h2 className="text-lg font-medium text-gray-900 mb-4">系統狀態</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <span className="text-gray-600">後端 API</span>
            <span className="flex items-center text-green-600">
              <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
              運行中
            </span>
          </div>
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <span className="text-gray-600">資料庫</span>
            <span className="flex items-center text-green-600">
              <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
              已連接
            </span>
          </div>
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <span className="text-gray-600">WebSocket</span>
            <span className="flex items-center text-green-600">
              <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
              已連接
            </span>
          </div>
        </div>
      </div>

      {/* 快速統計 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-8 w-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">追蹤股票</p>
              <p className="text-2xl font-bold text-gray-900">12</p>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-8 w-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">技術指標</p>
              <p className="text-2xl font-bold text-gray-900">6</p>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-8 w-8 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5v-5zM9 17h5v5l-5-5zM7 7h.01M7 3a4 4 0 000 8v0a1 1 0 001 1h2.586l4.707 4.707C16.077 17.492 17 16.92 17 16V4c0-.92-.923-1.492-1.707-.707L11.586 7H9a1 1 0 00-1 1v0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">今日信號</p>
              <p className="text-2xl font-bold text-gray-900">3</p>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-8 w-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">數據更新</p>
              <p className="text-2xl font-bold text-gray-900">即時</p>
            </div>
          </div>
        </div>
      </div>

      {/* 導航連結 */}
      <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
        <a
          href="/stocks"
          className="block bg-white shadow hover:shadow-md transition-shadow rounded-lg p-6 text-center"
        >
          <h3 className="text-lg font-medium text-gray-900 mb-2">股票管理</h3>
          <p className="text-gray-600">管理和監控股票列表</p>
        </a>

        <a
          href="/charts"
          className="block bg-white shadow hover:shadow-md transition-shadow rounded-lg p-6 text-center"
        >
          <h3 className="text-lg font-medium text-gray-900 mb-2">圖表分析</h3>
          <p className="text-gray-600">查看K線圖表和技術指標</p>
        </a>

        <a
          href="/signals"
          className="block bg-white shadow hover:shadow-md transition-shadow rounded-lg p-6 text-center"
        >
          <h3 className="text-lg font-medium text-gray-900 mb-2">交易信號</h3>
          <p className="text-gray-600">監控交易信號和買賣點</p>
        </a>
      </div>
    </div>
  );
}
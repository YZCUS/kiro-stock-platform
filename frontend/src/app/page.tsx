'use client';

import { Layout } from '../components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui';
import { BarChart3, TrendingUp, Bell, Activity } from 'lucide-react';

export default function HomePage() {
    return (
        <Layout>
            <div className="space-y-6">
                {/* Header */}
                <div className="text-center">
                    <h1 className="text-4xl font-bold text-gray-900 mb-4">
                        股票分析平台
                    </h1>
                    <p className="text-xl text-gray-600 mb-8">
                        自動化股票數據收集與技術分析平台
                    </p>
                </div>

                {/* Feature Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <Card>
                        <CardContent>
                            <div className="text-center">
                                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                                    <Activity className="w-6 h-6 text-blue-600" />
                                </div>
                                <CardTitle className="mb-2">自動數據收集</CardTitle>
                                <p className="text-gray-600">
                                    每日自動從Yahoo Finance收集台股和美股數據
                                </p>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent>
                            <div className="text-center">
                                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                                    <BarChart3 className="w-6 h-6 text-green-600" />
                                </div>
                                <CardTitle className="mb-2">技術指標分析</CardTitle>
                                <p className="text-gray-600">
                                    RSI、MACD、布林通道等多種技術指標計算
                                </p>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent>
                            <div className="text-center">
                                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                                    <Bell className="w-6 h-6 text-purple-600" />
                                </div>
                                <CardTitle className="mb-2">交易信號偵測</CardTitle>
                                <p className="text-gray-600">
                                    自動偵測黃金交叉、死亡交叉等交易信號
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* System Status */}
                <Card>
                    <CardHeader>
                        <CardTitle>系統狀態</CardTitle>
                    </CardHeader>
                    <CardContent>
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
                    </CardContent>
                </Card>

                {/* Quick Stats */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <Card>
                        <CardContent>
                            <div className="flex items-center">
                                <TrendingUp className="h-8 w-8 text-blue-600" />
                                <div className="ml-4">
                                    <p className="text-sm font-medium text-gray-600">追蹤股票</p>
                                    <p className="text-2xl font-bold text-gray-900">12</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent>
                            <div className="flex items-center">
                                <BarChart3 className="h-8 w-8 text-green-600" />
                                <div className="ml-4">
                                    <p className="text-sm font-medium text-gray-600">技術指標</p>
                                    <p className="text-2xl font-bold text-gray-900">6</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent>
                            <div className="flex items-center">
                                <Bell className="h-8 w-8 text-orange-600" />
                                <div className="ml-4">
                                    <p className="text-sm font-medium text-gray-600">今日信號</p>
                                    <p className="text-2xl font-bold text-gray-900">3</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent>
                            <div className="flex items-center">
                                <Activity className="h-8 w-8 text-purple-600" />
                                <div className="ml-4">
                                    <p className="text-sm font-medium text-gray-600">數據更新</p>
                                    <p className="text-2xl font-bold text-gray-900">即時</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </Layout>
    );
}
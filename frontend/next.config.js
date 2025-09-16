/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,

  // 禁用靜態優化避免SSR問題
  output: 'standalone',

  // 環境變數配置
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
  },

  // 圖片優化配置
  images: {
    domains: ['localhost'],
  },

  // 實驗性功能
  experimental: {
    // Future experimental features can be added here
  },

  // Webpack 配置
  webpack: (config, { isServer }) => {
    // 客戶端特定配置
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
      };
    }

    return config;
  },
};

module.exports = nextConfig;
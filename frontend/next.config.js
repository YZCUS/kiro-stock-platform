/** @type {import('next').NextConfig} */
const staticAssetCacheControl =
  process.env.NODE_ENV === 'production'
    ? 'public, max-age=31536000, immutable'
    : 'no-store, must-revalidate';

const devDocumentCacheHeaders =
  process.env.NODE_ENV === 'production'
    ? []
    : [
        {
          key: 'Cache-Control',
          value: 'no-store, no-cache, must-revalidate, proxy-revalidate',
        },
        {
          key: 'Pragma',
          value: 'no-cache',
        },
        {
          key: 'Expires',
          value: '0',
        },
      ];

const apiRewriteBaseUrl =
  process.env.NEXT_PUBLIC_API_URL === 'same-origin'
    ? process.env.INTERNAL_API_BASE_URL || 'http://localhost:8000'
    : process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const nextConfig = {
  // Enable static optimization
  output: 'standalone',

  // Build optimization
  experimental: {
    // Enable modern builds for better performance
    esmExternals: true,
    // 優化特定包的導入（減少 bundle 大小）
    optimizePackageImports: ['lucide-react', '@tanstack/react-query'],
  },

  // Performance optimizations
  compiler: {
    // Remove console logs in production
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error'],
    } : false,
  },

  // Image optimization
  images: {
    domains: ['localhost'],
    formats: ['image/webp', 'image/avif'],
    minimumCacheTTL: 3600, // 1 hour
  },

  // Headers for security and caching
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
      ...(devDocumentCacheHeaders.length > 0
        ? [
            {
              source: '/:path((?!_next/static|static).*)',
              headers: devDocumentCacheHeaders,
            },
          ]
        : []),
      {
        source: '/static/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: staticAssetCacheControl,
          },
        ],
      },
      {
        source: '/_next/static/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: staticAssetCacheControl,
          },
        ],
      },
    ];
  },

  // Compression
  compress: true,

  // Build-time environment variables
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },

  // Webpack configuration
  webpack: (config, { buildId, dev, isServer, defaultLoaders, nextRuntime, webpack }) => {
    // Add path alias resolution for @/ imports
    const path = require('path');
    config.resolve.alias['@'] = path.resolve(__dirname, 'src');

    // Production optimizations
    if (!dev) {
      // Enable webpack bundle analyzer in production (when env var is set)
      if (process.env.ANALYZE === 'true') {
        const BundleAnalyzerPlugin = require('@next/bundle-analyzer')({
          enabled: true,
        });
        config.plugins.push(new BundleAnalyzerPlugin());
      }

      // Split chunks for better caching
      config.optimization.splitChunks = {
        chunks: 'all',
        cacheGroups: {
          default: {
            minChunks: 1,
            priority: -20,
            reuseExistingChunk: true,
          },
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            priority: -10,
            chunks: 'all',
          },
          react: {
            test: /[\\/]node_modules[\\/](react|react-dom)[\\/]/,
            name: 'react',
            priority: 10,
            chunks: 'all',
          },
          charts: {
            test: /[\\/]node_modules[\\/](lightweight-charts)[\\/]/,
            name: 'charts',
            priority: 10,
            chunks: 'all',
          },
        },
      };
    }

    return config;
  },

  // Redirects
  async redirects() {
    return [
      {
        source: '/home',
        destination: '/',
        permanent: true,
      },
    ];
  },

  // Rewrites for API proxy (if needed)
  async rewrites() {
    return [
      {
        source: '/api/proxy/:path*',
        destination: `${apiRewriteBaseUrl}/:path*`,
      },
    ];
  },

  // TypeScript configuration
  typescript: {
    // Disable type checking during build (should be done in CI/CD)
    ignoreBuildErrors: false,
  },

  // ESLint configuration
  eslint: {
    // Disable ESLint during build (should be done in CI/CD)
    ignoreDuringBuilds: false,
  },

  // Power pack features
  poweredByHeader: false,

  // React configuration
  reactStrictMode: true,

  // 生產環境優化
  productionBrowserSourceMaps: false, // 禁用生產環境 source maps
};

module.exports = nextConfig;

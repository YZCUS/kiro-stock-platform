/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable static optimization
  output: 'standalone',

  // Build optimization
  experimental: {
    // Enable modern builds for better performance
    esmExternals: true,
    // Enable server components
    serverComponentsExternalPackages: [],
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
      {
        source: '/static/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/_next/static/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
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
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/:path*`,
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

  // Development only configurations
  ...(process.env.NODE_ENV === 'development' && {
    // Enable React strict mode in development
    reactStrictMode: true,
  }),
};

module.exports = nextConfig;
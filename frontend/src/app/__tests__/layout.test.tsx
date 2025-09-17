/**
 * Layout Component Tests
 *
 * 這些測試確保清理重複文件後，剩餘的 Layout 組件正常工作
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import RootLayout from '../layout';
import uiReducer from '../../store/slices/uiSlice';
import signalsReducer from '../../store/slices/signalsSlice';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    pathname: '/',
  }),
  usePathname: () => '/',
}));

// Mock the child components
jest.mock('../../components/ui/Toast', () => {
  return function MockToast() {
    return <div data-testid="toast">Toast Component</div>;
  };
});

jest.mock('../../components/ui/WebSocketStatus', () => {
  return function MockWebSocketStatus() {
    return <div data-testid="websocket-status">WebSocket Status</div>;
  };
});

jest.mock('../../components/ErrorBoundary', () => {
  return function MockErrorBoundary({ children }: { children: React.ReactNode }) {
    return <div data-testid="error-boundary">{children}</div>;
  };
});

// Mock the Providers component
jest.mock('../../store/providers', () => ({
  Providers: ({ children }: { children: React.ReactNode }) => {
    const store = configureStore({
      reducer: {
        ui: uiReducer,
        signals: signalsReducer,
      },
    });

    return (
      <Provider store={store}>
        <div data-testid="providers">{children}</div>
      </Provider>
    );
  },
}));

// Mock CSS import
jest.mock('../globals.css', () => ({}));

describe('RootLayout', () => {
  const TestContent = () => <div data-testid="test-content">Test Content</div>;

  it('應該渲染基本的佈局結構', () => {
    render(
      <RootLayout>
        <TestContent />
      </RootLayout>
    );

    // 檢查基本結構
    expect(screen.getByRole('banner')).toBeInTheDocument(); // nav 標籤
    expect(screen.getByRole('main')).toBeInTheDocument(); // main 標籤
    expect(screen.getByRole('contentinfo')).toBeInTheDocument(); // footer 標籤
  });

  it('應該包含 ErrorBoundary 包裝', () => {
    render(
      <RootLayout>
        <TestContent />
      </RootLayout>
    );

    expect(screen.getByTestId('error-boundary')).toBeInTheDocument();
  });

  it('應該包含 Providers 包裝', () => {
    render(
      <RootLayout>
        <TestContent />
      </RootLayout>
    );

    expect(screen.getByTestId('providers')).toBeInTheDocument();
  });

  it('應該渲染所有導航連結', () => {
    render(
      <RootLayout>
        <TestContent />
      </RootLayout>
    );

    // 檢查所有導航連結
    expect(screen.getByText('股票分析平台')).toBeInTheDocument();
    expect(screen.getByText('首頁')).toBeInTheDocument();
    expect(screen.getByText('股票管理')).toBeInTheDocument();
    expect(screen.getByText('圖表分析')).toBeInTheDocument();
    expect(screen.getByText('即時儀表板')).toBeInTheDocument();
    expect(screen.getByText('交易信號')).toBeInTheDocument();
    expect(screen.getByText('系統狀態')).toBeInTheDocument(); // 這個在 layout 2.tsx 中是缺失的
  });

  it('應該包含 WebSocket 狀態指示器', () => {
    render(
      <RootLayout>
        <TestContent />
      </RootLayout>
    );

    expect(screen.getByTestId('websocket-status')).toBeInTheDocument();
  });

  it('應該包含 Toast 通知組件', () => {
    render(
      <RootLayout>
        <TestContent />
      </RootLayout>
    );

    expect(screen.getByTestId('toast')).toBeInTheDocument();
  });

  it('應該渲染子組件內容', () => {
    render(
      <RootLayout>
        <TestContent />
      </RootLayout>
    );

    expect(screen.getByTestId('test-content')).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('應該包含正確的 HTML 結構和屬性', () => {
    const { container } = render(
      <RootLayout>
        <TestContent />
      </RootLayout>
    );

    const html = container.querySelector('html');
    expect(html).toHaveAttribute('lang', 'zh-TW');

    const body = container.querySelector('body');
    expect(body).toHaveClass('min-h-screen', 'bg-gray-50');
  });

  it('應該包含版權信息', () => {
    render(
      <RootLayout>
        <TestContent />
      </RootLayout>
    );

    expect(screen.getByText(/© 2024 股票分析平台. 版權所有./)).toBeInTheDocument();
  });

  it('導航連結應該有正確的 href 屬性', () => {
    render(
      <RootLayout>
        <TestContent />
      </RootLayout>
    );

    // 檢查連結的 href 屬性
    expect(screen.getByText('首頁').closest('a')).toHaveAttribute('href', '/');
    expect(screen.getByText('股票管理').closest('a')).toHaveAttribute('href', '/stocks');
    expect(screen.getByText('圖表分析').closest('a')).toHaveAttribute('href', '/charts');
    expect(screen.getByText('即時儀表板').closest('a')).toHaveAttribute('href', '/dashboard');
    expect(screen.getByText('交易信號').closest('a')).toHaveAttribute('href', '/signals');
    expect(screen.getByText('系統狀態').closest('a')).toHaveAttribute('href', '/system');
  });

  it('應該有響應式設計的 CSS classes', () => {
    render(
      <RootLayout>
        <TestContent />
      </RootLayout>
    );

    // 檢查響應式容器
    const container = screen.getByText('股票分析平台').closest('.max-w-7xl');
    expect(container).toHaveClass('mx-auto', 'px-4', 'sm:px-6', 'lg:px-8');

    // 檢查導航樣式
    const nav = screen.getByRole('banner');
    expect(nav).toHaveClass('bg-white', 'shadow-sm', 'border-b', 'border-gray-200');
  });
});

describe('RootLayout - 組件集成測試', () => {
  it('應該正確集成所有子組件', () => {
    const TestPage = () => (
      <div>
        <h1>Test Page</h1>
        <p>This is a test page content</p>
      </div>
    );

    render(
      <RootLayout>
        <TestPage />
      </RootLayout>
    );

    // 驗證所有組件都被渲染
    expect(screen.getByTestId('error-boundary')).toBeInTheDocument();
    expect(screen.getByTestId('providers')).toBeInTheDocument();
    expect(screen.getByTestId('websocket-status')).toBeInTheDocument();
    expect(screen.getByTestId('toast')).toBeInTheDocument();

    // 驗證頁面內容被正確渲染
    expect(screen.getByText('Test Page')).toBeInTheDocument();
    expect(screen.getByText('This is a test page content')).toBeInTheDocument();
  });

  it('應該在組件層次結構中保持正確的順序', () => {
    render(
      <RootLayout>
        <div>Content</div>
      </RootLayout>
    );

    const errorBoundary = screen.getByTestId('error-boundary');
    const providers = screen.getByTestId('providers');

    // ErrorBoundary 應該包含 Providers
    expect(errorBoundary).toContainElement(providers);
  });
});

describe('RootLayout - 對比 layout 2.tsx 缺失功能測試', () => {
  it('應該包含 ErrorBoundary（layout 2.tsx 中缺失）', () => {
    render(
      <RootLayout>
        <div>Test</div>
      </RootLayout>
    );

    // 這個功能在 layout 2.tsx 中是缺失的
    expect(screen.getByTestId('error-boundary')).toBeInTheDocument();
  });

  it('應該包含系統狀態導航連結（layout 2.tsx 中缺失）', () => {
    render(
      <RootLayout>
        <div>Test</div>
      </RootLayout>
    );

    // 這個導航項在 layout 2.tsx 中是缺失的
    expect(screen.getByText('系統狀態')).toBeInTheDocument();
    expect(screen.getByText('系統狀態').closest('a')).toHaveAttribute('href', '/system');
  });

  it('應該驗證清理重複文件的決策是正確的', () => {
    // 這個測試確保我們保留了功能更完整的版本
    render(
      <RootLayout>
        <div>Test</div>
      </RootLayout>
    );

    // 驗證所有關鍵功能都存在
    const criticalFeatures = [
      'error-boundary',      // 錯誤邊界
      'providers',          // Redux providers
      'websocket-status',   // WebSocket 狀態
      'toast',             // Toast 通知
    ];

    criticalFeatures.forEach(feature => {
      expect(screen.getByTestId(feature)).toBeInTheDocument();
    });

    // 驗證所有導航項都存在
    const navItems = [
      '首頁',
      '股票管理',
      '圖表分析',
      '即時儀表板',
      '交易信號',
      '系統狀態'
    ];

    navItems.forEach(item => {
      expect(screen.getByText(item)).toBeInTheDocument();
    });
  });
});
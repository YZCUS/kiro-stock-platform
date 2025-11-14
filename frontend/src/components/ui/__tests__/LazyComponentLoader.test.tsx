/**
 * LazyComponentLoader Tests
 *
 * 測試懶載入組件加載器的功能
 */
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import {
  createLazyComponent,
  createStandardLazyComponent,
  createLazyChartComponent
} from '../LazyComponentLoader';

// Mock dynamic import
jest.mock('next/dynamic', () => {
  return (importFn: () => Promise<any>, options: any) => {
    const MockComponent = React.forwardRef<any, any>((props, ref) => {
      const [loading, setLoading] = React.useState(true);
      const [error, setError] = React.useState<Error | null>(null);

      React.useEffect(() => {
        importFn()
          .then(() => {
            setLoading(false);
          })
          .catch((err) => {
            setError(err);
            setLoading(false);
          });
      }, []);

      if (loading && options.loading) {
        return React.createElement(options.loading);
      }

      if (error) {
        throw error;
      }

      return React.createElement('div', { ...props, ref }, 'Mocked Component');
    });

    MockComponent.displayName = 'MockDynamicComponent';
    return MockComponent;
  };
});

// Mock 測試組件
const TestComponent: React.FC<{ message: string }> = ({ message }) => (
  <div data-testid="test-component">{message}</div>
);

describe('LazyComponentLoader', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('createLazyComponent', () => {
    it('應該顯示載入狀態', async () => {
      const mockImportFn = jest.fn(() =>
        new Promise<{ default: React.ComponentType<any> }>(resolve =>
          setTimeout(() => resolve({ default: TestComponent }), 100)
        )
      );

      const LazyTestComponent = createLazyComponent({
        importFn: mockImportFn,
      });

      render(<LazyTestComponent message="test" />);

      // 驗證載入狀態顯示
      expect(screen.getByRole('progressbar', { hidden: true })).toBeInTheDocument();
    });

    it('應該在載入完成後顯示組件', async () => {
      const mockImportFn = jest.fn(() =>
        Promise.resolve<{ default: React.ComponentType<any> }>({ default: TestComponent })
      );

      const LazyTestComponent = createLazyComponent({
        importFn: mockImportFn,
        minLoadingTime: 0,
      });

      render(<LazyTestComponent message="Hello World" />);

      await waitFor(() => {
        expect(screen.getByTestId('test-component')).toBeInTheDocument();
      });

      expect(screen.getByText('Hello World')).toBeInTheDocument();
    });

    it('應該處理載入錯誤', async () => {
      const mockError = new Error('Failed to load component');
      const mockImportFn = jest.fn(() => Promise.reject(mockError));

      const LazyTestComponent = createLazyComponent({
        importFn: mockImportFn,
      });

      render(<LazyTestComponent message="test" />);

      await waitFor(() => {
        expect(screen.getByText('組件載入失敗')).toBeInTheDocument();
      });

      expect(screen.getByText('Failed to load component')).toBeInTheDocument();
      expect(screen.getByText('重新載入')).toBeInTheDocument();
    });

    it('應該支援重試功能', async () => {
      let shouldFail = true;
      const mockImportFn = jest.fn((): Promise<{ default: React.ComponentType<any> }> => {
        if (shouldFail) {
          return Promise.reject(new Error('Load failed'));
        }
        return Promise.resolve({ default: TestComponent });
      });

      const LazyTestComponent = createLazyComponent({
        importFn: mockImportFn,
      });

      render(<LazyTestComponent message="Retry Test" />);

      // 等待錯誤顯示
      await waitFor(() => {
        expect(screen.getByText('組件載入失敗')).toBeInTheDocument();
      });

      // 設置成功並點擊重試
      shouldFail = false;
      const retryButton = screen.getByText('重新載入');
      fireEvent.click(retryButton);

      // 驗證重試後載入成功
      await waitFor(() => {
        expect(screen.getByTestId('test-component')).toBeInTheDocument();
      });

      expect(screen.getByText('Retry Test')).toBeInTheDocument();
    });

    it('應該使用自定義載入組件', async () => {
      const CustomLoading = () => <div data-testid="custom-loading">Custom Loading...</div>;

      const mockImportFn = jest.fn(() =>
        new Promise<{ default: React.ComponentType<any> }>(resolve =>
          setTimeout(() => resolve({ default: TestComponent }), 100)
        )
      );

      const LazyTestComponent = createLazyComponent({
        importFn: mockImportFn,
        fallback: CustomLoading,
      });

      render(<LazyTestComponent message="test" />);

      expect(screen.getByTestId('custom-loading')).toBeInTheDocument();
    });

    it('應該遵守最小載入時間', async () => {
      const mockImportFn = jest.fn(() =>
        Promise.resolve<{ default: React.ComponentType<any> }>({ default: TestComponent })
      );

      const LazyTestComponent = createLazyComponent({
        importFn: mockImportFn,
        minLoadingTime: 200,
      });

      const startTime = Date.now();
      render(<LazyTestComponent message="test" />);

      await waitFor(() => {
        expect(screen.getByTestId('test-component')).toBeInTheDocument();
      });

      const endTime = Date.now();
      const elapsed = endTime - startTime;

      // 驗證至少等待了最小載入時間
      expect(elapsed).toBeGreaterThanOrEqual(190); // 允許一些誤差
    });
  });

  describe('createStandardLazyComponent', () => {
    it('應該創建標準的懶載入組件', async () => {
      const mockImportFn = jest.fn(() =>
        Promise.resolve<{ default: React.ComponentType<any> }>({ default: TestComponent })
      );

      const LazyTestComponent = createStandardLazyComponent(mockImportFn);

      render(<LazyTestComponent message="Standard Test" />);

      await waitFor(() => {
        expect(screen.getByTestId('test-component')).toBeInTheDocument();
      });

      expect(screen.getByText('Standard Test')).toBeInTheDocument();
    });

    it('應該顯示標準載入樣式', async () => {
      const mockImportFn = jest.fn(() =>
        new Promise<{ default: React.ComponentType<any> }>(resolve =>
          setTimeout(() => resolve({ default: TestComponent }), 100)
        )
      );

      const LazyTestComponent = createStandardLazyComponent(mockImportFn, 300);

      const { container } = render(<LazyTestComponent message="test" />);

      // 驗證標準載入樣式
      const loadingElement = container.querySelector('.bg-white.shadow.rounded-lg');
      expect(loadingElement).toBeInTheDocument();
      expect(loadingElement).toHaveStyle('min-height: 300px');
    });
  });

  describe('createLazyChartComponent', () => {
    it('應該創建圖表專用的懶載入組件', async () => {
      const mockImportFn = jest.fn(() =>
        Promise.resolve({ default: TestComponent })
      );

      const LazyChartComponent = createLazyChartComponent(mockImportFn);

      render(<LazyChartComponent message="Chart Test" />);

      await waitFor(() => {
        expect(screen.getByTestId('test-component')).toBeInTheDocument();
      });

      expect(screen.getByText('Chart Test')).toBeInTheDocument();
    });

    it('應該顯示圖表載入樣式', async () => {
      const mockImportFn = jest.fn(() =>
        new Promise<{ default: React.ComponentType<any> }>(resolve =>
          setTimeout(() => resolve({ default: TestComponent }), 100)
        )
      );

      const LazyChartComponent = createLazyChartComponent(mockImportFn, 500);

      render(<LazyChartComponent message="test" />);

      // 驗證圖表載入文字
      expect(screen.getByText('載入圖表組件中...')).toBeInTheDocument();
    });

    it('應該顯示圖表專用的錯誤樣式', async () => {
      const mockImportFn = jest.fn(() =>
        Promise.reject(new Error('Chart load failed'))
      );

      const LazyChartComponent = createLazyChartComponent(mockImportFn);

      render(<LazyChartComponent message="test" />);

      await waitFor(() => {
        expect(screen.getByText('圖表載入失敗')).toBeInTheDocument();
      });
    });
  });

  describe('性能優化', () => {
    it('應該避免不必要的重新渲染', async () => {
      const mockImportFn = jest.fn(() =>
        Promise.resolve({ default: TestComponent })
      );

      const LazyTestComponent = createLazyComponent({
        importFn: mockImportFn,
      });

      const { rerender } = render(<LazyTestComponent message="test1" />);

      await waitFor(() => {
        expect(screen.getByTestId('test-component')).toBeInTheDocument();
      });

      const initialCallCount = mockImportFn.mock.calls.length;

      // 重新渲染但 props 改變
      rerender(<LazyTestComponent message="test2" />);

      // importFn 不應該被重新調用
      expect(mockImportFn.mock.calls.length).toBe(initialCallCount);
      expect(screen.getByText('test2')).toBeInTheDocument();
    });
  });
});
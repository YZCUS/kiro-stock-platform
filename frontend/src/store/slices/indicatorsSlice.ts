/**
 * 技術指標管理 Redux Slice
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { TechnicalIndicator } from '../../types';

// 技術指標類型定義
export interface IndicatorData {
  symbol: string;
  timeframe: string;
  indicators: {
    sma?: TechnicalIndicator[];
    ema?: TechnicalIndicator[];
    rsi?: TechnicalIndicator[];
    macd?: {
      macd: TechnicalIndicator[];
      signal: TechnicalIndicator[];
      histogram: TechnicalIndicator[];
    };
    bollinger?: {
      upper: TechnicalIndicator[];
      middle: TechnicalIndicator[];
      lower: TechnicalIndicator[];
    };
    kd?: {
      k: TechnicalIndicator[];
      d: TechnicalIndicator[];
    };
  };
  lastUpdate: string;
}

export interface IndicatorConfig {
  type: 'SMA' | 'EMA' | 'RSI' | 'MACD' | 'BOLLINGER' | 'KD';
  period?: number;
  parameters?: Record<string, any>;
  enabled: boolean;
}

// 異步操作
export const fetchIndicators = createAsyncThunk(
  'indicators/fetchIndicators',
  async (params: {
    symbol: string;
    timeframe: string;
    indicators: string[];
    startDate?: string;
    endDate?: string;
  }) => {
    // 模擬 API 調用
    await new Promise(resolve => setTimeout(resolve, 1000));

    // 生成模擬技術指標數據
    const generateMockData = (days: number = 30) => {
      const data: TechnicalIndicator[] = [];
      const now = new Date();

      for (let i = days - 1; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);

        data.push({
          date: date.toISOString().split('T')[0],
          value: Math.random() * 100 + 50, // 隨機值 50-150
          parameters: {},
        });
      }

      return data;
    };

    const mockIndicatorData: IndicatorData = {
      symbol: params.symbol,
      timeframe: params.timeframe,
      indicators: {},
      lastUpdate: new Date().toISOString(),
    };

    // 根據請求的指標生成對應數據
    if (params.indicators.includes('SMA')) {
      mockIndicatorData.indicators.sma = generateMockData().map(item => ({
        ...item,
        value: item.value * 0.95, // SMA 稍微平滑
        parameters: { period: 20 },
      }));
    }

    if (params.indicators.includes('EMA')) {
      mockIndicatorData.indicators.ema = generateMockData().map(item => ({
        ...item,
        value: item.value * 0.98, // EMA 更接近當前價格
        parameters: { period: 12 },
      }));
    }

    if (params.indicators.includes('RSI')) {
      mockIndicatorData.indicators.rsi = generateMockData().map(item => ({
        ...item,
        value: Math.random() * 80 + 10, // RSI 範圍 10-90
        parameters: { period: 14 },
      }));
    }

    if (params.indicators.includes('MACD')) {
      const macdData = generateMockData();
      mockIndicatorData.indicators.macd = {
        macd: macdData.map(item => ({
          ...item,
          value: (Math.random() - 0.5) * 10, // MACD 可以是負值
          parameters: { fast: 12, slow: 26 },
        })),
        signal: macdData.map(item => ({
          ...item,
          value: (Math.random() - 0.5) * 8, // Signal 線
          parameters: { period: 9 },
        })),
        histogram: macdData.map(item => ({
          ...item,
          value: (Math.random() - 0.5) * 5, // 柱狀圖
          parameters: {},
        })),
      };
    }

    if (params.indicators.includes('BOLLINGER')) {
      const baseData = generateMockData();
      mockIndicatorData.indicators.bollinger = {
        upper: baseData.map(item => ({
          ...item,
          value: item.value * 1.1, // 上軌
          parameters: { period: 20, std: 2 },
        })),
        middle: baseData.map(item => ({
          ...item,
          value: item.value, // 中軌 (SMA)
          parameters: { period: 20 },
        })),
        lower: baseData.map(item => ({
          ...item,
          value: item.value * 0.9, // 下軌
          parameters: { period: 20, std: 2 },
        })),
      };
    }

    if (params.indicators.includes('KD')) {
      const kdData = generateMockData();
      mockIndicatorData.indicators.kd = {
        k: kdData.map(item => ({
          ...item,
          value: Math.random() * 80 + 10, // K 值 10-90
          parameters: { period: 9 },
        })),
        d: kdData.map(item => ({
          ...item,
          value: Math.random() * 80 + 10, // D 值 10-90
          parameters: { period: 3 },
        })),
      };
    }

    return mockIndicatorData;
  }
);

export const calculateIndicator = createAsyncThunk(
  'indicators/calculateIndicator',
  async (params: {
    symbol: string;
    type: string;
    period: number;
    parameters?: Record<string, any>;
  }) => {
    // 模擬計算特定指標
    await new Promise(resolve => setTimeout(resolve, 500));

    return {
      symbol: params.symbol,
      type: params.type,
      data: Array.from({ length: 20 }, (_, i) => ({
        date: new Date(Date.now() - (19 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        value: Math.random() * 100 + 50,
        parameters: { period: params.period, ...params.parameters },
      })),
      calculatedAt: new Date().toISOString(),
    };
  }
);

// 介面定義
interface IndicatorsState {
  data: Record<string, IndicatorData>; // 以 symbol-timeframe 為 key
  configs: Record<string, IndicatorConfig[]>; // 以 symbol 為 key 的指標配置
  loading: boolean;
  error: string | null;
  calculating: string[]; // 正在計算中的指標
  lastCalculation: string | null;
}

// 初始狀態
const initialState: IndicatorsState = {
  data: {},
  configs: {},
  loading: false,
  error: null,
  calculating: [],
  lastCalculation: null,
};

// Slice 定義
const indicatorsSlice = createSlice({
  name: 'indicators',
  initialState,
  reducers: {
    setIndicatorConfig: (state, action: PayloadAction<{
      symbol: string;
      configs: IndicatorConfig[];
    }>) => {
      const { symbol, configs } = action.payload;
      state.configs[symbol] = configs;
    },
    updateIndicatorConfig: (state, action: PayloadAction<{
      symbol: string;
      type: string;
      config: Partial<IndicatorConfig>;
    }>) => {
      const { symbol, type, config } = action.payload;
      if (state.configs[symbol]) {
        const index = state.configs[symbol].findIndex(c => c.type === type);
        if (index !== -1) {
          state.configs[symbol][index] = { ...state.configs[symbol][index], ...config };
        }
      }
    },
    toggleIndicator: (state, action: PayloadAction<{
      symbol: string;
      type: string;
    }>) => {
      const { symbol, type } = action.payload;
      if (state.configs[symbol]) {
        const config = state.configs[symbol].find(c => c.type === type);
        if (config) {
          config.enabled = !config.enabled;
        }
      }
    },
    clearError: (state) => {
      state.error = null;
    },
    clearIndicatorData: (state, action: PayloadAction<string>) => {
      const key = action.payload;
      delete state.data[key];
    },
    updateRealtimeIndicator: (state, action: PayloadAction<{
      symbol: string;
      timeframe: string;
      type: string;
      value: TechnicalIndicator;
    }>) => {
      const { symbol, timeframe, type, value } = action.payload;
      const key = `${symbol}-${timeframe}`;

      if (state.data[key]) {
        // 更新即時指標值
        if (type === 'sma' && state.data[key].indicators.sma) {
          state.data[key].indicators.sma.push(value);
          // 保持最多100個數據點
          if (state.data[key].indicators.sma!.length > 100) {
            state.data[key].indicators.sma = state.data[key].indicators.sma!.slice(-100);
          }
        }
        // 類似的邏輯可以擴展到其他指標
        state.data[key].lastUpdate = new Date().toISOString();
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // fetchIndicators
      .addCase(fetchIndicators.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchIndicators.fulfilled, (state, action) => {
        state.loading = false;
        const { symbol, timeframe } = action.payload;
        const key = `${symbol}-${timeframe}`;
        state.data[key] = action.payload;
        state.lastCalculation = new Date().toISOString();
      })
      .addCase(fetchIndicators.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || '獲取技術指標失敗';
      })

      // calculateIndicator
      .addCase(calculateIndicator.pending, (state, action) => {
        const { symbol, type } = action.meta.arg;
        const key = `${symbol}-${type}`;
        if (!state.calculating.includes(key)) {
          state.calculating.push(key);
        }
      })
      .addCase(calculateIndicator.fulfilled, (state, action) => {
        const { symbol, type } = action.payload;
        const key = `${symbol}-${type}`;
        state.calculating = state.calculating.filter(c => c !== key);
        state.lastCalculation = action.payload.calculatedAt;
      })
      .addCase(calculateIndicator.rejected, (state, action) => {
        const { symbol, type } = action.meta.arg;
        const key = `${symbol}-${type}`;
        state.calculating = state.calculating.filter(c => c !== key);
        state.error = action.error.message || `計算 ${type} 指標失敗`;
      });
  },
});

export const {
  setIndicatorConfig,
  updateIndicatorConfig,
  toggleIndicator,
  clearError,
  clearIndicatorData,
  updateRealtimeIndicator,
} = indicatorsSlice.actions;

export default indicatorsSlice.reducer;
import { IndicatorsApiService, IndicatorResponse, IndicatorBatchResponse } from '../indicatorsApi';
import { ApiService } from '../../lib/api';

// Mock ApiService
jest.mock('../../lib/api');
const mockApiService = ApiService as jest.Mocked<typeof ApiService>;

describe('IndicatorsApiService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('calculateIndicator', () => {
    it('should call the correct endpoint with default parameters', async () => {
      const mockResponse: IndicatorResponse = {
        symbol: 'AAPL',
        indicators: {
          rsi: 65.5,
          sma_20: 120.5
        },
        period: 30,
        timestamp: '2024-01-01T12:00:00Z',
        success: true,
        data_points: 30
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const params = {
        stock_id: 1,
        indicator_type: 'RSI' as const,
        period: 14
      };

      const result = await IndicatorsApiService.calculateIndicator(params);

      expect(mockApiService.post).toHaveBeenCalledWith(
        '/api/v1/stocks/1/indicators/calculate',
        {
          indicator_type: 'RSI',
          period: 14,
          timeframe: '1d',
          parameters: {},
          start_date: undefined,
          end_date: undefined
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle custom parameters correctly', async () => {
      const mockResponse: IndicatorResponse = {
        symbol: 'TSLA',
        indicators: {
          rsi: 45.2,
          sma_5: 115.8
        },
        period: 50,
        timestamp: '2024-01-01T12:00:00Z',
        success: true,
        data_points: 50
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const params = {
        stock_id: 2,
        indicator_type: 'RSI' as any, // Multiple types in comma-separated string
        period: 50,
        timeframe: '1h' as const,
        parameters: { custom_param: 'value' },
        start_date: '2024-01-01',
        end_date: '2024-01-31'
      };

      const result = await IndicatorsApiService.calculateIndicator(params);

      expect(mockApiService.post).toHaveBeenCalledWith(
        '/api/v1/stocks/2/indicators/calculate',
        {
          indicator_type: 'RSI,SMA_5',
          period: 50,
          timeframe: '1h',
          parameters: { custom_param: 'value' },
          start_date: '2024-01-01',
          end_date: '2024-01-31'
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle API errors gracefully', async () => {
      const errorMessage = 'Stock not found';
      mockApiService.post.mockRejectedValue(new Error(errorMessage));

      const params = {
        stock_id: 999,
        indicator_type: 'RSI' as const,
        period: 14
      };

      await expect(IndicatorsApiService.calculateIndicator(params))
        .rejects.toThrow(errorMessage);

      expect(mockApiService.post).toHaveBeenCalledTimes(1);
    });

    it('should handle response with errors and warnings', async () => {
      const mockResponse: IndicatorResponse = {
        symbol: '2330.TW',
        indicators: {
          rsi: 65.5
        },
        period: 30,
        timestamp: '2024-01-01T12:00:00Z',
        success: false,
        data_points: 5,
        errors: ['數據不足，需要至少20天數據'],
        warnings: ['RSI 數據可能不準確']
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const params = {
        stock_id: 1,
        indicator_type: 'RSI' as any, // Multiple types in comma-separated string
        period: 30
      };

      const result = await IndicatorsApiService.calculateIndicator(params);

      expect(result).toEqual(mockResponse);
      expect(result.success).toBe(false);
      expect(result.errors).toHaveLength(1);
      expect(result.warnings).toHaveLength(1);
    });

    it('should handle complex indicator formats', async () => {
      const mockResponse: IndicatorResponse = {
        symbol: 'AAPL',
        indicators: {
          rsi: 65.5,
          sma_20: 120.5,
          macd: {
            macd: 2.5,
            signal: 1.8,
            histogram: 0.7
          },
          bollinger: {
            upper: 130.0,
            middle: 125.0,
            lower: 120.0
          },
          stoch: {
            k: 80.5,
            d: 75.2
          }
        },
        period: 30,
        timestamp: '2024-01-01T12:00:00Z',
        success: true,
        data_points: 30
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const params = {
        stock_id: 1,
        indicator_type: 'RSI' as any, // Multiple types in comma-separated string
        period: 30
      };

      const result = await IndicatorsApiService.calculateIndicator(params);

      expect(result.indicators.rsi).toBe(65.5);
      expect(result.indicators.macd).toEqual({
        macd: 2.5,
        signal: 1.8,
        histogram: 0.7
      });
      expect(result.indicators.bollinger).toEqual({
        upper: 130.0,
        middle: 125.0,
        lower: 120.0
      });
      expect(result.indicators.stoch).toEqual({
        k: 80.5,
        d: 75.2
      });
    });
  });

  describe('batchCalculateIndicators', () => {
    it('should call the batch endpoint correctly', async () => {
      const mockResponse = {
        stock_id: 1,
        symbol: 'AAPL',
        timeframe: '1d',
        indicators: {
          RSI: {
            data: [{ value: 65.5, date: '2024-01-01' }],
            parameters: { period: 14 }
          },
          SMA_20: {
            data: [{ value: 120.5, date: '2024-01-01' }],
            parameters: { period: 20 }
          }
        },
        calculated_at: '2024-01-01T12:00:00Z'
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const params = {
        stock_id: 1,
        indicators: [
          { type: 'RSI', period: 14 },
          { type: 'SMA_20', period: 20 }
        ],
        timeframe: '1d' as const,
        start_date: '2024-01-01',
        end_date: '2024-01-31'
      };

      const result = await IndicatorsApiService.batchCalculateIndicators(params);

      expect(mockApiService.post).toHaveBeenCalledWith(
        '/api/v1/stocks/1/indicators/calculate/batch',
        {
          indicators: [
            { type: 'RSI', period: 14 },
            { type: 'SMA_20', period: 20 }
          ],
          timeframe: '1d',
          start_date: '2024-01-01',
          end_date: '2024-01-31'
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should use default timeframe when not provided', async () => {
      const mockResponse = {
        stock_id: 1,
        symbol: 'AAPL',
        timeframe: '1d',
        indicators: {},
        calculated_at: '2024-01-01T12:00:00Z'
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const params = {
        stock_id: 1,
        indicators: [{ type: 'RSI', period: 14 }]
      };

      await IndicatorsApiService.batchCalculateIndicators(params);

      expect(mockApiService.post).toHaveBeenCalledWith(
        '/api/v1/stocks/1/indicators/calculate/batch',
        expect.objectContaining({
          timeframe: '1d'
        })
      );
    });
  });

  describe('Response format validation', () => {
    it('should validate IndicatorResponse format', () => {
      const validResponse: IndicatorResponse = {
        symbol: 'AAPL',
        indicators: {
          rsi: 65.5,
          sma_20: 120.5
        },
        period: 30,
        timestamp: '2024-01-01T12:00:00Z',
        success: true,
        data_points: 30
      };

      // Type checking ensures this compiles correctly
      expect(validResponse.symbol).toBeDefined();
      expect(validResponse.indicators).toBeDefined();
      expect(validResponse.period).toBeDefined();
      expect(validResponse.timestamp).toBeDefined();
      expect(validResponse.success).toBeDefined();
      expect(validResponse.data_points).toBeDefined();
    });

    it('should handle optional error and warning fields', () => {
      const responseWithErrors: IndicatorResponse = {
        symbol: 'AAPL',
        indicators: {},
        period: 30,
        timestamp: '2024-01-01T12:00:00Z',
        success: false,
        data_points: 5,
        errors: ['Insufficient data'],
        warnings: ['Data quality issues']
      };

      expect(responseWithErrors.errors).toHaveLength(1);
      expect(responseWithErrors.warnings).toHaveLength(1);
      expect(responseWithErrors.success).toBe(false);
    });

    it('should match backend IndicatorCalculateRequest format', async () => {
      // 驗證前端請求格式與後端期望的 IndicatorCalculateRequest 格式一致
      const params = {
        stock_id: 1,
        indicator_type: 'RSI' as any, // Multiple types in comma-separated string
        period: 20,
        timeframe: '1d' as const,
        parameters: { custom_param: 'value' },
        start_date: '2024-01-01',
        end_date: '2024-01-31'
      };

      // 驗證生成的請求數據格式
      const expectedRequestData = {
        indicator_type: 'RSI,SMA_20,MACD',
        period: 20,
        timeframe: '1d',
        parameters: { custom_param: 'value' },
        start_date: '2024-01-01',
        end_date: '2024-01-31'
      };

      const mockResponse: IndicatorResponse = {
        symbol: 'AAPL',
        indicators: {
          rsi: 65.5,
          sma_20: 120.5,
          macd: {
            macd: 2.5,
            signal: 1.8,
            histogram: 0.7
          }
        },
        period: 20,
        timestamp: '2024-01-01T12:00:00Z',
        success: true,
        data_points: 30
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const result = await IndicatorsApiService.calculateIndicator(params);

      // 驗證 API 調用的參數格式正確
      expect(mockApiService.post).toHaveBeenCalledWith(
        '/api/v1/stocks/1/indicators/calculate',
        expectedRequestData
      );

      // 驗證響應格式符合 IndicatorResponse 接口
      expect(result).toEqual(mockResponse);
      expect(typeof result.symbol).toBe('string');
      expect(typeof result.indicators).toBe('object');
      expect(typeof result.period).toBe('number');
      expect(typeof result.timestamp).toBe('string');
      expect(typeof result.success).toBe('boolean');
      expect(typeof result.data_points).toBe('number');
    });

    it('should handle default parameters correctly for POST endpoint', async () => {
      // 測試預設參數處理
      const params = {
        stock_id: 1,
        indicator_type: 'RSI' as const
        // 不提供 period, timeframe, parameters
      };

      const expectedRequestData = {
        indicator_type: 'RSI',
        period: 14, // 前端應該提供預設值
        timeframe: '1d', // 前端應該提供預設值
        parameters: {}, // 前端應該提供預設值
        start_date: undefined,
        end_date: undefined
      };

      const mockResponse: IndicatorResponse = {
        symbol: 'AAPL',
        indicators: { rsi: 65.5 },
        period: 14,
        timestamp: '2024-01-01T12:00:00Z',
        success: true,
        data_points: 30
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const result = await IndicatorsApiService.calculateIndicator(params);

      expect(mockApiService.post).toHaveBeenCalledWith(
        '/api/v1/stocks/1/indicators/calculate',
        expectedRequestData
      );

      expect(result).toEqual(mockResponse);
    });

    it('should match backend IndicatorBatchCalculateRequest format', async () => {
      // 驗證前端批量請求格式與後端期望的格式一致
      const params = {
        stock_id: 1,
        indicators: [
          { type: 'RSI', period: 14 },
          { type: 'SMA_20', period: 20, parameters: { custom_param: 'value' } }
        ],
        timeframe: '1d' as const,
        start_date: '2024-01-01',
        end_date: '2024-01-31'
      };

      const expectedRequestData = {
        indicators: [
          { type: 'RSI', period: 14 },
          { type: 'SMA_20', period: 20, parameters: { custom_param: 'value' } }
        ],
        timeframe: '1d',
        start_date: '2024-01-01',
        end_date: '2024-01-31'
      };

      const mockResponse: IndicatorBatchResponse = {
        stock_id: 1,
        symbol: 'AAPL',
        timeframe: '1d',
        indicators: {
          RSI: {
            data: [{ date: '2024-01-01', value: 65.5 }],
            parameters: { period: 14, timeframe: '1d' }
          },
          SMA_20: {
            data: [{ date: '2024-01-01', value: 120.5 }],
            parameters: { period: 20, timeframe: '1d', custom_param: 'value' }
          }
        },
        calculated_at: '2024-01-01T12:00:00Z'
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const result = await IndicatorsApiService.batchCalculateIndicators(params);

      // 驗證 API 調用的參數格式正確
      expect(mockApiService.post).toHaveBeenCalledWith(
        '/api/v1/stocks/1/indicators/calculate/batch',
        expectedRequestData
      );

      // 驗證響應格式符合 IndicatorBatchResponse 接口
      expect(result).toEqual(mockResponse);
      expect(typeof result.stock_id).toBe('number');
      expect(typeof result.symbol).toBe('string');
      expect(typeof result.timeframe).toBe('string');
      expect(typeof result.indicators).toBe('object');
      expect(typeof result.calculated_at).toBe('string');

      // 驗證每個指標的數據結構
      Object.entries(result.indicators).forEach(([indicatorType, indicatorData]) => {
        expect(typeof indicatorType).toBe('string');
        expect(Array.isArray(indicatorData.data)).toBe(true);
        expect(typeof indicatorData.parameters).toBe('object');
      });
    });

    it('should handle batch calculation with default parameters', async () => {
      const params = {
        stock_id: 1,
        indicators: [
          { type: 'RSI' }, // 不提供 period
          { type: 'SMA_20' } // 不提供 period
        ]
        // 不提供 timeframe
      };

      const expectedRequestData = {
        indicators: [
          { type: 'RSI' },
          { type: 'SMA_20' }
        ],
        timeframe: '1d',
        start_date: undefined,
        end_date: undefined
      };

      const mockResponse: IndicatorBatchResponse = {
        stock_id: 1,
        symbol: 'AAPL',
        timeframe: '1d',
        indicators: {
          RSI: {
            data: [{ date: '2024-01-01', value: 65.5 }],
            parameters: { period: 14, timeframe: '1d' }
          },
          SMA_20: {
            data: [{ date: '2024-01-01', value: 120.5 }],
            parameters: { period: 20, timeframe: '1d' }
          }
        },
        calculated_at: '2024-01-01T12:00:00Z'
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const result = await IndicatorsApiService.batchCalculateIndicators(params);

      expect(mockApiService.post).toHaveBeenCalledWith(
        '/api/v1/stocks/1/indicators/calculate/batch',
        expectedRequestData
      );

      expect(result).toEqual(mockResponse);
    });

    it('should call the correct summary endpoint for getIndicators', async () => {
      // 驗證 getIndicators 使用新的 SUMMARY 端點
      const params = {
        stock_id: 1,
        indicator_types: ['RSI', 'SMA_20'],
        timeframe: '1d' as const
      };

      const mockResponse = {
        stock_id: 1,
        symbol: 'AAPL',
        timeframe: '1d',
        indicators: {
          RSI: {
            symbol: 'AAPL',
            indicators: { rsi: 65.5 },
            period: 14,
            timestamp: '2024-01-01T12:00:00Z',
            success: true,
            data_points: 30
          },
          SMA_20: {
            symbol: 'AAPL',
            indicators: { sma_20: 120.5 },
            period: 20,
            timestamp: '2024-01-01T12:00:00Z',
            success: true,
            data_points: 30
          }
        }
      };

      mockApiService.get.mockResolvedValue(mockResponse);

      const result = await IndicatorsApiService.getIndicators(params);

      // 驗證使用 SUMMARY 端點而不是 LIST 端點
      expect(mockApiService.get).toHaveBeenCalledWith(
        '/api/v1/stocks/1/indicators/summary?indicator_types=RSI&indicator_types=SMA_20&timeframe=1d'
      );

      expect(result).toEqual(mockResponse);

      // 驗證響應格式符合前端期望
      expect(typeof result.stock_id).toBe('number');
      expect(typeof result.symbol).toBe('string');
      expect(typeof result.timeframe).toBe('string');
      expect(typeof result.indicators).toBe('object');

      // 驗證每個指標都是 IndicatorResponse 格式
      Object.entries(result.indicators).forEach(([indicatorType, indicatorResponse]) => {
        expect(typeof indicatorType).toBe('string');
        expect(typeof indicatorResponse.symbol).toBe('string');
        expect(typeof indicatorResponse.indicators).toBe('object');
        expect(typeof indicatorResponse.success).toBe('boolean');
      });
    });

    it('should verify the corrected summary endpoint contract', async () => {
      // 驗證修正後的摘要端點契約是否正確
      const params = {
        stock_id: 1,
        indicator_types: ['RSI', 'SMA_20'],
        timeframe: '1d' as const
      };

      // 這是後端實際返回的格式（匹配 IndicatorSummaryResponse）
      const mockBackendResponse = {
        stock_id: 1,
        symbol: 'AAPL',
        timeframe: '1d',
        indicators: {
          RSI: {
            symbol: 'AAPL',
            indicators: { rsi: 65.5 },
            period: 14,
            timestamp: '2024-01-01T12:00:00Z',
            success: true,
            data_points: 30
          },
          SMA_20: {
            symbol: 'AAPL',
            indicators: { sma_20: 120.5 },
            period: 20,
            timestamp: '2024-01-01T12:00:00Z',
            success: true,
            data_points: 30
          }
        }
      };

      mockApiService.get.mockResolvedValue(mockBackendResponse);

      const result = await IndicatorsApiService.getIndicators(params);

      // 驗證 API 調用使用正確的端點
      expect(mockApiService.get).toHaveBeenCalledWith(
        '/api/v1/stocks/1/indicators/summary?indicator_types=RSI&indicator_types=SMA_20&timeframe=1d'
      );

      // 驗證響應格式完全匹配前端期望
      expect(result).toEqual(mockBackendResponse);

      // 關鍵驗證：確保 stock_id 和 symbol 不是 undefined
      expect(result.stock_id).toBe(1);
      expect(result.stock_id).not.toBeUndefined();
      expect(result.symbol).toBe('AAPL');
      expect(result.symbol).not.toBeUndefined();
      expect(result.timeframe).toBe('1d');
      expect(result.timeframe).not.toBeUndefined();

      // 驗證 indicators 結構
      expect(typeof result.indicators).toBe('object');
      expect(result.indicators).not.toBeUndefined();

      // 驗證每個指標都符合 IndicatorResponse 格式
      Object.entries(result.indicators).forEach(([indicatorType, indicatorData]) => {
        expect(typeof indicatorType).toBe('string');
        expect(typeof indicatorData.symbol).toBe('string');
        expect(typeof indicatorData.indicators).toBe('object');
        expect(typeof indicatorData.period).toBe('number');
        expect(typeof indicatorData.timestamp).toBe('string');
        expect(typeof indicatorData.success).toBe('boolean');
        expect(typeof indicatorData.data_points).toBe('number');

        // 確保關鍵字段不是 undefined
        expect(indicatorData.symbol).not.toBeUndefined();
        expect(indicatorData.success).not.toBeUndefined();
      });
    });

    it('should handle API response unwrapping correctly', async () => {
      // 測試 API 響應解包是否正確處理
      const params = {
        stock_id: 1,
        indicator_types: ['RSI'],
        timeframe: '1d' as const
      };

      // 測試兩種可能的響應格式
      const scenarios = [
        {
          name: '直接響應格式',
          mockResponse: {
            stock_id: 1,
            symbol: 'AAPL',
            timeframe: '1d',
            indicators: {
              RSI: {
                symbol: 'AAPL',
                indicators: { rsi: 65.5 },
                period: 14,
                timestamp: '2024-01-01T12:00:00Z',
                success: true,
                data_points: 30
              }
            }
          }
        },
        {
          name: '包裝在 data 字段中的響應格式',
          mockResponse: {
            data: {
              stock_id: 1,
              symbol: 'AAPL',
              timeframe: '1d',
              indicators: {
                RSI: {
                  symbol: 'AAPL',
                  indicators: { rsi: 65.5 },
                  period: 14,
                  timestamp: '2024-01-01T12:00:00Z',
                  success: true,
                  data_points: 30
                }
              }
            }
          }
        }
      ];

      for (const scenario of scenarios) {
        mockApiService.get.mockResolvedValue(scenario.mockResponse);

        const result = await IndicatorsApiService.getIndicators(params);

        // 無論是哪種格式，結果都應該包含必需的字段且不為 undefined
        expect(result.stock_id).toBeDefined();
        expect(result.stock_id).not.toBeUndefined();
        expect(result.symbol).toBeDefined();
        expect(result.symbol).not.toBeUndefined();
        expect(result.timeframe).toBeDefined();
        expect(result.timeframe).not.toBeUndefined();
        expect(result.indicators).toBeDefined();
        expect(result.indicators).not.toBeUndefined();

        console.log(`✓ ${scenario.name} 測試通過`);
      }
    });
  });
});
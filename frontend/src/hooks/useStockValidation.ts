/**
 * 股號驗證 Hook
 * 可重用的股票代號驗證邏輯
 */
import { useState, useCallback } from 'react';
import {
  validateStockSymbol,
  validateStockSymbolAuto,
  StockValidationResult,
} from '../services/stockValidationApi';

interface UseStockValidationResult {
  isValidating: boolean;
  validationError: string | null;
  validatedStock: StockValidationResult | null;
  validate: (symbol: string, market?: 'TW' | 'US') => Promise<StockValidationResult | null>;
  reset: () => void;
}

/**
 * 股號驗證 Hook
 * @returns 驗證狀態和方法
 */
export function useStockValidation(): UseStockValidationResult {
  const [isValidating, setIsValidating] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [validatedStock, setValidatedStock] = useState<StockValidationResult | null>(null);

  const validate = useCallback(async (
    symbol: string,
    market?: 'TW' | 'US'
  ): Promise<StockValidationResult | null> => {
    if (!symbol || !symbol.trim()) {
      setValidationError('請輸入股票代號');
      return null;
    }

    setIsValidating(true);
    setValidationError(null);
    setValidatedStock(null);

    try {
      let result: StockValidationResult;

      if (market) {
        result = await validateStockSymbol(symbol, market);
      } else {
        result = await validateStockSymbolAuto(symbol);
      }

      setValidatedStock(result);
      return result;
    } catch (error: any) {
      const errorMessage = error.message || '驗證股票代號失敗';
      setValidationError(errorMessage);
      return null;
    } finally {
      setIsValidating(false);
    }
  }, []);

  const reset = useCallback(() => {
    setValidationError(null);
    setValidatedStock(null);
    setIsValidating(false);
  }, []);

  return {
    isValidating,
    validationError,
    validatedStock,
    validate,
    reset,
  };
}

export default useStockValidation;

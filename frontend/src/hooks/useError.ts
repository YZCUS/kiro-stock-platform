/**
 * 錯誤處理 Hook
 */
import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '../store';
import { 
  setGlobalError, 
  setComponentError, 
  clearComponentError,
  clearAllErrors
} from '../store/slices/uiSlice';
import { useToast } from './useToast';

export const useError = (component?: string) => {
  const dispatch = useAppDispatch();
  const { error: toastError } = useToast();
  
  const error = useAppSelector(state => {
    if (component) {
      return state.ui.errors.components[component] || null;
    }
    return state.ui.errors.global;
  });

  const setError = useCallback((errorMessage: string | null, showToast = false) => {
    if (component) {
      dispatch(setComponentError({ component, error: errorMessage }));
    } else {
      dispatch(setGlobalError(errorMessage));
    }

    // 可選擇是否顯示 toast 通知
    if (showToast && errorMessage) {
      toastError('錯誤', errorMessage);
    }
  }, [dispatch, component, toastError]);

  const clearError = useCallback(() => {
    if (component) {
      dispatch(clearComponentError(component));
    } else {
      dispatch(setGlobalError(null));
    }
  }, [dispatch, component]);

  const clearAll = useCallback(() => {
    dispatch(clearAllErrors());
  }, [dispatch]);

  // 錯誤處理包裝器
  const withErrorHandling = useCallback(async <T>(
    promise: Promise<T>,
    options: {
      showToast?: boolean;
      fallbackValue?: T;
      onError?: (error: Error) => void;
    } = {}
  ): Promise<T | undefined> => {
    const { showToast = true, fallbackValue, onError } = options;
    
    try {
      clearError();
      const result = await promise;
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '未知錯誤';
      setError(errorMessage, showToast);
      
      if (onError && err instanceof Error) {
        onError(err);
      }
      
      return fallbackValue;
    }
  }, [setError, clearError]);

  return {
    error,
    setError,
    clearError,
    clearAll,
    withErrorHandling,
  };
};
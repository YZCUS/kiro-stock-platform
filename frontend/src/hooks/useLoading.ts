/**
 * 載入狀態管理 Hook
 */
import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '../store';
import { 
  setGlobalLoading, 
  setComponentLoading, 
  clearComponentLoading 
} from '../store/slices/uiSlice';

export const useLoading = (component?: string) => {
  const dispatch = useAppDispatch();
  
  const isLoading = useAppSelector(state => {
    if (component) {
      return state.ui.loading.components[component] || false;
    }
    return state.ui.loading.global;
  });

  const setLoading = useCallback((loading: boolean) => {
    if (component) {
      dispatch(setComponentLoading({ component, loading }));
    } else {
      dispatch(setGlobalLoading(loading));
    }
  }, [dispatch, component]);

  const clearLoading = useCallback(() => {
    if (component) {
      dispatch(clearComponentLoading(component));
    } else {
      dispatch(setGlobalLoading(false));
    }
  }, [dispatch, component]);

  // 自動載入包裝器
  const withLoading = useCallback(async <T>(promise: Promise<T>): Promise<T> => {
    setLoading(true);
    try {
      const result = await promise;
      return result;
    } finally {
      setLoading(false);
    }
  }, [setLoading]);

  return {
    isLoading,
    setLoading,
    clearLoading,
    withLoading,
  };
};
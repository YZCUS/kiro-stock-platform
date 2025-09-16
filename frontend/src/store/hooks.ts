/**
 * Redux Hooks 定義
 */
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';
import type { RootState, AppDispatch } from './index';

// 使用這些 hooks 替代標準的 useDispatch 和 useSelector
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

// 便利 hooks for specific state slices
export const useStocks = () => useAppSelector(state => state.stocks);
export const useSignals = () => useAppSelector(state => state.signals);
export const useIndicators = () => useAppSelector(state => state.indicators);
export const useUI = () => useAppSelector(state => state.ui);

// 便利 hooks for loading states
export const useIsLoading = () => {
  const stocksLoading = useAppSelector(state => state.stocks.loading);
  const signalsLoading = useAppSelector(state => state.signals.loading);
  const indicatorsLoading = useAppSelector(state => state.indicators.loading);
  const globalLoading = useAppSelector(state => state.ui.globalLoading);

  return stocksLoading || signalsLoading || indicatorsLoading || globalLoading;
};

// 便利 hooks for error states
export const useHasErrors = () => {
  const stocksError = useAppSelector(state => state.stocks.error);
  const signalsError = useAppSelector(state => state.signals.error);
  const indicatorsError = useAppSelector(state => state.indicators.error);
  const globalError = useAppSelector(state => state.ui.errors.global);

  return !!(stocksError || signalsError || indicatorsError || globalError);
};
/**
 * Toast 通知 Hook
 */
import { useCallback } from 'react';
import { useAppDispatch } from '../store';
import { addToast, removeToast, clearToasts } from '../store/slices/uiSlice';
import type { ToastMessage } from '../store/slices/uiSlice';

export const useToast = () => {
  const dispatch = useAppDispatch();

  const toast = useCallback((message: Omit<ToastMessage, 'id'>) => {
    const result = dispatch(addToast(message));
    const id = Date.now().toString(); // Fallback ID

    // 自動移除 toast
    if (message.duration !== 0) {
      setTimeout(() => {
        dispatch(removeToast(id));
      }, message.duration || 5000);
    }

    return id;
  }, [dispatch]);

  const success = useCallback((title: string, message?: string, duration?: number) => {
    return toast({
      type: 'success',
      title,
      message,
      duration,
    });
  }, [toast]);

  const error = useCallback((title: string, message?: string, duration?: number) => {
    return toast({
      type: 'error',
      title,
      message,
      duration: duration || 7000, // 錯誤訊息顯示更久
    });
  }, [toast]);

  const warning = useCallback((title: string, message?: string, duration?: number) => {
    return toast({
      type: 'warning',
      title,
      message,
      duration,
    });
  }, [toast]);

  const info = useCallback((title: string, message?: string, duration?: number) => {
    return toast({
      type: 'info',
      title,
      message,
      duration,
    });
  }, [toast]);

  const dismiss = useCallback((id: string) => {
    dispatch(removeToast(id));
  }, [dispatch]);

  const dismissAll = useCallback(() => {
    dispatch(clearToasts());
  }, [dispatch]);

  return {
    toast,
    success,
    error,
    warning,
    info,
    dismiss,
    dismissAll,
  };
};
/**
 * Toast 通知組件
 */
'use client';

import React, { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '../../store';
import { removeToast } from '../../store/slices/uiSlice';

const Toast: React.FC = () => {
  const dispatch = useAppDispatch();
  const toasts = useAppSelector(state => state.ui.toasts);

  useEffect(() => {
    toasts.forEach(toast => {
      if (toast.duration && toast.duration > 0) {
        const timer = setTimeout(() => {
          dispatch(removeToast(toast.id));
        }, toast.duration);

        return () => clearTimeout(timer);
      }
    });
  }, [toasts, dispatch]);

  if (toasts.length === 0) {
    return null;
  }

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`max-w-sm w-full shadow-lg rounded-lg pointer-events-auto ring-1 ring-black ring-opacity-5 overflow-hidden ${
            toast.type === 'success'
              ? 'bg-green-50 ring-green-500'
              : toast.type === 'error'
              ? 'bg-red-50 ring-red-500'
              : toast.type === 'warning'
              ? 'bg-yellow-50 ring-yellow-500'
              : 'bg-blue-50 ring-blue-500'
          }`}
        >
          <div className="p-4">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                {/* 圖標 */}
                {toast.type === 'success' && (
                  <svg className="h-6 w-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )}
                {toast.type === 'error' && (
                  <svg className="h-6 w-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
                {toast.type === 'warning' && (
                  <svg className="h-6 w-6 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.268 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                )}
                {toast.type === 'info' && (
                  <svg className="h-6 w-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
              </div>
              <div className="ml-3 w-0 flex-1 pt-0.5">
                <p className={`text-sm font-medium ${
                  toast.type === 'success'
                    ? 'text-green-900'
                    : toast.type === 'error'
                    ? 'text-red-900'
                    : toast.type === 'warning'
                    ? 'text-yellow-900'
                    : 'text-blue-900'
                }`}>
                  {toast.title}
                </p>
                {toast.message && (
                  <p className={`mt-1 text-sm ${
                    toast.type === 'success'
                      ? 'text-green-700'
                      : toast.type === 'error'
                      ? 'text-red-700'
                      : toast.type === 'warning'
                      ? 'text-yellow-700'
                      : 'text-blue-700'
                  }`}>
                    {toast.message}
                  </p>
                )}
              </div>
              <div className="ml-4 flex-shrink-0 flex">
                <button
                  onClick={() => dispatch(removeToast(toast.id))}
                  className={`rounded-md inline-flex ${
                    toast.type === 'success'
                      ? 'text-green-400 hover:text-green-500 focus:ring-green-600'
                      : toast.type === 'error'
                      ? 'text-red-400 hover:text-red-500 focus:ring-red-600'
                      : toast.type === 'warning'
                      ? 'text-yellow-400 hover:text-yellow-500 focus:ring-yellow-600'
                      : 'text-blue-400 hover:text-blue-500 focus:ring-blue-600'
                  } focus:outline-none focus:ring-2 focus:ring-offset-2`}
                >
                  <span className="sr-only">關閉</span>
                  <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default Toast;
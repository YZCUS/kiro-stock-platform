import React from 'react';
import { act, render, screen } from '@testing-library/react';
import { configureStore } from '@reduxjs/toolkit';
import { Provider } from 'react-redux';

import Toast from '../Toast';
import uiReducer, { addToast } from '../../../store/slices/uiSlice';
import type { ToastMessage } from '../../../types';

const makeStore = (toasts: ToastMessage[]) => {
  const uiState = uiReducer(undefined, { type: 'test/init' });

  return configureStore({
    reducer: { ui: uiReducer },
    preloadedState: {
      ui: {
        ...uiState,
        toasts,
      },
    },
  });
};

const renderToast = (toasts: ToastMessage[]) => {
  const store = makeStore(toasts);
  const result = render(
    <Provider store={store}>
      <Toast />
    </Provider>
  );

  return { store, ...result };
};

describe('Toast', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    act(() => {
      jest.runOnlyPendingTimers();
    });
    jest.useRealTimers();
  });

  it('keeps an always-mounted polite live region for notifications', () => {
    renderToast([]);

    const region = screen.getByRole('region', { name: '通知' });
    expect(region).toHaveAttribute('aria-live', 'polite');
    expect(region).toHaveAttribute('aria-atomic', 'false');
    expect(region).toHaveAttribute('aria-relevant', 'additions text');
  });

  it('does not restart an existing toast timer when another toast is added', () => {
    const { store } = renderToast([
      {
        id: 'first',
        type: 'info',
        title: 'First toast',
        duration: 1000,
      },
    ]);

    act(() => {
      jest.advanceTimersByTime(600);
      store.dispatch(addToast({
        type: 'success',
        title: 'Second toast',
        duration: 5000,
      }));
    });

    act(() => {
      jest.advanceTimersByTime(400);
    });

    expect(store.getState().ui.toasts.map((toast) => toast.id)).not.toContain('first');
    expect(screen.queryByText('First toast')).not.toBeInTheDocument();
    expect(screen.getByText('Second toast')).toBeInTheDocument();
  });

  it('clears the timer when a toast unmounts', () => {
    const { store, unmount } = renderToast([
      {
        id: 'persistent-after-unmount',
        type: 'warning',
        title: 'Unmounted toast',
        duration: 1000,
      },
    ]);

    unmount();

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(store.getState().ui.toasts).toHaveLength(1);
  });
});

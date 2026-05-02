'use client';

import { useEffect } from 'react';
import { useAppDispatch } from '@/store';
import { authInitialized, restoreAuth } from '@/store/slices/authSlice';

export default function AuthInit() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    // Restore auth state from localStorage on mount
    let restored = false;

    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token');
      const userStr = localStorage.getItem('user');

      if (token && userStr) {
        try {
          const user = JSON.parse(userStr);
          dispatch(restoreAuth({ user, token }));
          restored = true;
        } catch {
          // Clear invalid data
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      }
    }

    if (!restored) {
      dispatch(authInitialized());
    }
  }, [dispatch]);

  return null;
}

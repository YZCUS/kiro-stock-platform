'use client';

import { useEffect } from 'react';
import { useAppDispatch } from '@/store';
import { restoreAuth } from '@/store/slices/authSlice';

export default function AuthInit() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    // Restore auth state from localStorage on mount
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token');
      const userStr = localStorage.getItem('user');

      if (token && userStr) {
        try {
          const user = JSON.parse(userStr);
          dispatch(restoreAuth({ user, token }));
        } catch (err) {
          // Clear invalid data
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      }
    }
  }, [dispatch]);

  return null;
}

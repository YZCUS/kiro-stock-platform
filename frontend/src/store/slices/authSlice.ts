/**
 * Auth Redux Slice
 */
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { UserResponse } from '@/services/authApi';

interface AuthState {
  isAuthenticated: boolean;
  initialized: boolean;
  user: UserResponse | null;
  token: string | null;
  loading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  isAuthenticated: false,
  initialized: false,
  user: null,
  token: null,
  loading: false,
  error: null,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setAuthLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setAuthError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
      state.loading = false;
    },
    authInitialized: (state) => {
      state.initialized = true;
    },
    loginSuccess: (state, action: PayloadAction<{ user: UserResponse; token: string }>) => {
      state.isAuthenticated = true;
      state.initialized = true;
      state.user = action.payload.user;
      state.token = action.payload.token;
      state.loading = false;
      state.error = null;
      // Store token in localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('token', action.payload.token);
        localStorage.setItem('user', JSON.stringify(action.payload.user));
      }
    },
    logout: (state) => {
      state.isAuthenticated = false;
      state.initialized = true;
      state.user = null;
      state.token = null;
      state.loading = false;
      state.error = null;
      // Remove token from localStorage
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      }
    },
    restoreAuth: (state, action: PayloadAction<{ user: UserResponse; token: string }>) => {
      state.isAuthenticated = true;
      state.initialized = true;
      state.user = action.payload.user;
      state.token = action.payload.token;
    },
  },
});

export const {
  setAuthLoading,
  setAuthError,
  authInitialized,
  loginSuccess,
  logout,
  restoreAuth,
} = authSlice.actions;

export default authSlice.reducer;

/**
 * Auth API Service
 */
import { apiClient, API_ENDPOINTS } from '@/lib/api';

export interface UserRegister {
  email: string;
  username: string;
  password: string;
}

export interface UserLogin {
  username: string;
  password: string;
}

export interface UserResponse {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface PasswordChange {
  old_password: string;
  new_password: string;
}

/**
 * Register a new user
 */
export const register = async (data: UserRegister): Promise<TokenResponse> => {
  const response = await apiClient.post<TokenResponse>(
    API_ENDPOINTS.AUTH.REGISTER,
    data
  );
  return response.data;
};

/**
 * Login user
 */
export const login = async (data: UserLogin): Promise<TokenResponse> => {
  const response = await apiClient.post<TokenResponse>(
    API_ENDPOINTS.AUTH.LOGIN,
    data
  );
  return response.data;
};

/**
 * Get current user info
 */
export const getCurrentUser = async (token: string): Promise<UserResponse> => {
  const response = await apiClient.get<UserResponse>(
    API_ENDPOINTS.AUTH.ME,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
  return response.data;
};

/**
 * Change password
 */
export const changePassword = async (
  data: PasswordChange,
  token: string
): Promise<{ message: string }> => {
  const response = await apiClient.post(
    API_ENDPOINTS.AUTH.CHANGE_PASSWORD,
    data,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
  return response.data;
};

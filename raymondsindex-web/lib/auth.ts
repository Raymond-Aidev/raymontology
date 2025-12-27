import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// API URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://raymontology-production.up.railway.app/api';

// 토큰 저장소 키
const AUTH_TOKEN_KEY = 'auth_token';

// 토큰 유틸리티 함수
export const getToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(AUTH_TOKEN_KEY);
};

export const setToken = (token: string): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem(AUTH_TOKEN_KEY, token);
};

export const removeToken = (): void => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(AUTH_TOKEN_KEY);
};

// 사용자 타입
export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  subscription_tier: string | null;
  subscription_expires_at: string | null;
  created_at: string;
}

// 로그인 자격 증명
export interface LoginCredentials {
  email: string;
  password: string;
}

// 회원가입 데이터
export interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

// 인증 스토어 상태
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (credentials: LoginCredentials) => Promise<boolean>;
  register: (data: RegisterData) => Promise<boolean>;
  logout: () => void;
  checkAuth: () => Promise<boolean>;
  clearError: () => void;
  setToken: (token: string) => void;
}

const initialState = {
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
};

// API 호출 헬퍼
async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      ...initialState,

      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true, error: null });

        try {
          const { access_token } = await apiCall<{ access_token: string }>(
            '/auth/login',
            {
              method: 'POST',
              body: JSON.stringify(credentials),
            }
          );

          setToken(access_token);
          set({ token: access_token });

          // 사용자 정보 조회
          const user = await apiCall<User>('/auth/me', {
            headers: { Authorization: `Bearer ${access_token}` },
          });

          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          });
          return true;
        } catch (err) {
          const message = err instanceof Error ? err.message : '로그인에 실패했습니다';
          set({
            error: message,
            isLoading: false,
          });
          return false;
        }
      },

      register: async (data: RegisterData) => {
        set({ isLoading: true, error: null });

        try {
          await apiCall('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data),
          });

          set({
            isLoading: false,
            error: null,
          });
          return true;
        } catch (err) {
          const message = err instanceof Error ? err.message : '회원가입에 실패했습니다';
          set({
            error: message,
            isLoading: false,
          });
          return false;
        }
      },

      logout: () => {
        removeToken();
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          error: null,
        });
      },

      checkAuth: async () => {
        const { token } = get();
        if (!token) {
          set({ isAuthenticated: false, user: null });
          return false;
        }

        set({ isLoading: true });

        try {
          const user = await apiCall<User>('/auth/me', {
            headers: { Authorization: `Bearer ${token}` },
          });

          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          });
          return true;
        } catch {
          removeToken();
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
          });
          return false;
        }
      },

      clearError: () => set({ error: null }),

      setToken: (token: string) => {
        setToken(token);
        set({ token });
      },
    }),
    {
      name: 'raymondsindex-auth',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// 유틸리티 셀렉터
export const selectIsAdmin = (state: AuthState) => state.user?.is_superuser === true;
export const selectUserName = (state: AuthState) => state.user?.full_name || state.user?.username || '사용자';

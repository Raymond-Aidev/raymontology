import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import apiClient, { setToken as saveToken, removeToken } from '../api/client'

// 사용자 타입 (백엔드 UserMe 스키마와 일치)
export interface User {
  id: string
  email: string
  username: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
  created_at: string
}

// 로그인 자격 증명
export interface LoginCredentials {
  email: string
  password: string
}

// 회원가입 데이터
export interface RegisterData {
  email: string
  username: string
  password: string
  full_name?: string
}

// 인증 스토어 상태
interface AuthState {
  // 사용자 정보
  user: User | null
  token: string | null
  isAuthenticated: boolean

  // 로딩/에러 상태
  isLoading: boolean
  error: string | null

  // 액션
  login: (credentials: LoginCredentials) => Promise<boolean>
  register: (data: RegisterData) => Promise<boolean>
  logout: () => void
  checkAuth: () => Promise<void>
  updateUser: (user: Partial<User>) => void
  clearError: () => void
  setToken: (token: string) => void

  // 초기화
  reset: () => void
}

const initialState = {
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      ...initialState,

      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true, error: null })

        try {
          // 실제 API 호출
          const response = await apiClient.post('/api/auth/login', credentials)
          const { access_token } = response.data

          // 토큰 저장 (localStorage + Zustand)
          saveToken(access_token)
          set({ token: access_token })

          // 사용자 정보 조회
          const userResponse = await apiClient.get('/api/auth/me', {
            headers: { Authorization: `Bearer ${access_token}` }
          })

          set({
            user: userResponse.data,
            isAuthenticated: true,
            isLoading: false,
          })
          return true
        } catch (err: unknown) {
          const error = err as { response?: { data?: { detail?: string } } }
          const message = error.response?.data?.detail || '로그인에 실패했습니다'
          set({
            error: message,
            isLoading: false,
          })
          return false
        }
      },

      register: async (data: RegisterData) => {
        set({ isLoading: true, error: null })

        try {
          // 실제 API 호출
          const response = await apiClient.post('/api/auth/register', data)
          const { access_token } = response.data

          // 토큰 저장 (localStorage + Zustand)
          saveToken(access_token)
          set({ token: access_token })

          // 사용자 정보 조회
          const userResponse = await apiClient.get('/api/auth/me', {
            headers: { Authorization: `Bearer ${access_token}` }
          })

          set({
            user: userResponse.data,
            isAuthenticated: true,
            isLoading: false,
          })
          return true
        } catch (err: unknown) {
          const error = err as { response?: { data?: { detail?: string } } }
          const message = error.response?.data?.detail || '회원가입에 실패했습니다'
          set({
            error: message,
            isLoading: false,
          })
          return false
        }
      },

      logout: () => {
        removeToken()
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          error: null,
        })
      },

      checkAuth: async () => {
        const { token } = get()
        if (!token) {
          set({ isAuthenticated: false, user: null })
          return
        }

        set({ isLoading: true })

        try {
          // 토큰으로 사용자 정보 조회
          const response = await apiClient.get('/api/auth/me', {
            headers: { Authorization: `Bearer ${token}` }
          })

          set({
            user: response.data,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch {
          // 토큰이 유효하지 않으면 로그아웃
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
          })
        }
      },

      updateUser: (userData) => set((state) => ({
        user: state.user ? { ...state.user, ...userData } : null,
      })),

      clearError: () => set({ error: null }),

      setToken: (token: string) => set({ token }),

      reset: () => set(initialState),
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

// 유틸리티 셀렉터
export const selectIsAdmin = (state: AuthState) => state.user?.is_superuser === true
export const selectUserName = (state: AuthState) => state.user?.full_name || state.user?.username || '사용자'
export const selectUserEmail = (state: AuthState) => state.user?.email || ''

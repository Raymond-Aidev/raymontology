import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// 사용자 타입
export interface User {
  id: string
  email: string
  name: string
  role: 'user' | 'admin'
  avatar?: string
  createdAt: string
}

// 로그인 자격 증명
export interface LoginCredentials {
  email: string
  password: string
}

// 회원가입 데이터
export interface RegisterData {
  email: string
  password: string
  name: string
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
          // TODO: 실제 API 호출로 교체
          // const response = await apiClient.post('/auth/login', credentials)
          // const { user, token } = response.data

          // Mock 로그인 (개발용)
          await new Promise(resolve => setTimeout(resolve, 500))

          if (credentials.email === 'admin@test.com' && credentials.password === 'password') {
            const mockUser: User = {
              id: '1',
              email: credentials.email,
              name: '관리자',
              role: 'admin',
              createdAt: new Date().toISOString(),
            }
            const mockToken = 'mock-jwt-token-12345'

            set({
              user: mockUser,
              token: mockToken,
              isAuthenticated: true,
              isLoading: false,
            })
            return true
          } else if (credentials.email && credentials.password) {
            // 일반 사용자 Mock
            const mockUser: User = {
              id: '2',
              email: credentials.email,
              name: credentials.email.split('@')[0],
              role: 'user',
              createdAt: new Date().toISOString(),
            }
            const mockToken = 'mock-jwt-token-user-' + Date.now()

            set({
              user: mockUser,
              token: mockToken,
              isAuthenticated: true,
              isLoading: false,
            })
            return true
          }

          throw new Error('이메일 또는 비밀번호가 올바르지 않습니다')
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : '로그인에 실패했습니다',
            isLoading: false,
          })
          return false
        }
      },

      register: async (data: RegisterData) => {
        set({ isLoading: true, error: null })

        try {
          // TODO: 실제 API 호출로 교체
          // const response = await apiClient.post('/auth/register', data)

          // Mock 회원가입
          await new Promise(resolve => setTimeout(resolve, 500))

          // 이메일 중복 검사 (Mock)
          if (data.email === 'admin@test.com') {
            throw new Error('이미 사용 중인 이메일입니다')
          }

          const mockUser: User = {
            id: String(Date.now()),
            email: data.email,
            name: data.name,
            role: 'user',
            createdAt: new Date().toISOString(),
          }
          const mockToken = 'mock-jwt-token-' + Date.now()

          set({
            user: mockUser,
            token: mockToken,
            isAuthenticated: true,
            isLoading: false,
          })
          return true
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : '회원가입에 실패했습니다',
            isLoading: false,
          })
          return false
        }
      },

      logout: () => {
        // 토큰 제거
        localStorage.removeItem('auth-store')

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
          set({ isAuthenticated: false })
          return
        }

        set({ isLoading: true })

        try {
          // TODO: 실제 API 호출로 교체
          // const response = await apiClient.get('/auth/me')
          // set({ user: response.data, isAuthenticated: true })

          // Mock 토큰 검증
          await new Promise(resolve => setTimeout(resolve, 200))

          // 토큰이 있으면 인증된 것으로 처리 (Mock)
          set({ isLoading: false, isAuthenticated: true })
        } catch {
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
export const selectIsAdmin = (state: AuthState) => state.user?.role === 'admin'
export const selectUserName = (state: AuthState) => state.user?.name || '게스트'
export const selectUserEmail = (state: AuthState) => state.user?.email || ''

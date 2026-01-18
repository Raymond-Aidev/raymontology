import axios from 'axios'

// API 기본 URL 설정
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// 토큰 저장소 키
export const AUTH_TOKEN_KEY = 'auth_token'

// 토큰 유틸리티 함수
export const getToken = (): string | null => {
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

export const setToken = (token: string): void => {
  localStorage.setItem(AUTH_TOKEN_KEY, token)
}

export const removeToken = (): void => {
  localStorage.removeItem(AUTH_TOKEN_KEY)
}

// Axios 인스턴스 생성
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 요청 인터셉터
apiClient.interceptors.request.use(
  (config) => {
    // localStorage에서 토큰 가져오기
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 응답 인터셉터
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // 401 에러 시 토큰 제거
    if (error.response?.status === 401) {
      removeToken()
      localStorage.removeItem('auth-store')

      // Protected 경로에서만 로그인 페이지로 리다이렉트
      // Public 페이지(메인, 소개, 가격 등)에서는 리다이렉트하지 않음
      const PROTECTED_PATH_PREFIXES = ['/company/', '/service-application']
      const currentPath = window.location.pathname
      const isProtectedPath = PROTECTED_PATH_PREFIXES.some(
        prefix => currentPath.startsWith(prefix)
      )

      if (isProtectedPath && currentPath !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient

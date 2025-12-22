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
    // 401 에러 시 토큰 제거 및 리다이렉트
    if (error.response?.status === 401) {
      removeToken()
      localStorage.removeItem('auth-store')
      // 로그인 페이지가 아닌 경우에만 리다이렉트
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient

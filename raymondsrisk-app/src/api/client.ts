import axios from 'axios'

// API 기본 URL 설정
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://raymontology-production.up.railway.app'

// 토큰 저장소 키 (authService.ts와 동일)
export const AUTH_TOKEN_KEY = 'raymondsrisk_access_token'

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
    if (error.response?.status === 401) {
      removeToken()
      localStorage.removeItem('auth-store')
    }
    return Promise.reject(error)
  }
)

export default apiClient

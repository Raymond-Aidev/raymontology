import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

// API 기본 URL 설정
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://raymontology-production.up.railway.app'

// 토큰 저장소 키 (authService.ts와 동일)
export const AUTH_TOKEN_KEY = 'raymondsrisk_access_token'
const REFRESH_TOKEN_KEY = 'raymondsrisk_refresh_token'

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

export const getRefreshToken = (): string | null => {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export const setRefreshToken = (token: string): void => {
  localStorage.setItem(REFRESH_TOKEN_KEY, token)
}

// Axios 인스턴스 생성
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,  // 30초로 증가 (리포트 API가 느릴 수 있음)
  headers: {
    'Content-Type': 'application/json',
  },
})

// 토큰 갱신 중 플래그 (중복 갱신 방지)
let isRefreshing = false
// 갱신 대기 중인 요청들
let refreshSubscribers: ((token: string) => void)[] = []

// 갱신 완료 후 대기 중인 요청들 재실행
const onRefreshed = (newToken: string) => {
  refreshSubscribers.forEach(callback => callback(newToken))
  refreshSubscribers = []
}

// 갱신 대기열에 요청 추가
const addRefreshSubscriber = (callback: (token: string) => void) => {
  refreshSubscribers.push(callback)
}

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

// 응답 인터셉터 (401 시 토큰 자동 갱신)
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // 401 에러이고, 재시도가 아닌 경우
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      // 토큰 갱신 API 자체의 401은 재시도하지 않음
      if (originalRequest.url?.includes('/auth/toss/refresh')) {
        removeToken()
        localStorage.removeItem(REFRESH_TOKEN_KEY)
        window.dispatchEvent(new CustomEvent('auth:unauthorized'))
        return Promise.reject(error)
      }

      const refreshToken = getRefreshToken()

      // 리프레시 토큰이 없으면 로그아웃
      if (!refreshToken) {
        removeToken()
        window.dispatchEvent(new CustomEvent('auth:unauthorized'))
        return Promise.reject(error)
      }

      // 이미 갱신 중이면 대기열에 추가
      if (isRefreshing) {
        return new Promise((resolve) => {
          addRefreshSubscriber((newToken: string) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            resolve(apiClient(originalRequest))
          })
        })
      }

      // 토큰 갱신 시작
      originalRequest._retry = true
      isRefreshing = true

      try {
        console.log('[apiClient] Refreshing token...')
        const response = await axios.post(
          `${API_BASE_URL}/api/auth/toss/refresh`,
          { refreshToken },
          { headers: { 'Content-Type': 'application/json' } }
        )

        const { accessToken, refreshToken: newRefreshToken } = response.data

        // 새 토큰 저장
        setToken(accessToken)
        setRefreshToken(newRefreshToken)

        console.log('[apiClient] Token refreshed successfully')

        // 대기 중인 요청들 처리
        onRefreshed(accessToken)

        // 원래 요청 재시도
        originalRequest.headers.Authorization = `Bearer ${accessToken}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        console.error('[apiClient] Token refresh failed:', refreshError)
        // 갱신 실패 → 로그아웃
        removeToken()
        localStorage.removeItem(REFRESH_TOKEN_KEY)
        window.dispatchEvent(new CustomEvent('auth:unauthorized'))
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient

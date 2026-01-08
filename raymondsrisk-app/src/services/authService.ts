import type { TokenResponse, UserInfoResponse, CreditInfo, TossUser } from '../types/auth'
import apiClient from '../api/client'

// 로컬 스토리지 키
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'raymondsrisk_access_token',
  REFRESH_TOKEN: 'raymondsrisk_refresh_token',
  USER_KEY: 'raymondsrisk_user_key',
  USER_INFO: 'raymondsrisk_user_info',
}

/**
 * 토스 로그인 인가 코드로 토큰 발급
 * 서버에서 토스 API를 호출하여 토큰 발급
 */
export async function exchangeCodeForToken(
  authorizationCode: string,
  referrer: string
): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/api/auth/toss/token', {
    authorizationCode,
    referrer,
  })

  // 토큰 저장
  localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, response.data.accessToken)
  localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, response.data.refreshToken)

  return response.data
}

/**
 * 토큰으로 사용자 정보 조회
 */
export async function fetchUserInfo(): Promise<TossUser> {
  const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)

  if (!accessToken) {
    throw new Error('No access token')
  }

  const response = await apiClient.get<UserInfoResponse>('/api/auth/toss/me', {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })

  const user: TossUser = {
    userKey: response.data.userKey,
    name: response.data.encryptedUserInfo?.name,
    phone: response.data.encryptedUserInfo?.phone,
    email: response.data.encryptedUserInfo?.email,
  }

  // 사용자 정보 저장
  localStorage.setItem(STORAGE_KEYS.USER_KEY, user.userKey)
  localStorage.setItem(STORAGE_KEYS.USER_INFO, JSON.stringify(user))

  return user
}

/**
 * 이용권(크레딧) 조회
 */
export async function fetchCredits(): Promise<CreditInfo> {
  const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)

  if (!accessToken) {
    throw new Error('No access token')
  }

  const response = await apiClient.get<CreditInfo>('/api/credits/balance', {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })

  return response.data
}

/**
 * 로그아웃
 */
export async function logout(): Promise<void> {
  const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)

  if (accessToken) {
    try {
      await apiClient.post('/api/auth/toss/logout', null, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })
    } catch {
      // 서버 로그아웃 실패해도 로컬은 정리
      console.warn('Server logout failed, clearing local storage')
    }
  }

  // 로컬 스토리지 정리
  Object.values(STORAGE_KEYS).forEach(key => {
    localStorage.removeItem(key)
  })
}

/**
 * 저장된 인증 정보 복원
 */
export function restoreAuth(): { user: TossUser | null; accessToken: string | null } {
  const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)
  const userInfoStr = localStorage.getItem(STORAGE_KEYS.USER_INFO)

  if (!accessToken || !userInfoStr) {
    return { user: null, accessToken: null }
  }

  try {
    const user = JSON.parse(userInfoStr) as TossUser
    return { user, accessToken }
  } catch {
    return { user: null, accessToken: null }
  }
}

/**
 * 저장된 토큰이 서버에서 유효한지 검증
 * 토스 앱에서 연동 해제 시 서버 토큰이 무효화되므로 이를 감지
 */
export async function validateStoredToken(): Promise<boolean> {
  const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)

  if (!accessToken) {
    return false
  }

  try {
    // /api/auth/toss/me 엔드포인트로 토큰 유효성 확인
    // 토큰이 무효화되었으면 401 반환
    await apiClient.get('/api/auth/toss/me', {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    })
    return true
  } catch (error) {
    // 401 Unauthorized = 토큰 무효화됨 (연동 해제)
    // 네트워크 오류 등 다른 에러는 일단 유효한 것으로 처리 (오프라인 대응)
    if (error && typeof error === 'object' && 'response' in error) {
      const axiosError = error as { response?: { status: number } }
      if (axiosError.response?.status === 401) {
        // 토큰 무효화됨 - localStorage 정리
        clearAuth()
        return false
      }
    }
    // 네트워크 오류 등은 일단 유효하다고 가정
    return true
  }
}

/**
 * 로컬 인증 정보 정리 (서버 호출 없이)
 */
export function clearAuth(): void {
  Object.values(STORAGE_KEYS).forEach(key => {
    localStorage.removeItem(key)
  })
}

/**
 * 인증 상태 확인
 */
export function isAuthenticated(): boolean {
  const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)
  const userKey = localStorage.getItem(STORAGE_KEYS.USER_KEY)
  return !!(accessToken && userKey)
}

/**
 * 토큰 갱신
 */
export async function refreshToken(): Promise<TokenResponse> {
  const refreshTokenValue = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN)

  if (!refreshTokenValue) {
    throw new Error('No refresh token')
  }

  const response = await apiClient.post<TokenResponse>('/api/auth/toss/refresh', {
    refreshToken: refreshTokenValue,
  })

  // 새 토큰 저장
  localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, response.data.accessToken)
  localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, response.data.refreshToken)

  return response.data
}

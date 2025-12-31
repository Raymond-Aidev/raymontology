// 토스 로그인 사용자 정보
export interface TossUser {
  userKey: string
  name?: string
  phone?: string
  email?: string
}

// 인증 상태
export interface AuthState {
  isAuthenticated: boolean
  isLoading: boolean
  user: TossUser | null
  credits: number
  error: string | null
}

// 토스 로그인 응답 (appLogin)
export interface AppLoginResponse {
  authorizationCode: string
  referrer: 'sandbox' | 'DEFAULT'
}

// 토큰 발급 응답
export interface TokenResponse {
  accessToken: string
  refreshToken: string
  expiresIn: number
}

// 사용자 정보 조회 응답
export interface UserInfoResponse {
  userKey: string
  encryptedUserInfo?: {
    name?: string
    phone?: string
    email?: string
  }
}

// 이용권 정보
export interface CreditInfo {
  credits: number
  lastPurchaseAt?: string
}

// 인앱결제 응답
export interface PurchaseResponse {
  success: boolean
  receiptData?: string
}

// 앱인토스 SDK 전역 타입
declare global {
  interface Window {
    AppsInToss?: {
      appLogin: () => Promise<AppLoginResponse>
      purchase: (productId: string) => Promise<PurchaseResponse>
    }
    // SDK 브릿지 관련 타입 (granite 프레임워크가 주입)
    __CONSTANT_HANDLER_MAP?: Record<string, unknown>
    ReactNativeWebView?: {
      postMessage: (message: string) => void
    }
    __GRANITE_NATIVE_EMITTER?: {
      on: (event: string, callback: (data: unknown) => void) => () => void
      emit: (event: string, data: unknown) => void
    }
  }
}

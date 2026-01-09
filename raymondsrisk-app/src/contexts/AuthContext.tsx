import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { appLogin as tossAppLogin, getOperationalEnvironment } from '@apps-in-toss/web-framework'
import type { AuthState } from '../types/auth'
import '../types/auth' // 전역 타입 선언 import
import * as authService from '../services/authService'

interface AuthContextType extends AuthState {
  login: () => Promise<void>
  logout: () => Promise<void>
  refreshCredits: () => Promise<void>
  deductCredit: () => void
}

const defaultState: AuthState = {
  isAuthenticated: false,
  isLoading: true,
  user: null,
  credits: 0,
  error: null,
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(defaultState)

  // 토큰 검증 및 인증 상태 업데이트 함수 (재사용)
  const validateAndRestoreAuth = useCallback(async (isMountedRef: { current: boolean }) => {
    try {
      const { user, accessToken } = authService.restoreAuth()

      if (user && accessToken) {
        // 서버에서 토큰 유효성 검증 (토스 앱에서 연동 해제 시 무효화됨)
        const isValid = await authService.validateStoredToken()
        if (!isMountedRef.current) return

        if (!isValid) {
          setState({ ...defaultState, isLoading: false })
          return
        }

        // 토큰 유효 - 이용권 조회
        try {
          const creditInfo = await authService.fetchCredits()
          if (!isMountedRef.current) return
          setState({
            isAuthenticated: true,
            isLoading: false,
            user,
            credits: creditInfo.credits,
            error: null,
          })
        } catch {
          if (!isMountedRef.current) return
          setState({
            isAuthenticated: true,
            isLoading: false,
            user,
            credits: 0,
            error: null,
          })
        }
      } else {
        if (!isMountedRef.current) return
        setState({ ...defaultState, isLoading: false })
      }
    } catch {
      if (!isMountedRef.current) return
      setState({
        ...defaultState,
        isLoading: false,
      })
    }
  }, [])

  // 초기화: 저장된 인증 정보 복원 + 서버 검증
  useEffect(() => {
    const isMountedRef = { current: true }  // 메모리 릭 방지: 마운트 상태 추적

    validateAndRestoreAuth(isMountedRef)

    return () => {
      isMountedRef.current = false  // cleanup: 언마운트 표시
    }
  }, [validateAndRestoreAuth])

  // 포그라운드 복귀 시 토큰 재검증 (토스 앱에서 연동 해제 감지)
  useEffect(() => {
    const isMountedRef = { current: true }

    const handleVisibilityChange = async () => {
      // 포그라운드로 돌아왔고, 현재 인증된 상태인 경우에만 재검증
      if (document.visibilityState === 'visible' && state.isAuthenticated) {
        const isValid = await authService.validateStoredToken()
        if (!isMountedRef.current) return

        if (!isValid) {
          setState({ ...defaultState, isLoading: false })
        }
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      isMountedRef.current = false
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [state.isAuthenticated])

  // 401 Unauthorized 전역 이벤트 구독 (API 호출 시 토큰 무효화 감지)
  useEffect(() => {
    const handleUnauthorized = () => {
      setState({ ...defaultState, isLoading: false })
    }

    window.addEventListener('auth:unauthorized', handleUnauthorized)

    return () => {
      window.removeEventListener('auth:unauthorized', handleUnauthorized)
    }
  }, [])

  // 토스 로그인
  const login = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true, error: null }))

    try {
      // SDK 브릿지 초기화 상태 확인 (최대 3초 대기)
      const checkBridge = () => {
        const hasConstantMap = typeof window !== 'undefined' &&
          window.__CONSTANT_HANDLER_MAP &&
          typeof window.__CONSTANT_HANDLER_MAP === 'object' &&
          Object.keys(window.__CONSTANT_HANDLER_MAP).length > 0
        const hasWebView = typeof window !== 'undefined' &&
          window.ReactNativeWebView &&
          typeof window.ReactNativeWebView.postMessage === 'function'
        return { hasConstantMap, hasWebView }
      }

      let bridgeCheck = checkBridge()

      // 브릿지가 초기화되지 않은 경우 최대 3초간 대기 (100ms 간격)
      if (!bridgeCheck.hasConstantMap || !bridgeCheck.hasWebView) {
        for (let i = 0; i < 30; i++) {
          await new Promise(resolve => setTimeout(resolve, 100))
          bridgeCheck = checkBridge()
          if (bridgeCheck.hasConstantMap && bridgeCheck.hasWebView) {
            break
          }
        }
      }

      // 대기 후에도 브릿지가 초기화되지 않은 경우 에러 반환
      if (!bridgeCheck.hasConstantMap || !bridgeCheck.hasWebView) {
        throw new Error('토스 앱 또는 샌드박스 앱에서 실행해주세요.')
      }

      // 환경 확인
      try {
        getOperationalEnvironment()
      } catch {
        // 환경 확인 실패해도 계속 진행
      }

      // 토스앱/샌드박스: appLogin으로 인가 코드 받기
      const { authorizationCode, referrer } = await tossAppLogin()

      // 서버에 인가 코드 전송하여 토큰 발급
      await authService.exchangeCodeForToken(authorizationCode, referrer)

      // 사용자 정보 조회
      const user = await authService.fetchUserInfo()

      // 이용권 조회
      let credits = 0
      try {
        const creditInfo = await authService.fetchCredits()
        credits = creditInfo.credits
      } catch {
        // 이용권 조회 실패해도 로그인은 성공
      }

      setState({
        isAuthenticated: true,
        isLoading: false,
        user,
        credits,
        error: null,
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : '로그인에 실패했습니다.'
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
      }))
      throw error
    }
  }, [])

  // 로그아웃
  const logout = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true }))

    try {
      await authService.logout()
    } finally {
      setState({
        ...defaultState,
        isLoading: false,
      })
    }
  }, [])

  // 이용권 새로고침
  const refreshCredits = useCallback(async () => {
    if (!state.isAuthenticated) return

    try {
      const creditInfo = await authService.fetchCredits()
      setState(prev => ({
        ...prev,
        credits: creditInfo.credits,
      }))
    } catch {
      // 조회 실패 시 무시
    }
  }, [state.isAuthenticated])

  // 이용권 차감 (로컬 상태만 업데이트, 서버는 리포트 조회 시 자동 차감)
  const deductCredit = useCallback(() => {
    setState(prev => ({
      ...prev,
      credits: Math.max(0, prev.credits - 1),
    }))
  }, [])

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        logout,
        refreshCredits,
        deductCredit,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

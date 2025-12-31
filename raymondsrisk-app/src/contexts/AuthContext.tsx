import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { appLogin as tossAppLogin, getOperationalEnvironment } from '@apps-in-toss/web-framework'
import type { AuthState, TossUser } from '../types/auth'
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

// 디버그 로그를 저장하는 전역 배열 (화면에 표시용)
export const debugLogs: string[] = []
function debugLog(message: string) {
  const timestamp = new Date().toLocaleTimeString()
  const log = `[${timestamp}] ${message}`
  debugLogs.push(log)
  console.log(log)
  // 최대 50개 로그 유지
  if (debugLogs.length > 50) debugLogs.shift()
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(defaultState)

  // 초기화: 저장된 인증 정보 복원
  useEffect(() => {
    const initAuth = async () => {
      try {
        const { user, accessToken } = authService.restoreAuth()

        if (user && accessToken) {
          // 이용권 조회
          try {
            const creditInfo = await authService.fetchCredits()
            setState({
              isAuthenticated: true,
              isLoading: false,
              user,
              credits: creditInfo.credits,
              error: null,
            })
          } catch {
            // 토큰 만료 등의 경우
            setState({
              isAuthenticated: true,
              isLoading: false,
              user,
              credits: 0,
              error: null,
            })
          }
        } else {
          setState({
            ...defaultState,
            isLoading: false,
          })
        }
      } catch {
        setState({
          ...defaultState,
          isLoading: false,
        })
      }
    }

    initAuth()
  }, [])

  // 토스 로그인
  const login = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true, error: null }))

    try {
      debugLog('login() 시작')
      debugLog(`import.meta.env.DEV = ${import.meta.env.DEV}`)
      debugLog(`import.meta.env.MODE = ${import.meta.env.MODE}`)
      debugLog(`import.meta.env.PROD = ${import.meta.env.PROD}`)

      // 개발 환경(granite dev)에서는 모의 로그인
      if (import.meta.env.DEV) {
        debugLog('DEV 환경 - 모의 로그인 실행')
        const mockUserKey = 'dev_user_' + Date.now()
        const mockUser: TossUser = {
          userKey: mockUserKey,
          name: '테스트 사용자',
        }
        const mockToken = `dev_token_${mockUserKey}`
        localStorage.setItem('raymondsrisk_access_token', mockToken)
        localStorage.setItem('raymondsrisk_refresh_token', mockToken)
        localStorage.setItem('raymondsrisk_user_key', mockUserKey)
        localStorage.setItem('raymondsrisk_user_info', JSON.stringify(mockUser))

        setState({
          isAuthenticated: true,
          isLoading: false,
          user: mockUser,
          credits: 10,
          error: null,
        })
        debugLog('DEV 모의 로그인 완료')
        return
      }

      // 프로덕션 빌드(.ait 파일): 환경 감지
      debugLog('PROD 환경 - SDK 브릿지 확인 시작')

      // window 객체 상태 덤프
      debugLog(`typeof window = ${typeof window}`)
      if (typeof window !== 'undefined') {
        debugLog(`window.__CONSTANT_HANDLER_MAP = ${JSON.stringify(window.__CONSTANT_HANDLER_MAP)}`)
        debugLog(`window.ReactNativeWebView 존재 = ${!!window.ReactNativeWebView}`)
        debugLog(`window.__GRANITE_NATIVE_EMITTER 존재 = ${!!window.__GRANITE_NATIVE_EMITTER}`)
      }

      // SDK 브릿지 초기화 상태 확인
      const hasConstantMap = typeof window !== 'undefined' &&
        window.__CONSTANT_HANDLER_MAP &&
        typeof window.__CONSTANT_HANDLER_MAP === 'object' &&
        Object.keys(window.__CONSTANT_HANDLER_MAP).length > 0
      const hasWebView = typeof window !== 'undefined' &&
        window.ReactNativeWebView &&
        typeof window.ReactNativeWebView.postMessage === 'function'

      debugLog(`hasConstantMap = ${hasConstantMap}`)
      debugLog(`hasWebView = ${hasWebView}`)

      // 브릿지가 초기화되지 않은 경우 샌드박스 모의 로그인 사용
      if (!hasConstantMap || !hasWebView) {
        debugLog('브릿지 미초기화 - 샌드박스 모의 로그인')
        const sandboxUserKey = `sandbox_user_${Date.now()}`
        const sandboxUser: TossUser = {
          userKey: sandboxUserKey,
          name: '샌드박스 테스트 사용자',
        }
        const sandboxToken = `sandbox_token_${sandboxUserKey}`
        localStorage.setItem('raymondsrisk_access_token', sandboxToken)
        localStorage.setItem('raymondsrisk_refresh_token', sandboxToken)
        localStorage.setItem('raymondsrisk_user_key', sandboxUserKey)
        localStorage.setItem('raymondsrisk_user_info', JSON.stringify(sandboxUser))

        setState({
          isAuthenticated: true,
          isLoading: false,
          user: sandboxUser,
          credits: 10,
          error: null,
        })
        debugLog('브릿지 미초기화 모의 로그인 완료')
        return
      }

      // SDK 브릿지 초기화됨 - 환경 확인
      debugLog('브릿지 초기화됨 - getOperationalEnvironment 호출')
      let environment: 'toss' | 'sandbox' = 'sandbox'
      try {
        environment = getOperationalEnvironment()
        debugLog(`getOperationalEnvironment() = ${environment}`)
      } catch (e) {
        debugLog(`getOperationalEnvironment() 에러: ${e}`)
        environment = 'sandbox'
      }

      // 실제 토스 로그인 연동
      debugLog(`환경: ${environment} - appLogin 호출`)

      // 토스앱/샌드박스: appLogin으로 인가 코드 받기
      const { authorizationCode, referrer } = await tossAppLogin()
      debugLog(`appLogin 성공: referrer=${referrer}, authCode=${authorizationCode.substring(0, 10)}...`)

      // 서버에 인가 코드 전송하여 토큰 발급
      debugLog('서버에 토큰 요청 중...')
      await authService.exchangeCodeForToken(authorizationCode, referrer)
      debugLog('토큰 발급 완료')

      // 사용자 정보 조회
      debugLog('사용자 정보 조회 중...')
      const user = await authService.fetchUserInfo()
      debugLog(`사용자 정보: ${user.userKey}`)

      // 이용권 조회
      let credits = 0
      try {
        debugLog('이용권 조회 중...')
        const creditInfo = await authService.fetchCredits()
        credits = creditInfo.credits
        debugLog(`이용권: ${credits}건`)
      } catch (e) {
        debugLog(`이용권 조회 실패: ${e}`)
        // 이용권 조회 실패해도 로그인은 성공
      }

      setState({
        isAuthenticated: true,
        isLoading: false,
        user,
        credits,
        error: null,
      })
      debugLog('로그인 완료')
    } catch (error) {
      const message = error instanceof Error ? error.message : '로그인에 실패했습니다.'
      debugLog(`login() 에러: ${message}`)
      debugLog(`에러 상세: ${JSON.stringify(error)}`)
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

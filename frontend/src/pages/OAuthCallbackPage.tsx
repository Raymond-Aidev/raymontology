import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

function OAuthCallbackPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { setToken, checkAuth } = useAuthStore()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = searchParams.get('token')
    const errorParam = searchParams.get('error')

    if (errorParam) {
      // OAuth 에러 처리
      const errorMessages: Record<string, string> = {
        google_auth_failed: 'Google 로그인이 취소되었습니다',
        kakao_auth_failed: 'Kakao 로그인이 취소되었습니다',
        token_exchange_failed: '인증 토큰 교환에 실패했습니다',
        user_info_failed: '사용자 정보를 가져오는데 실패했습니다',
        no_email: '이메일 정보가 제공되지 않았습니다',
        no_code: '인증 코드가 없습니다',
        oauth_error: 'OAuth 인증 중 오류가 발생했습니다'
      }
      setError(errorMessages[errorParam] || '로그인 중 오류가 발생했습니다')
      setTimeout(() => navigate('/login'), 3000)
      return
    }

    if (token) {
      // 토큰 저장 및 사용자 정보 확인
      setToken(token)
      checkAuth().then((success) => {
        if (success) {
          navigate('/', { replace: true })
        } else {
          setError('사용자 인증에 실패했습니다')
          setTimeout(() => navigate('/login'), 3000)
        }
      })
    } else {
      setError('인증 토큰이 없습니다')
      setTimeout(() => navigate('/login'), 3000)
    }
  }, [searchParams, setToken, checkAuth, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        {error ? (
          <>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">로그인 실패</h2>
            <p className="text-gray-600 mb-4">{error}</p>
            <p className="text-sm text-gray-500">잠시 후 로그인 페이지로 이동합니다...</p>
          </>
        ) : (
          <>
            <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-600">로그인 처리 중...</p>
          </>
        )}
      </div>
    </div>
  )
}

export default OAuthCallbackPage

import { useState, useEffect } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import apiClient from '../api/client'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'

function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')

  const [isLoading, setIsLoading] = useState(true)
  const [isSuccess, setIsSuccess] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      setIsLoading(false)
      setError('유효하지 않은 인증 링크입니다.')
      return
    }

    const verifyEmail = async () => {
      try {
        await apiClient.get(`/api/auth/verify-email?token=${token}`)
        setIsSuccess(true)
      } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } } }
        setError(error.response?.data?.detail || '이메일 인증 중 오류가 발생했습니다.')
      } finally {
        setIsLoading(false)
      }
    }

    verifyEmail()
  }, [token])

  // 로딩 중
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-theme-bg p-4">
        <div className="w-full max-w-md">
          <div className="bg-theme-card border border-theme-border rounded-2xl shadow-xl p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-6 flex items-center justify-center">
              <div className="w-12 h-12 border-4 border-accent-primary border-t-transparent rounded-full animate-spin" />
            </div>
            <h2 className="text-2xl font-bold text-text-primary mb-3">이메일 인증 중...</h2>
            <p className="text-text-secondary">
              잠시만 기다려주세요.
            </p>
          </div>
        </div>
      </div>
    )
  }

  // 성공 화면
  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-theme-bg p-4">
        <div className="w-full max-w-md">
          <div className="flex justify-center mb-8">
            <Link to="/" className="inline-block">
              <RaymondsRiskLogo size="md" variant="compact" />
            </Link>
          </div>

          <div className="bg-theme-card border border-theme-border rounded-2xl shadow-xl p-8 text-center">
            <div className="w-20 h-20 bg-accent-success/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-text-primary mb-3">가입 완료!</h2>
            <p className="text-text-secondary mb-8">
              이메일 인증이 완료되었습니다.<br />
              이제 로그인하여 서비스를 이용하실 수 있습니다.
            </p>
            <button
              onClick={() => navigate('/login')}
              className="w-full py-3.5 px-4 bg-accent-primary text-white rounded-lg font-semibold hover:bg-accent-primary/90 transition-colors shadow-lg shadow-accent-primary/25"
            >
              로그인하러 가기
            </button>
          </div>
        </div>
      </div>
    )
  }

  // 에러 화면
  return (
    <div className="min-h-screen flex items-center justify-center bg-theme-bg p-4">
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <Link to="/" className="inline-block">
            <RaymondsRiskLogo size="md" variant="compact" />
          </Link>
        </div>

        <div className="bg-theme-card border border-theme-border rounded-2xl shadow-xl p-8 text-center">
          <div className="w-20 h-20 bg-accent-danger/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-accent-danger" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-text-primary mb-3">인증 실패</h2>
          <p className="text-text-secondary mb-8">
            {error}
          </p>
          <div className="space-y-3">
            <Link
              to="/login"
              className="block w-full py-3.5 px-4 bg-accent-primary text-white rounded-lg font-semibold hover:bg-accent-primary/90 transition-colors text-center"
            >
              로그인 페이지로 이동
            </Link>
            <p className="text-sm text-text-muted">
              문제가 계속되면 다시 회원가입을 시도해주세요.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default VerifyEmailPage

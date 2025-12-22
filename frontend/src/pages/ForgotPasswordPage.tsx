import { useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../api/client'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'

function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      await apiClient.post('/api/auth/forgot-password', { email })
      setIsSubmitted(true)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || '요청 처리 중 오류가 발생했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  if (isSubmitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-theme-bg p-4">
        <div className="w-full max-w-md">
          <div className="bg-theme-card border border-theme-border rounded-2xl shadow-xl p-8 text-center">
            <div className="w-16 h-16 bg-accent-success/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-8 h-8 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-text-primary mb-3">이메일을 확인해주세요</h2>
            <p className="text-text-secondary mb-6">
              {email}로 비밀번호 재설정 링크를 발송했습니다.
              이메일이 도착하지 않았다면 스팸 폴더를 확인해주세요.
            </p>
            <Link
              to="/login"
              className="inline-block w-full py-3 px-4 bg-accent-primary text-white rounded-lg font-medium hover:bg-accent-primary/90 transition-colors"
            >
              로그인 페이지로 돌아가기
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-theme-bg p-4">
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <Link to="/" className="inline-block">
            <RaymondsRiskLogo size="md" variant="compact" />
          </Link>
        </div>

        <div className="bg-theme-card border border-theme-border rounded-2xl shadow-xl p-8">
          <h2 className="text-2xl font-bold text-text-primary mb-2">비밀번호 찾기</h2>
          <p className="text-text-secondary mb-6">
            가입한 이메일 주소를 입력하시면 비밀번호 재설정 링크를 보내드립니다.
          </p>

          {error && (
            <div className="mb-6 p-4 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
              <p className="text-sm text-accent-danger">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-text-secondary mb-2">
                이메일
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                  </svg>
                </div>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="example@email.com"
                  className="w-full pl-10 pr-4 py-3 bg-theme-surface border border-theme-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/50 focus:border-accent-primary transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading || !email}
              className={`w-full py-3 px-4 rounded-lg font-medium text-white transition-all
                         ${isLoading || !email ? 'bg-accent-primary/50 cursor-not-allowed' : 'bg-accent-primary hover:bg-accent-primary/90'}`}
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  전송 중...
                </span>
              ) : (
                '재설정 링크 보내기'
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <Link to="/login" className="text-sm text-accent-primary hover:text-accent-primary/80 font-medium">
              로그인 페이지로 돌아가기
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ForgotPasswordPage

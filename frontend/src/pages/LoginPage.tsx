import { useState, useCallback, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'

function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, isLoading: authLoading, login, clearError } = useAuthStore()


  // 로그인 전에 접근하려던 페이지
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/'

  // 이미 로그인된 경우 원래 페이지로 리다이렉트
  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, authLoading, navigate, from])

  // 로그인 폼 상태
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [showLoginPassword, setShowLoginPassword] = useState(false)
  const [loginLoading, setLoginLoading] = useState(false)
  const [loginError, setLoginError] = useState('')

  // 로그인 처리
  const handleLogin = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!loginEmail || !loginPassword) return

    setLoginError('')
    setLoginLoading(true)
    clearError()

    try {
      const success = await login({ email: loginEmail, password: loginPassword })
      if (success) {
        navigate(from, { replace: true })
      } else {
        const storeError = useAuthStore.getState().error
        setLoginError(storeError || '이메일 또는 비밀번호가 올바르지 않습니다.')
      }
    } catch {
      setLoginError('로그인 중 오류가 발생했습니다.')
    } finally {
      setLoginLoading(false)
    }
  }, [loginEmail, loginPassword, login, clearError, navigate, from])

  return (
    <div className="min-h-screen bg-theme-bg flex items-center justify-center py-8 px-4 sm:px-6">
      <div className="w-full max-w-md">
        {/* 로고 */}
        <div className="flex justify-center mb-8">
          <Link to="/" className="inline-block">
            <RaymondsRiskLogo size="md" variant="compact" />
          </Link>
        </div>

        {/* 로그인 카드 */}
        <div className="bg-theme-card border border-theme-border rounded-2xl p-8 shadow-xl">
            <h2 className="text-2xl font-bold text-text-primary mb-6 text-center">
              로그인
            </h2>

            {loginError && (
              <div className="mb-4 p-3 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
                <p className="text-sm text-accent-danger">{loginError}</p>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label htmlFor="login-email" className="block text-sm font-medium text-text-secondary mb-2">
                  이메일
                </label>
                <input
                  id="login-email"
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder="example@email.com"
                  autoComplete="email"
                  className="w-full px-4 py-3 bg-theme-surface border border-theme-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/30 focus:border-accent-primary transition-colors"
                />
              </div>

              <div>
                <label htmlFor="login-password" className="block text-sm font-medium text-text-secondary mb-2">
                  비밀번호
                </label>
                <div className="relative">
                  <input
                    id="login-password"
                    type={showLoginPassword ? 'text' : 'password'}
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="비밀번호 입력"
                    autoComplete="current-password"
                    className="w-full px-4 py-3 pr-12 bg-theme-surface border border-theme-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/30 focus:border-accent-primary transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowLoginPassword(!showLoginPassword)}
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-text-muted hover:text-text-secondary"
                  >
                    {showLoginPassword ? (
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      </svg>
                    ) : (
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
                <div className="text-right mt-2">
                  <Link
                    to="/forgot-password"
                    className="text-sm text-accent-primary hover:text-accent-primary/80 hover:underline"
                  >
                    비밀번호를 잊으셨나요?
                  </Link>
                </div>
              </div>

              <button
                type="submit"
                disabled={loginLoading || !loginEmail || !loginPassword}
                className={`w-full py-3.5 px-4 rounded-lg font-semibold text-white transition-all ${
                  loginLoading || !loginEmail || !loginPassword
                    ? 'bg-accent-primary/50 cursor-not-allowed'
                    : 'bg-accent-primary hover:bg-accent-primary/90 shadow-lg shadow-accent-primary/25'
                }`}
              >
                {loginLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    로그인 중...
                  </span>
                ) : (
                  '로그인'
                )}
              </button>
            </form>

          {/* 문의 안내 (회원가입 비활성화됨) */}
          <div className="mt-6 pt-6 border-t border-theme-border text-center">
            <p className="text-sm text-text-secondary">
              계정이 필요하시면{' '}
              <Link to="/contact" className="text-accent-primary hover:underline">
                문의하기
              </Link>
              를 이용해주세요.
            </p>
          </div>
        </div>

        {/* 하단 링크 */}
        <div className="mt-6 text-center">
          <p className="text-sm text-text-muted">
            <Link to="/about" className="hover:text-text-secondary hover:underline">
              서비스 소개
            </Link>
            {' · '}
            <Link to="/contact" className="hover:text-text-secondary hover:underline">
              문의하기
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default LoginPage

import { useState, useCallback, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'

function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, isLoading: authLoading, login, register, clearError } = useAuthStore()

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

  // 회원가입 폼 상태
  const [registerEmail, setRegisterEmail] = useState('')
  const [registerPassword, setRegisterPassword] = useState('')
  const [registerConfirmPassword, setRegisterConfirmPassword] = useState('')
  const [registerUsername, setRegisterUsername] = useState('')
  const [showRegisterPassword, setShowRegisterPassword] = useState(false)
  const [agreeTerms, setAgreeTerms] = useState(false)
  const [registerLoading, setRegisterLoading] = useState(false)
  const [registerError, setRegisterError] = useState('')
  const [showSuccessModal, setShowSuccessModal] = useState(false)

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
        // store에서 error 가져오기
        const storeError = useAuthStore.getState().error
        setLoginError(storeError || '이메일 또는 비밀번호가 올바르지 않습니다.')
      }
    } catch {
      setLoginError('로그인 중 오류가 발생했습니다.')
    } finally {
      setLoginLoading(false)
    }
  }, [loginEmail, loginPassword, login, clearError, navigate, from])

  // 비밀번호 유효성 검사
  const validatePassword = (pwd: string) => {
    if (!pwd) return ''
    if (pwd.length < 8) return '8자 이상'
    if (!/[A-Z]/.test(pwd)) return '대문자 포함'
    if (!/[a-z]/.test(pwd)) return '소문자 포함'
    if (!/[0-9]/.test(pwd)) return '숫자 포함'
    if (!/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(pwd)) return '특수문자 포함'
    return ''
  }

  const passwordValidation = validatePassword(registerPassword)
  const isRegisterValid = registerEmail && registerPassword && registerConfirmPassword &&
                          registerUsername && registerPassword === registerConfirmPassword &&
                          !passwordValidation && agreeTerms

  // 회원가입 처리
  const handleRegister = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isRegisterValid) return

    setRegisterError('')
    setRegisterLoading(true)
    clearError()

    try {
      const success = await register({
        email: registerEmail,
        password: registerPassword,
        username: registerUsername,
        full_name: registerUsername
      })
      if (success) {
        setShowSuccessModal(true)
        // 폼 초기화
        setRegisterEmail('')
        setRegisterPassword('')
        setRegisterConfirmPassword('')
        setRegisterUsername('')
        setAgreeTerms(false)
      } else {
        // store에서 error 가져오기
        const storeError = useAuthStore.getState().error
        setRegisterError(storeError || '회원가입 중 오류가 발생했습니다.')
      }
    } catch {
      setRegisterError('회원가입 중 오류가 발생했습니다.')
    } finally {
      setRegisterLoading(false)
    }
  }, [isRegisterValid, register, registerEmail, registerPassword, registerUsername, clearError])

  return (
    <div className="min-h-screen bg-theme-bg py-8 px-4 sm:px-6">
      <div className="max-w-[900px] mx-auto">
        {/* 로고 */}
        <div className="flex justify-center mb-8">
          <Link to="/" className="inline-block">
            <RaymondsRiskLogo size="md" variant="compact" />
          </Link>
        </div>

        {/* 소셜 로그인 */}
        <div className="max-w-[400px] mx-auto mb-8">
          <div className="space-y-3">
            <a
              href={`${import.meta.env.VITE_API_URL || ''}/api/auth/google`}
              className="w-full flex items-center justify-center gap-3 py-3.5 px-4 bg-[#5E6AD2] hover:bg-[#4F5ABF] text-white rounded-lg font-medium transition-colors"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              Google로 계속하기
            </a>

            <a
              href={`${import.meta.env.VITE_API_URL || ''}/api/auth/kakao`}
              className="w-full flex items-center justify-center gap-3 py-3.5 px-4 bg-[#FEE500] hover:bg-[#FDD800] rounded-lg font-medium transition-colors"
              style={{ color: '#3C1E1E' }}
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M12 4C7.029 4 3 7.164 3 11.073c0 2.507 1.674 4.712 4.2 5.985l-.856 3.212c-.077.29.248.517.502.35l3.845-2.567c.428.037.864.057 1.309.057 4.971 0 9-3.164 9-7.073S16.971 4 12 4z"
                />
              </svg>
              카카오로 계속하기
            </a>
          </div>

          {/* 구분선 */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-theme-border" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-3 bg-theme-bg text-text-muted">또는 이메일로 계속하기</span>
            </div>
          </div>
        </div>

        {/* 로그인 + 회원가입 카드 */}
        <div className="grid md:grid-cols-2 gap-6 max-w-[900px] mx-auto">
          {/* 로그인 카드 */}
          <div className="bg-theme-card border border-theme-border rounded-2xl p-6 shadow-lg">
            <h2 className="text-xl font-semibold text-text-primary mb-6 flex items-center gap-2">
              <svg className="w-5 h-5 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
              </svg>
              로그인
            </h2>

            {loginError && (
              <div className="mb-4 p-3 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
                <p className="text-sm text-accent-danger">{loginError}</p>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label htmlFor="login-email" className="block text-sm font-medium text-text-secondary mb-1.5">
                  이메일
                </label>
                <input
                  id="login-email"
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder="example@email.com"
                  autoComplete="email"
                  className="w-full px-4 py-2.5 bg-theme-surface border border-theme-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/30 focus:border-accent-primary transition-colors"
                />
              </div>

              <div>
                <label htmlFor="login-password" className="block text-sm font-medium text-text-secondary mb-1.5">
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
                    className="w-full px-4 py-2.5 pr-10 bg-theme-surface border border-theme-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/30 focus:border-accent-primary transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowLoginPassword(!showLoginPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-text-muted hover:text-text-secondary"
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
                <div className="text-right mt-1.5">
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
                className={`w-full py-3 px-4 rounded-lg font-medium text-white transition-all ${
                  loginLoading || !loginEmail || !loginPassword
                    ? 'bg-accent-primary/50 cursor-not-allowed'
                    : 'bg-accent-primary hover:bg-accent-primary/90'
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
          </div>

          {/* 회원가입 카드 */}
          <div className="bg-theme-card border border-theme-border rounded-2xl p-6 shadow-lg">
            <h2 className="text-xl font-semibold text-text-primary mb-6 flex items-center gap-2">
              <svg className="w-5 h-5 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
              </svg>
              회원가입
            </h2>

            {registerError && (
              <div className="mb-4 p-3 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
                <p className="text-sm text-accent-danger">{registerError}</p>
              </div>
            )}

            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label htmlFor="register-username" className="block text-sm font-medium text-text-secondary mb-1.5">
                  이름
                </label>
                <input
                  id="register-username"
                  type="text"
                  value={registerUsername}
                  onChange={(e) => setRegisterUsername(e.target.value)}
                  placeholder="홍길동"
                  autoComplete="name"
                  className="w-full px-4 py-2.5 bg-theme-surface border border-theme-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/30 focus:border-accent-primary transition-colors"
                />
              </div>

              <div>
                <label htmlFor="register-email" className="block text-sm font-medium text-text-secondary mb-1.5">
                  이메일
                </label>
                <input
                  id="register-email"
                  type="email"
                  value={registerEmail}
                  onChange={(e) => setRegisterEmail(e.target.value)}
                  placeholder="example@email.com"
                  autoComplete="email"
                  className="w-full px-4 py-2.5 bg-theme-surface border border-theme-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/30 focus:border-accent-primary transition-colors"
                />
              </div>

              <div>
                <label htmlFor="register-password" className="block text-sm font-medium text-text-secondary mb-1.5">
                  비밀번호
                </label>
                <div className="relative">
                  <input
                    id="register-password"
                    type={showRegisterPassword ? 'text' : 'password'}
                    value={registerPassword}
                    onChange={(e) => setRegisterPassword(e.target.value)}
                    placeholder="8자 이상, 대/소문자, 숫자, 특수문자"
                    autoComplete="new-password"
                    className={`w-full px-4 py-2.5 pr-10 bg-theme-surface border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 transition-colors ${
                      registerPassword && passwordValidation
                        ? 'border-accent-warning/50 focus:ring-accent-warning/30'
                        : 'border-theme-border focus:ring-accent-primary/30 focus:border-accent-primary'
                    }`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowRegisterPassword(!showRegisterPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-text-muted hover:text-text-secondary"
                  >
                    {showRegisterPassword ? (
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
                {registerPassword && passwordValidation && (
                  <p className="mt-1 text-xs text-accent-warning">{passwordValidation} 필요</p>
                )}
              </div>

              <div>
                <label htmlFor="register-confirm-password" className="block text-sm font-medium text-text-secondary mb-1.5">
                  비밀번호 확인
                </label>
                <input
                  id="register-confirm-password"
                  type={showRegisterPassword ? 'text' : 'password'}
                  value={registerConfirmPassword}
                  onChange={(e) => setRegisterConfirmPassword(e.target.value)}
                  placeholder="비밀번호 재입력"
                  autoComplete="new-password"
                  className={`w-full px-4 py-2.5 bg-theme-surface border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 transition-colors ${
                    registerConfirmPassword && registerPassword !== registerConfirmPassword
                      ? 'border-accent-danger/50 focus:ring-accent-danger/30'
                      : 'border-theme-border focus:ring-accent-primary/30 focus:border-accent-primary'
                  }`}
                />
                {registerConfirmPassword && registerPassword !== registerConfirmPassword && (
                  <p className="mt-1 text-xs text-accent-danger">비밀번호가 일치하지 않습니다</p>
                )}
              </div>

              {/* 이용약관 동의 */}
              <div className="flex items-start gap-2">
                <input
                  id="agree-terms"
                  type="checkbox"
                  checked={agreeTerms}
                  onChange={(e) => setAgreeTerms(e.target.checked)}
                  className="mt-1 w-4 h-4 rounded border-theme-border text-accent-primary focus:ring-accent-primary/30"
                />
                <label htmlFor="agree-terms" className="text-sm text-text-secondary">
                  <Link to="/terms" className="text-accent-primary hover:underline">이용약관</Link>
                  {' '}및{' '}
                  <Link to="/privacy" className="text-accent-primary hover:underline">개인정보 처리방침</Link>
                  에 동의합니다
                </label>
              </div>

              <button
                type="submit"
                disabled={registerLoading || !isRegisterValid}
                className={`w-full py-3 px-4 rounded-lg font-medium text-white transition-all ${
                  registerLoading || !isRegisterValid
                    ? 'bg-accent-success/50 cursor-not-allowed'
                    : 'bg-accent-success hover:bg-accent-success/90'
                }`}
              >
                {registerLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    가입 중...
                  </span>
                ) : (
                  '회원가입'
                )}
              </button>
            </form>
          </div>
        </div>

        {/* 하단 링크 */}
        <div className="mt-8 text-center space-y-3">
          <p className="text-sm text-text-secondary">
            <Link to="/about" className="text-text-primary font-medium hover:underline">
              서비스 소개
            </Link>
            {' '}|{' '}
            <Link to="/contact" className="text-text-primary font-medium hover:underline">
              문의하기
            </Link>
          </p>
        </div>
      </div>

      {/* 회원가입 성공 모달 */}
      {showSuccessModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-theme-card border border-theme-border rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl animate-scale-in">
            <div className="w-16 h-16 mx-auto mb-4 bg-accent-success/10 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-text-primary text-center mb-2">회원가입 완료</h3>
            <p className="text-sm text-text-secondary text-center mb-6">
              회원가입이 완료되었습니다.<br />
              왼쪽 로그인 폼에서 로그인해주세요.
            </p>
            <button
              onClick={() => setShowSuccessModal(false)}
              className="w-full py-3 px-4 bg-accent-primary hover:bg-accent-primary/90 text-white font-medium rounded-xl text-center transition-colors"
            >
              확인
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default LoginPage

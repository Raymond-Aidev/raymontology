import { useState, useCallback, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'

type ViewMode = 'login' | 'register'

function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, isLoading: authLoading, login, register, clearError } = useAuthStore()

  // 현재 보기 모드
  const [viewMode, setViewMode] = useState<ViewMode>('login')

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
        setRegisterEmail('')
        setRegisterPassword('')
        setRegisterConfirmPassword('')
        setRegisterUsername('')
        setAgreeTerms(false)
      } else {
        const storeError = useAuthStore.getState().error
        setRegisterError(storeError || '회원가입 중 오류가 발생했습니다.')
      }
    } catch {
      setRegisterError('회원가입 중 오류가 발생했습니다.')
    } finally {
      setRegisterLoading(false)
    }
  }, [isRegisterValid, register, registerEmail, registerPassword, registerUsername, clearError])

  // 뷰 전환 시 에러 초기화
  const switchView = (mode: ViewMode) => {
    setViewMode(mode)
    setLoginError('')
    setRegisterError('')
  }

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
        {viewMode === 'login' && (
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

            {/* 회원가입 링크 */}
            <div className="mt-6 pt-6 border-t border-theme-border text-center">
              <p className="text-sm text-text-secondary mb-3">
                아직 계정이 없으신가요?
              </p>
              <button
                onClick={() => switchView('register')}
                className="text-accent-primary font-semibold hover:underline"
              >
                회원가입
              </button>
            </div>
          </div>
        )}

        {/* 회원가입 카드 */}
        {viewMode === 'register' && (
          <div className="bg-theme-card border border-theme-border rounded-2xl p-8 shadow-xl">
            <h2 className="text-2xl font-bold text-text-primary mb-6 text-center">
              회원가입
            </h2>

            {registerError && (
              <div className="mb-4 p-3 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
                <p className="text-sm text-accent-danger">{registerError}</p>
              </div>
            )}

            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label htmlFor="register-username" className="block text-sm font-medium text-text-secondary mb-2">
                  닉네임
                </label>
                <input
                  id="register-username"
                  type="text"
                  value={registerUsername}
                  onChange={(e) => setRegisterUsername(e.target.value)}
                  placeholder="사용할 닉네임"
                  autoComplete="username"
                  className="w-full px-4 py-3 bg-theme-surface border border-theme-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/30 focus:border-accent-primary transition-colors"
                />
              </div>

              <div>
                <label htmlFor="register-email" className="block text-sm font-medium text-text-secondary mb-2">
                  이메일
                </label>
                <input
                  id="register-email"
                  type="email"
                  value={registerEmail}
                  onChange={(e) => setRegisterEmail(e.target.value)}
                  placeholder="example@email.com"
                  autoComplete="email"
                  className="w-full px-4 py-3 bg-theme-surface border border-theme-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/30 focus:border-accent-primary transition-colors"
                />
              </div>

              <div>
                <label htmlFor="register-password" className="block text-sm font-medium text-text-secondary mb-2">
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
                    className={`w-full px-4 py-3 pr-12 bg-theme-surface border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 transition-colors ${
                      registerPassword && passwordValidation
                        ? 'border-accent-warning/50 focus:ring-accent-warning/30'
                        : 'border-theme-border focus:ring-accent-primary/30 focus:border-accent-primary'
                    }`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowRegisterPassword(!showRegisterPassword)}
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-text-muted hover:text-text-secondary"
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
                  <p className="mt-1.5 text-xs text-accent-warning">{passwordValidation} 필요</p>
                )}
              </div>

              <div>
                <label htmlFor="register-confirm-password" className="block text-sm font-medium text-text-secondary mb-2">
                  비밀번호 확인
                </label>
                <input
                  id="register-confirm-password"
                  type={showRegisterPassword ? 'text' : 'password'}
                  value={registerConfirmPassword}
                  onChange={(e) => setRegisterConfirmPassword(e.target.value)}
                  placeholder="비밀번호 재입력"
                  autoComplete="new-password"
                  className={`w-full px-4 py-3 bg-theme-surface border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 transition-colors ${
                    registerConfirmPassword && registerPassword !== registerConfirmPassword
                      ? 'border-accent-danger/50 focus:ring-accent-danger/30'
                      : 'border-theme-border focus:ring-accent-primary/30 focus:border-accent-primary'
                  }`}
                />
                {registerConfirmPassword && registerPassword !== registerConfirmPassword && (
                  <p className="mt-1.5 text-xs text-accent-danger">비밀번호가 일치하지 않습니다</p>
                )}
              </div>

              {/* 이용약관 동의 */}
              <div className="flex items-start gap-3 pt-2">
                <input
                  id="agree-terms"
                  type="checkbox"
                  checked={agreeTerms}
                  onChange={(e) => setAgreeTerms(e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded border-theme-border text-accent-primary focus:ring-accent-primary/30"
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
                className={`w-full py-3.5 px-4 rounded-lg font-semibold text-white transition-all mt-2 ${
                  registerLoading || !isRegisterValid
                    ? 'bg-accent-primary/50 cursor-not-allowed'
                    : 'bg-accent-primary hover:bg-accent-primary/90 shadow-lg shadow-accent-primary/25'
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

            {/* 로그인 링크 */}
            <div className="mt-6 pt-6 border-t border-theme-border text-center">
              <p className="text-sm text-text-secondary mb-3">
                이미 계정이 있으신가요?
              </p>
              <button
                onClick={() => switchView('login')}
                className="text-accent-primary font-semibold hover:underline"
              >
                로그인
              </button>
            </div>
          </div>
        )}

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

      {/* 회원가입 성공 모달 */}
      {showSuccessModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-theme-card border border-theme-border rounded-2xl p-8 max-w-sm w-full mx-4 shadow-2xl animate-scale-in">
            <div className="w-16 h-16 mx-auto mb-4 bg-accent-primary/10 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-text-primary text-center mb-2">인증 메일 발송 완료</h3>
            <p className="text-sm text-text-secondary text-center mb-6">
              입력하신 이메일로 인증 메일을 발송했습니다.<br />
              메일함을 확인하고 <strong className="text-text-primary">가입 확인</strong> 버튼을 클릭해주세요.
            </p>
            <p className="text-xs text-text-muted text-center mb-6">
              메일이 도착하지 않았다면 스팸함을 확인해주세요.
            </p>
            <button
              onClick={() => {
                setShowSuccessModal(false)
                switchView('login')
              }}
              className="w-full py-3.5 px-4 bg-accent-primary hover:bg-accent-primary/90 text-white font-semibold rounded-xl text-center transition-colors shadow-lg shadow-accent-primary/25"
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

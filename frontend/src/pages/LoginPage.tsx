import { useState, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { LoginForm, RegisterForm } from '../components/auth'
import { useAuthStore } from '../store/authStore'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'

type AuthMode = 'login' | 'register'

function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, isLoading } = useAuthStore()
  const [mode, setMode] = useState<AuthMode>('login')

  // 로그인 전에 접근하려던 페이지
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/'

  // 이미 로그인된 경우 원래 페이지로 리다이렉트
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate, from])

  const handleSuccess = () => {
    navigate(from, { replace: true })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-theme-bg p-4 sm:p-6">
      {/* 중앙 컨테이너 */}
      <div className="w-full max-w-[400px]">
        {/* 로고 */}
        <div className="flex justify-center mb-8">
          <Link to="/" className="inline-block">
            <RaymondsRiskLogo size="lg" variant="icon" />
          </Link>
        </div>

        {/* 제목 */}
        <h1 className="text-xl sm:text-2xl font-semibold text-text-primary text-center mb-8">
          {mode === 'login' ? 'RaymondsRisk 로그인' : '워크스페이스 생성'}
        </h1>

        {/* 소셜 로그인 버튼 */}
        <div className="space-y-3 mb-6">
          {/* Google 로그인 */}
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

          {/* 이메일 로그인/회원가입 토글 */}
          <button
            onClick={() => {
              const emailSection = document.getElementById('email-section')
              if (emailSection) {
                emailSection.classList.toggle('hidden')
              }
            }}
            className="w-full flex items-center justify-center gap-3 py-3.5 px-4 bg-theme-surface hover:bg-theme-hover border border-theme-border text-text-primary rounded-lg font-medium transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            이메일로 계속하기
          </button>

          {/* Kakao 로그인 */}
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

        {/* 이메일 폼 섹션 (기본 숨김) */}
        <div id="email-section" className="hidden">
          {/* 구분선 */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-theme-border" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-3 bg-theme-bg text-text-muted">또는</span>
            </div>
          </div>

          {/* 탭 전환 */}
          <div className="flex mb-6 bg-theme-surface rounded-lg p-1">
            <button
              onClick={() => setMode('login')}
              className={`flex-1 py-2.5 text-sm font-medium rounded-md transition-all ${
                mode === 'login'
                  ? 'bg-theme-card text-text-primary shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              로그인
            </button>
            <button
              onClick={() => setMode('register')}
              className={`flex-1 py-2.5 text-sm font-medium rounded-md transition-all ${
                mode === 'register'
                  ? 'bg-theme-card text-text-primary shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              회원가입
            </button>
          </div>

          {/* 폼 */}
          {mode === 'login' ? (
            <LoginForm
              onSuccess={handleSuccess}
              onSwitchToRegister={() => setMode('register')}
              minimal={true}
            />
          ) : (
            <RegisterForm
              onSuccess={handleSuccess}
              onSwitchToLogin={() => setMode('login')}
            />
          )}
        </div>

        {/* 회원가입 버튼 (로그인 모드일 때만) */}
        {mode === 'login' && (
          <div className="mt-6">
            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-theme-border" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-3 bg-theme-bg text-text-muted">계정이 없으신가요?</span>
              </div>
            </div>
            <button
              onClick={() => {
                setMode('register')
                const emailSection = document.getElementById('email-section')
                if (emailSection) {
                  emailSection.classList.remove('hidden')
                }
              }}
              className="w-full flex items-center justify-center gap-2 py-3.5 px-4 bg-theme-surface hover:bg-theme-hover border-2 border-accent-primary text-accent-primary rounded-lg font-medium transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
              </svg>
              회원가입
            </button>
          </div>
        )}

        {/* 하단 링크 */}
        <div className="mt-6 text-center space-y-3">
          {/* 약관 */}
          <p className="text-xs text-text-muted">
            가입 시{' '}
            <Link to="/terms" className="text-text-secondary hover:text-text-primary hover:underline">
              이용약관
            </Link>
            {' '}및{' '}
            <Link to="/privacy" className="text-text-secondary hover:text-text-primary hover:underline">
              개인정보 처리방침
            </Link>
            에 동의하게 됩니다.
          </p>

          {/* 서비스 소개 링크 */}
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
    </div>
  )
}

export default LoginPage

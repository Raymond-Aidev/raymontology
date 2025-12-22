import { useState, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { LoginForm, RegisterForm } from '../components/auth'
import { useAuthStore } from '../store/authStore'

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
    <div className="min-h-screen flex">
      {/* 왼쪽: 브랜드 영역 */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-blue-600 via-blue-700 to-purple-700 p-12 flex-col justify-between">
        <div>
          <Link to="/">
            <img
              src="/logo.png?v=2"
              alt="Raymond Partners"
              className="h-16 w-auto object-contain"
            />
          </Link>
        </div>

        <div className="text-white">
          <h1 className="text-4xl font-bold mb-6 leading-tight">
            한국 주식시장의<br />
            숨겨진 리스크를<br />
            탐지합니다
          </h1>
          <p className="text-blue-100 text-lg leading-relaxed">
            회사 간 관계 네트워크, 임원 이력, CB 인수인 연결고리를 분석하여
            개인 투자자가 알기 어려운 리스크를 선제적으로 파악합니다.
          </p>
        </div>

        {/* 특징 목록 */}
        <div className="space-y-4">
          <div className="flex items-center gap-3 text-blue-100">
            <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <span>CB 네트워크 실시간 분석</span>
          </div>
          <div className="flex items-center gap-3 text-blue-100">
            <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <span>임원 경력 네트워크 추적</span>
          </div>
          <div className="flex items-center gap-3 text-blue-100">
            <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <span>RaymondsRisk 종합 점수</span>
          </div>
        </div>
      </div>

      {/* 오른쪽: 폼 영역 */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-theme-bg">
        <div className="w-full max-w-md">
          {/* 모바일 로고 */}
          <div className="lg:hidden text-center mb-8">
            <Link to="/">
              <img
                src="/logo.png?v=2"
                alt="Raymond Partners"
                className="h-14 w-auto object-contain mx-auto"
              />
            </Link>
          </div>

          {/* 탭 전환 */}
          <div className="bg-theme-card border border-theme-border rounded-2xl shadow-xl p-8">
            <div className="flex mb-8 bg-theme-surface rounded-lg p-1">
              <button
                onClick={() => setMode('login')}
                className={`flex-1 py-2.5 text-sm font-medium rounded-md transition-all ${
                  mode === 'login'
                    ? 'bg-theme-card text-accent-primary shadow-sm'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                로그인
              </button>
              <button
                onClick={() => setMode('register')}
                className={`flex-1 py-2.5 text-sm font-medium rounded-md transition-all ${
                  mode === 'register'
                    ? 'bg-theme-card text-accent-primary shadow-sm'
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
              />
            ) : (
              <RegisterForm
                onSuccess={handleSuccess}
                onSwitchToLogin={() => setMode('login')}
              />
            )}
          </div>

        </div>
      </div>
    </div>
  )
}

export default LoginPage

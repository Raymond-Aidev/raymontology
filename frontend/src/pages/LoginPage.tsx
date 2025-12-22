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
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-blue-600 via-blue-700 to-purple-700 p-8 xl:p-12 flex-col justify-between">
        <div>
          <Link to="/" className="inline-block">
            <div className="flex items-center gap-3">
              <img
                src="/logo.png?v=2"
                alt="RaymondsRisk"
                className="h-12 xl:h-16 w-auto object-contain"
              />
              <div className="text-white">
                <h2 className="text-xl xl:text-2xl font-bold">RaymondsRisk</h2>
                <p className="text-xs xl:text-sm text-blue-200">관계형 리스크 추적 분석</p>
              </div>
            </div>
          </Link>
        </div>

        <div className="text-white flex-1 flex flex-col justify-center py-8">
          <p className="text-blue-200 text-sm xl:text-base mb-3 font-medium">
            주식시장의 숨겨진 리스크 추적 분석 서비스
          </p>
          <h1 className="text-3xl xl:text-4xl 2xl:text-5xl font-bold mb-6 leading-tight">
            회사간 숨겨진 관계,<br />
            임원 리스크, CB 발행과<br />
            인수대상자 관계 리스크
          </h1>
          <p className="text-blue-100 text-base xl:text-lg leading-relaxed mb-8">
            투자 전 필수 점검 서비스.<br />
            3단계 관계망 분석으로 임원 이력, CB 인수자, 숨겨진 연결고리까지.
          </p>

          {/* 주요 기능 뱃지 */}
          <div className="flex flex-wrap gap-2 xl:gap-3">
            <span className="inline-flex items-center gap-1.5 px-3 xl:px-4 py-1.5 xl:py-2 bg-white/10 backdrop-blur-sm rounded-full text-xs xl:text-sm font-medium text-white border border-white/20">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              3단계 관계망 분석
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 xl:px-4 py-1.5 xl:py-2 bg-white/10 backdrop-blur-sm rounded-full text-xs xl:text-sm font-medium text-white border border-white/20">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              실시간 리스크 감지
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 xl:px-4 py-1.5 xl:py-2 bg-white/10 backdrop-blur-sm rounded-full text-xs xl:text-sm font-medium text-white border border-white/20">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              RaymondsRisk Score
            </span>
          </div>
        </div>

        {/* 하단 저작권 */}
        <div className="text-blue-200/60 text-xs">
          &copy; 2024 Raymond Partners. All rights reserved.
        </div>
      </div>

      {/* 오른쪽: 폼 영역 */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-theme-bg">
        <div className="w-full max-w-md">
          {/* 모바일 헤더 */}
          <div className="lg:hidden text-center mb-6">
            <Link to="/" className="inline-block mb-4">
              <div className="flex items-center justify-center gap-2">
                <img
                  src="/logo.png?v=2"
                  alt="RaymondsRisk"
                  className="h-10 w-auto object-contain"
                />
                <span className="text-lg font-bold text-text-primary">RaymondsRisk</span>
              </div>
            </Link>
            <p className="text-xs text-text-secondary mb-3">관계형 리스크 추적 분석 서비스</p>
            <div className="flex flex-wrap justify-center gap-1.5">
              <span className="px-2 py-1 bg-accent-primary/10 text-accent-primary text-[10px] rounded-full font-medium">
                3단계 관계망
              </span>
              <span className="px-2 py-1 bg-accent-primary/10 text-accent-primary text-[10px] rounded-full font-medium">
                실시간 감지
              </span>
              <span className="px-2 py-1 bg-accent-primary/10 text-accent-primary text-[10px] rounded-full font-medium">
                Risk Score
              </span>
            </div>
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

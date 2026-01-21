import { useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'
import RegisterForm from '../components/auth/RegisterForm'

function RegisterPage() {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading: authLoading } = useAuthStore()

  // 이미 로그인된 경우 홈으로 리다이렉트
  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      navigate('/', { replace: true })
    }
  }, [isAuthenticated, authLoading, navigate])

  return (
    <div className="min-h-screen bg-theme-bg flex items-center justify-center py-8 px-4 sm:px-6">
      <div className="w-full max-w-md">
        {/* 로고 */}
        <div className="flex justify-center mb-8">
          <Link to="/" className="inline-block">
            <RaymondsRiskLogo size="md" variant="compact" />
          </Link>
        </div>

        {/* 회원가입 카드 */}
        <div className="bg-theme-card border border-theme-border rounded-2xl p-8 shadow-xl">
          <h2 className="text-2xl font-bold text-text-primary mb-2 text-center">
            회원가입
          </h2>
          <p className="text-sm text-text-muted text-center mb-6">
            가입 시 1회 무료 기업 조회가 제공됩니다
          </p>

          <RegisterForm
            onSwitchToLogin={() => navigate('/login')}
          />
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

export default RegisterPage

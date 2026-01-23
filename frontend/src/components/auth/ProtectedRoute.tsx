import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuthStore()
  const location = useLocation()

  // 인증 체크 중일 때 로딩 표시
  if (isLoading) {
    return (
      <div className="min-h-screen bg-theme-bg flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-3 border-accent-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-text-secondary text-sm">인증 확인 중...</p>
        </div>
      </div>
    )
  }

  // 인증되지 않은 경우 로그인 페이지로 리다이렉트
  if (!isAuthenticated) {
    // 현재 위치를 저장하여 로그인 후 돌아올 수 있도록 함
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}

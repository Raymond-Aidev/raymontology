import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import AnalysisPage from './pages/AnalysisPage'
import PaywallPage from './pages/PaywallPage'
import PurchasePage from './pages/PurchasePage'
import MyCompaniesPage from './pages/MyCompaniesPage'
import LoginPage from './pages/LoginPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5분
      retry: 1,
    },
  },
})

// 인증 필수 래퍼 - 미인증시 로그인 페이지로 리다이렉트
function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  // 로딩 중
  if (isLoading) {
    return null
  }

  // 미인증 → 로그인 페이지
  if (!isAuthenticated) {
    return <LoginPage />
  }

  return <>{children}</>
}

function AppRoutes() {
  return (
    <BrowserRouter>
      <RequireAuth>
        <Routes>
          {/* 모든 페이지는 로그인 필수 */}
          <Route path="/" element={<HomePage />} />
          <Route path="/home" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />

          {/* 유료 전환 (Paywall) */}
          <Route path="/paywall" element={<PaywallPage />} />
          <Route path="/purchase" element={<PurchasePage />} />

          {/* 내 조회 기업 (MY) */}
          <Route path="/my" element={<MyCompaniesPage />} />

          {/* 유료 영역 (이용권 필요) - 통합 분석 페이지 */}
          <Route path="/report/:corpCode" element={<AnalysisPage />} />
          <Route path="/analysis/:corpCode" element={<AnalysisPage />} />
        </Routes>
      </RequireAuth>
    </BrowserRouter>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App

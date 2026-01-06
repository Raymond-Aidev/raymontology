import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './contexts/AuthContext'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import ReportPage from './pages/ReportPage'
import PaywallPage from './pages/PaywallPage'
import PurchasePage from './pages/PurchasePage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5분
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* 무료 영역 */}
            <Route path="/" element={<HomePage />} />
            <Route path="/home" element={<HomePage />} />
            <Route path="/search" element={<SearchPage />} />

            {/* 유료 전환 (Paywall) */}
            <Route path="/paywall" element={<PaywallPage />} />
            <Route path="/purchase" element={<PurchasePage />} />

            {/* 유료 영역 (이용권 필요) */}
            <Route path="/report/:corpCode" element={<ReportPage />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App

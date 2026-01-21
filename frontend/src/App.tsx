import { lazy, Suspense, useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import { PageLoading } from './components/common/Loading'
import ProtectedRoute from './components/auth/ProtectedRoute'
import { useAuthStore } from './store/authStore'

// Lazy load pages for code splitting
const LoginPage = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage'))
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage'))
const OAuthCallbackPage = lazy(() => import('./pages/OAuthCallbackPage'))
const MainSearchPage = lazy(() => import('./pages/MainSearchPage'))
const GraphPage = lazy(() => import('./pages/GraphPage'))
const ReportPage = lazy(() => import('./pages/ReportPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))
const AboutPage = lazy(() => import('./pages/AboutPage'))
const ContactPage = lazy(() => import('./pages/ContactPage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))
const TermsPage = lazy(() => import('./pages/TermsPage'))
const PrivacyPage = lazy(() => import('./pages/PrivacyPage'))
const VerifyEmailPage = lazy(() => import('./pages/VerifyEmailPage'))
const PricingPage = lazy(() => import('./pages/PricingPage'))
const PaymentSuccessPage = lazy(() => import('./pages/PaymentSuccessPage'))
const PaymentFailPage = lazy(() => import('./pages/PaymentFailPage'))
const RaymondsIndexRankingPage = lazy(() => import('./pages/RaymondsIndexRankingPage'))
const ServiceApplicationPage = lazy(() => import('./pages/ServiceApplicationPage'))
const ViewedCompaniesPage = lazy(() => import('./pages/ViewedCompaniesPage'))

function App() {
  const checkAuth = useAuthStore((state) => state.checkAuth)

  // 앱 시작 시 인증 상태 확인
  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  return (
    <Suspense fallback={<PageLoading />}>
      <Routes>
        {/* Auth pages (no header) */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/oauth/callback" element={<OAuthCallbackPage />} />

        {/* Admin page (separate layout) */}
        <Route path="/admin" element={<AdminPage />} />

        {/* Public MainLayout routes (shared header) */}
        <Route element={<MainLayout />}>
          <Route path="/" element={<MainSearchPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/contact" element={<ContactPage />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/raymonds-index" element={<RaymondsIndexRankingPage />} />
          <Route path="/payment/success" element={<PaymentSuccessPage />} />
          <Route path="/payment/fail" element={<PaymentFailPage />} />
        </Route>

        {/* Protected routes */}
        <Route element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }>
          <Route path="/company/:companyId/graph" element={<GraphPage />} />
          <Route path="/company/:companyId/report" element={<ReportPage />} />
          <Route path="/service-application" element={<ServiceApplicationPage />} />
          <Route path="/viewed-companies" element={<ViewedCompaniesPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}

export default App

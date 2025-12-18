import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import { PageLoading } from './components/common/Loading'

// Lazy load pages for code splitting
const LoginPage = lazy(() => import('./pages/LoginPage'))
const MainSearchPage = lazy(() => import('./pages/MainSearchPage'))
const GraphPage = lazy(() => import('./pages/GraphPage'))
const ReportPage = lazy(() => import('./pages/ReportPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))

function App() {
  return (
    <Suspense fallback={<PageLoading />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<MainLayout />}>
          <Route path="/" element={<MainSearchPage />} />
          <Route path="/company/:companyId/graph" element={<GraphPage />} />
          <Route path="/company/:companyId/report" element={<ReportPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}

export default App

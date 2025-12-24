import { Link } from 'react-router-dom'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'

function PricingPage() {
  return (
    <div className="min-h-screen bg-theme-bg">
      {/* Header */}
      <header className="bg-dark-surface/80 backdrop-blur-xl border-b border-dark-border sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <Link to="/" className="inline-block">
              <RaymondsRiskLogo size="sm" variant="compact" />
            </Link>
            <nav className="flex items-center gap-4">
              <Link
                to="/"
                className="text-sm text-text-secondary hover:text-text-primary transition-colors"
              >
                홈
              </Link>
              <Link
                to="/about"
                className="text-sm text-text-secondary hover:text-text-primary transition-colors"
              >
                서비스 소개
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-theme-card border border-theme-border rounded-2xl p-8">
          <div className="text-center py-20">
            <div className="w-16 h-16 bg-accent-primary/10 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-8 h-8 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-text-primary mb-4">이용권</h1>
            <p className="text-text-secondary text-lg">
              현재 준비중입니다
            </p>
            <p className="text-text-tertiary text-sm mt-2">
              서비스 준비가 완료되면 안내드리겠습니다.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}

export default PricingPage

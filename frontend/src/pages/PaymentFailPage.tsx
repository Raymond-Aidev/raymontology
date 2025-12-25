import { Link, useSearchParams } from 'react-router-dom'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'

function PaymentFailPage() {
  const [searchParams] = useSearchParams()
  const errorCode = searchParams.get('code')
  const errorMessage = searchParams.get('message')

  return (
    <div className="min-h-screen bg-theme-bg flex flex-col">
      {/* Header */}
      <header className="bg-dark-surface/80 backdrop-blur-xl border-b border-dark-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-center h-14">
            <Link to="/">
              <RaymondsRiskLogo size="sm" variant="compact" />
            </Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-theme-card border border-theme-border rounded-2xl p-8 text-center">
            <div className="w-16 h-16 bg-accent-danger/10 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-8 h-8 text-accent-danger" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>

            <h1 className="text-2xl font-bold text-text-primary mb-2">
              결제 실패
            </h1>
            <p className="text-text-secondary mb-6">
              {errorMessage || '결제가 취소되었거나 처리에 실패했습니다.'}
            </p>

            {errorCode && (
              <div className="bg-theme-surface rounded-lg p-3 mb-6">
                <p className="text-sm text-text-muted">
                  오류 코드: {errorCode}
                </p>
              </div>
            )}

            <div className="space-y-3">
              <Link
                to="/pricing"
                className="block w-full py-3 bg-accent-primary hover:bg-accent-primary/90 text-white font-medium rounded-xl transition-colors"
              >
                다시 시도
              </Link>
              <Link
                to="/"
                className="block w-full py-3 bg-theme-surface border border-theme-border hover:border-theme-border-hover text-text-primary font-medium rounded-xl transition-colors"
              >
                홈으로
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default PaymentFailPage

import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'
import apiClient from '../api/client'

function PaymentSuccessPage() {
  const [searchParams] = useSearchParams()
  const { isAuthenticated } = useAuthStore()
  const [isVerifying, setIsVerifying] = useState(true)
  const [result, setResult] = useState<{
    success: boolean
    message: string
    tier?: string
    expires_at?: string
  } | null>(null)

  const orderId = searchParams.get('orderId')
  const paymentKey = searchParams.get('paymentKey')
  const amount = searchParams.get('amount')

  useEffect(() => {
    if (orderId && paymentKey && amount && isAuthenticated) {
      verifyPayment()
    } else if (!isAuthenticated) {
      setIsVerifying(false)
      setResult({
        success: false,
        message: '로그인이 필요합니다.'
      })
    } else {
      setIsVerifying(false)
      setResult({
        success: false,
        message: '결제 정보가 올바르지 않습니다.'
      })
    }
  }, [orderId, paymentKey, amount, isAuthenticated])

  const verifyPayment = async () => {
    try {
      const response = await apiClient.post('/api/subscription/verify', {
        order_id: orderId,
        payment_key: paymentKey,
        amount: parseInt(amount || '0')
      })

      setResult(response.data)
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } }
      setResult({
        success: false,
        message: err.response?.data?.detail || '결제 확인에 실패했습니다.'
      })
    } finally {
      setIsVerifying(false)
    }
  }

  const tierNames: Record<string, string> = {
    light: '라이트',
    max: '맥스'
  }

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
            {isVerifying ? (
              <>
                <div className="w-16 h-16 mx-auto mb-6 flex items-center justify-center">
                  <div className="w-12 h-12 border-4 border-accent-primary border-t-transparent rounded-full animate-spin" />
                </div>
                <h1 className="text-xl font-semibold text-text-primary mb-2">
                  결제 확인 중...
                </h1>
                <p className="text-text-secondary">
                  잠시만 기다려주세요.
                </p>
              </>
            ) : result?.success ? (
              <>
                <div className="w-16 h-16 bg-accent-success/10 rounded-full flex items-center justify-center mx-auto mb-6">
                  <svg className="w-8 h-8 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h1 className="text-2xl font-bold text-text-primary mb-2">
                  결제 완료
                </h1>
                <p className="text-text-secondary mb-6">
                  {result.message}
                </p>

                {result.tier && (
                  <div className="bg-theme-surface rounded-xl p-4 mb-6">
                    <p className="text-sm text-text-secondary mb-1">이용권</p>
                    <p className="text-lg font-semibold text-accent-primary">
                      {tierNames[result.tier] || result.tier}
                    </p>
                    {result.expires_at && (
                      <>
                        <p className="text-sm text-text-secondary mt-3 mb-1">유효기간</p>
                        <p className="text-text-primary">
                          {new Date(result.expires_at).toLocaleDateString('ko-KR')}까지
                        </p>
                      </>
                    )}
                  </div>
                )}

                <Link
                  to="/"
                  className="inline-block w-full py-3 bg-accent-primary hover:bg-accent-primary/90 text-white font-medium rounded-xl transition-colors"
                >
                  시작하기
                </Link>
              </>
            ) : (
              <>
                <div className="w-16 h-16 bg-accent-danger/10 rounded-full flex items-center justify-center mx-auto mb-6">
                  <svg className="w-8 h-8 text-accent-danger" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
                <h1 className="text-2xl font-bold text-text-primary mb-2">
                  결제 실패
                </h1>
                <p className="text-text-secondary mb-6">
                  {result?.message || '결제 처리에 실패했습니다.'}
                </p>

                <div className="space-y-3">
                  <Link
                    to="/pricing"
                    className="block w-full py-3 bg-accent-primary hover:bg-accent-primary/90 text-white font-medium rounded-xl transition-colors"
                  >
                    다시 시도
                  </Link>
                  <Link
                    to="/contact"
                    className="block w-full py-3 bg-theme-surface border border-theme-border hover:border-theme-border-hover text-text-primary font-medium rounded-xl transition-colors"
                  >
                    문의하기
                  </Link>
                </div>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

export default PaymentSuccessPage

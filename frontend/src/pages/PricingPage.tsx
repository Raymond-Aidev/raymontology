import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'
import apiClient from '../api/client'

// 환경변수로 이용권 기능 활성화 여부 제어 (기본: false = 준비중)
const PRICING_ENABLED = import.meta.env.VITE_PRICING_ENABLED === 'true'

interface SubscriptionPlan {
  tier: 'free' | 'light' | 'max'
  name: string
  name_ko: string
  price: number
  price_display: string
  features: string[]
}

interface UserSubscriptionStatus {
  tier: string
  tier_name: string
  expires_at: string | null
  is_active: boolean
  days_remaining: number | null
}

function PricingPage() {
  const navigate = useNavigate()
  const { isAuthenticated, user } = useAuthStore()
  const [plans, setPlans] = useState<SubscriptionPlan[]>([])
  const [currentStatus, setCurrentStatus] = useState<UserSubscriptionStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null)
  const [selectedDuration, setSelectedDuration] = useState(1) // 1개월 기본
  const [isProcessing, setIsProcessing] = useState(false)

  useEffect(() => {
    if (PRICING_ENABLED) {
      loadPlans()
      if (isAuthenticated) {
        loadSubscriptionStatus()
      }
    } else {
      setIsLoading(false)
    }
  }, [isAuthenticated])

  const loadPlans = async () => {
    try {
      const response = await apiClient.get('/api/subscription/plans')
      setPlans(response.data.plans)
    } catch (error) {
      console.error('Failed to load plans:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const loadSubscriptionStatus = async () => {
    try {
      const response = await apiClient.get('/api/subscription/status')
      setCurrentStatus(response.data)
    } catch (error) {
      console.error('Failed to load subscription status:', error)
    }
  }

  const handleSubscribe = async (tier: 'light' | 'max') => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: { pathname: '/pricing' } } })
      return
    }

    setSelectedPlan(tier)
    setIsProcessing(true)

    try {
      const response = await apiClient.post('/api/subscription/checkout', {
        tier,
        duration_months: selectedDuration
      })

      const { checkout_url } = response.data

      if (checkout_url) {
        // PG 결제 페이지로 이동
        window.location.href = checkout_url
      } else {
        // Mock 모드: 바로 성공 페이지로 (개발용)
        const searchParams = new URLSearchParams({
          orderId: response.data.order_id,
          paymentKey: `mock_${Date.now()}`,
          amount: response.data.amount.toString()
        })
        navigate(`/payment/success?${searchParams.toString()}`)
      }
    } catch (error) {
      console.error('Failed to create checkout:', error)
      alert('결제 요청 중 오류가 발생했습니다.')
    } finally {
      setIsProcessing(false)
      setSelectedPlan(null)
    }
  }

  const getPlanPrice = (basePrice: number) => {
    const total = basePrice * selectedDuration
    if (selectedDuration >= 12) {
      return Math.round(total * 0.8) // 20% 할인
    } else if (selectedDuration >= 6) {
      return Math.round(total * 0.9) // 10% 할인
    }
    return total
  }

  const getDiscountText = () => {
    if (selectedDuration >= 12) return '20% 할인'
    if (selectedDuration >= 6) return '10% 할인'
    return null
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-theme-bg flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-accent-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  // 이용권 기능 비활성화 시 페이지 표시
  if (!PRICING_ENABLED) {
    // trial 이용권 사용자에게는 다른 메시지 표시
    const isTrialUser = isAuthenticated && user?.subscription_tier === 'trial'

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
              {isTrialUser ? (
                <>
                  {/* Trial 사용자 안내 */}
                  <div className="w-16 h-16 bg-accent-success/10 rounded-full flex items-center justify-center mx-auto mb-6">
                    <svg className="w-8 h-8 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" />
                    </svg>
                  </div>
                  <h1 className="text-2xl font-bold text-text-primary mb-4">1회 무료 이용권</h1>
                  <p className="text-accent-success text-lg font-medium">
                    가입 기념으로 1회 무료 이용 가능합니다
                  </p>
                  <p className="text-text-secondary text-sm mt-3">
                    기업 관계도 분석을 1회 무료로 체험해보세요.
                  </p>
                  <Link
                    to="/"
                    className="inline-flex items-center gap-2 mt-6 px-6 py-3 bg-accent-primary hover:bg-accent-primary/90 text-white font-medium rounded-xl transition-colors"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    기업 검색하러 가기
                  </Link>
                </>
              ) : (
                <>
                  {/* 일반 사용자 - 준비중 안내 */}
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
                </>
              )}
            </div>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-theme-bg">
      {/* Header */}
      <header className="bg-dark-surface/80 backdrop-blur-xl border-b border-dark-border sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
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
              {isAuthenticated ? (
                <span className="text-sm text-text-muted">
                  {user?.email}
                </span>
              ) : (
                <Link
                  to="/login"
                  className="text-sm text-accent-primary hover:text-accent-primary/80 transition-colors"
                >
                  로그인
                </Link>
              )}
            </nav>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Title */}
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-text-primary mb-3">이용권</h1>
          <p className="text-text-secondary">
            비즈니스에 맞는 플랜을 선택하세요
          </p>
        </div>

        {/* Current Status */}
        {currentStatus && currentStatus.tier !== 'free' && (
          <div className="mb-8 p-4 bg-accent-primary/10 border border-accent-primary/30 rounded-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-secondary">현재 이용권</p>
                <p className="text-lg font-semibold text-text-primary">
                  {currentStatus.tier_name}
                  {currentStatus.days_remaining !== null && (
                    <span className="text-sm font-normal text-text-secondary ml-2">
                      ({currentStatus.days_remaining}일 남음)
                    </span>
                  )}
                </p>
              </div>
              {currentStatus.expires_at && (
                <div className="text-right">
                  <p className="text-sm text-text-secondary">만료일</p>
                  <p className="text-text-primary">
                    {new Date(currentStatus.expires_at).toLocaleDateString('ko-KR')}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Duration Selector */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex bg-theme-surface border border-theme-border rounded-xl p-1">
            {[
              { value: 1, label: '1개월' },
              { value: 6, label: '6개월', discount: '10%' },
              { value: 12, label: '12개월', discount: '20%' }
            ].map((option) => (
              <button
                key={option.value}
                onClick={() => setSelectedDuration(option.value)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  selectedDuration === option.value
                    ? 'bg-accent-primary text-white'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                {option.label}
                {option.discount && (
                  <span className={`ml-1 text-xs ${
                    selectedDuration === option.value ? 'text-white/80' : 'text-accent-success'
                  }`}>
                    -{option.discount}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Plans Grid */}
        <div className="grid md:grid-cols-3 gap-6">
          {plans.map((plan) => {
            const isCurrentPlan = currentStatus?.tier === plan.tier
            const isPaidPlan = plan.tier !== 'free'
            const displayPrice = isPaidPlan ? getPlanPrice(plan.price) : 0

            return (
              <div
                key={plan.tier}
                className={`relative bg-theme-card border rounded-2xl p-6 transition-all ${
                  plan.tier === 'max'
                    ? 'border-accent-primary shadow-lg shadow-accent-primary/10'
                    : 'border-theme-border'
                } ${isCurrentPlan ? 'ring-2 ring-accent-success' : ''}`}
              >
                {/* Popular Badge */}
                {plan.tier === 'max' && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="px-3 py-1 bg-accent-primary text-white text-xs font-medium rounded-full">
                      인기
                    </span>
                  </div>
                )}

                {/* Current Badge */}
                {isCurrentPlan && (
                  <div className="absolute -top-3 right-4">
                    <span className="px-3 py-1 bg-accent-success text-white text-xs font-medium rounded-full">
                      현재 이용중
                    </span>
                  </div>
                )}

                {/* Plan Header */}
                <div className="text-center mb-6">
                  <h3 className="text-lg font-semibold text-text-primary mb-1">
                    {plan.name_ko}
                  </h3>
                  <div className="flex items-baseline justify-center gap-1">
                    {isPaidPlan ? (
                      <>
                        <span className="text-3xl font-bold text-text-primary">
                          {displayPrice.toLocaleString()}
                        </span>
                        <span className="text-text-secondary">원</span>
                        {selectedDuration > 1 && (
                          <span className="text-sm text-text-muted">
                            /{selectedDuration}개월
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="text-3xl font-bold text-text-primary">무료</span>
                    )}
                  </div>
                  {isPaidPlan && getDiscountText() && (
                    <p className="text-sm text-accent-success mt-1">{getDiscountText()}</p>
                  )}
                  {isPaidPlan && (
                    <p className="text-xs text-text-muted mt-1">
                      월 {plan.price.toLocaleString()}원
                    </p>
                  )}
                </div>

                {/* Features */}
                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <svg
                        className={`w-5 h-5 flex-shrink-0 ${
                          plan.tier === 'max' ? 'text-accent-primary' : 'text-accent-success'
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      <span className="text-sm text-text-secondary">{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* CTA Button */}
                {plan.tier === 'free' ? (
                  <button
                    disabled
                    className="w-full py-3 rounded-xl text-sm font-medium bg-theme-surface text-text-muted cursor-not-allowed"
                  >
                    기본 제공
                  </button>
                ) : (
                  <button
                    onClick={() => handleSubscribe(plan.tier as 'light' | 'max')}
                    disabled={isProcessing || isCurrentPlan}
                    className={`w-full py-3 rounded-xl text-sm font-medium transition-all ${
                      isCurrentPlan
                        ? 'bg-accent-success/20 text-accent-success cursor-not-allowed'
                        : plan.tier === 'max'
                        ? 'bg-accent-primary hover:bg-accent-primary/90 text-white'
                        : 'bg-theme-surface border border-theme-border hover:border-accent-primary text-text-primary'
                    }`}
                  >
                    {isProcessing && selectedPlan === plan.tier ? (
                      <span className="flex items-center justify-center gap-2">
                        <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                        처리 중...
                      </span>
                    ) : isCurrentPlan ? (
                      '이용중'
                    ) : (
                      '구독하기'
                    )}
                  </button>
                )}
              </div>
            )
          })}
        </div>

        {/* Contact Section */}
        <div className="mt-12 text-center">
          <p className="text-text-secondary mb-4">
            기업 맞춤 플랜이 필요하신가요?
          </p>
          <Link
            to="/contact"
            className="inline-flex items-center gap-2 text-accent-primary hover:text-accent-primary/80 transition-colors"
          >
            문의하기
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
      </main>
    </div>
  )
}

export default PricingPage

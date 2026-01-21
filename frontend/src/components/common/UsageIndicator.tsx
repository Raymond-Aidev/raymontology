import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import apiClient from '../../api/client'

interface UsageData {
  query: {
    used: number
    limit: number
    remaining: number
    unlimited: boolean
  }
  report: {
    used: number
    limit: number
    remaining: number
    unlimited: boolean
  }
  year_month: string
}

function UsageIndicator() {
  const { isAuthenticated, user } = useAuthStore()
  const [usage, setUsage] = useState<UsageData | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (isAuthenticated && user) {
      loadUsage()
    }
  }, [isAuthenticated, user])

  const loadUsage = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.get('/api/subscription/usage')
      setUsage(response.data)
    } catch (error) {
      console.error('Failed to load usage:', error)
    } finally {
      setIsLoading(false)
    }
  }

  if (!isAuthenticated || !user) {
    return null
  }

  // free 이용권이면 표시하지 않음 (조회 불가)
  if (user.subscription_tier === 'free' || !user.subscription_tier) {
    return (
      <Link
        to="/pricing"
        className="flex items-center gap-1.5 px-2.5 py-1 bg-accent-primary/10 border border-accent-primary/30 rounded-lg hover:bg-accent-primary/20 transition-colors"
      >
        <svg className="w-3.5 h-3.5 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        <span className="text-xs font-medium text-accent-primary">이용권 필요</span>
      </Link>
    )
  }

  // trial 이용권 (회원가입 1회 무료 체험)
  if (user.subscription_tier === 'trial') {
    // usage 데이터 로드 중이면 로딩 표시
    if (isLoading || !usage) {
      return (
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-dark-card border border-dark-border rounded-lg">
          <div className="w-3 h-3 border-2 border-accent-success border-t-transparent rounded-full animate-spin" />
        </div>
      )
    }

    // 1회 체험 사용 완료 (query_count >= 1)
    if (usage.query.used >= 1) {
      return (
        <Link
          to="/pricing"
          className="flex items-center gap-1.5 px-2.5 py-1 bg-accent-danger/10 border border-accent-danger/30 rounded-lg hover:bg-accent-danger/20 transition-colors"
        >
          <svg className="w-3.5 h-3.5 text-accent-danger" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-xs font-medium text-accent-danger">이용권 필요</span>
        </Link>
      )
    }

    // 1회 체험 사용 가능
    return (
      <Link
        to="/pricing"
        className="flex items-center gap-1.5 px-2.5 py-1 bg-accent-success/10 border border-accent-success/30 rounded-lg hover:bg-accent-success/20 transition-colors"
      >
        <svg className="w-3.5 h-3.5 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" />
        </svg>
        <span className="text-xs font-medium text-accent-success">1회 체험</span>
      </Link>
    )
  }

  if (isLoading || !usage) {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 bg-dark-card border border-dark-border rounded-lg">
        <div className="w-3 h-3 border-2 border-accent-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  // 무제한인 경우
  if (usage.query.unlimited) {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 bg-purple-500/10 border border-purple-500/30 rounded-lg">
        <svg className="w-3.5 h-3.5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
        </svg>
        <span className="text-xs font-medium text-purple-400">무제한</span>
      </div>
    )
  }

  // 제한이 있는 경우 - 남은 횟수 표시
  const usedPercent = (usage.query.used / usage.query.limit) * 100
  const isLow = usage.query.remaining <= 5
  const isWarning = usage.query.remaining <= 10 && usage.query.remaining > 5

  return (
    <Link
      to="/pricing"
      className={`flex items-center gap-2 px-2.5 py-1 rounded-lg border transition-colors ${
        isLow
          ? 'bg-accent-danger/10 border-accent-danger/30 hover:bg-accent-danger/20'
          : isWarning
          ? 'bg-accent-warning/10 border-accent-warning/30 hover:bg-accent-warning/20'
          : 'bg-blue-500/10 border-blue-500/30 hover:bg-blue-500/20'
      }`}
    >
      {/* Progress bar */}
      <div className="w-12 h-1.5 bg-dark-bg rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            isLow ? 'bg-accent-danger' : isWarning ? 'bg-accent-warning' : 'bg-blue-400'
          }`}
          style={{ width: `${Math.min(usedPercent, 100)}%` }}
        />
      </div>
      <span className={`text-xs font-medium ${
        isLow ? 'text-accent-danger' : isWarning ? 'text-accent-warning' : 'text-blue-400'
      }`}>
        {usage.query.remaining}건 남음
      </span>
    </Link>
  )
}

export default UsageIndicator

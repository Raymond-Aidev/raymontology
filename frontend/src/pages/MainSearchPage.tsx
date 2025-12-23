import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { SearchInput } from '../components/common'
import { getHighRiskCompanies, getPlatformStats, type PlatformStats } from '../api/company'
import { useGraphStore } from '../store'
import { useAuthStore } from '../store/authStore'
import type { CompanySearchResult } from '../types/company'

// Risk level config for dark theme
const riskConfig: Record<string, { bg: string; text: string; border: string; label: string }> = {
  critical: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30', label: '위험' },
  high: { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/30', label: '높음' },
  medium: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/30', label: '보통' },
  low: { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/30', label: '낮음' },
  very_low: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30', label: '매우 낮음' },
}

// Grade colors
const gradeConfig: Record<string, string> = {
  'AAA': 'text-green-400',
  'AA': 'text-green-400',
  'A': 'text-blue-400',
  'BBB': 'text-blue-400',
  'BB': 'text-yellow-400',
  'B': 'text-orange-400',
  'CCC': 'text-red-400',
  'CC': 'text-red-400',
  'C': 'text-red-500',
  'D': 'text-red-600',
}

function MainSearchPage() {
  const navigate = useNavigate()
  const clearNavigation = useGraphStore((state) => state.clearNavigation)
  const { isAuthenticated } = useAuthStore()

  const [highRiskCompanies, setHighRiskCompanies] = useState<CompanySearchResult[]>([])
  const [isLoadingHighRisk, setIsLoadingHighRisk] = useState(true)
  const [highRiskError, setHighRiskError] = useState<string | null>(null)
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [stats, setStats] = useState<PlatformStats | null>(null)

  useEffect(() => {
    const loadData = async () => {
      setIsLoadingHighRisk(true)
      setHighRiskError(null)
      try {
        // 병렬로 데이터 로드
        const [companies, platformStats] = await Promise.all([
          getHighRiskCompanies(5, 6),
          getPlatformStats()
        ])
        setHighRiskCompanies(companies)
        setStats(platformStats)
      } catch (error) {
        console.error('데이터 로드 실패:', error)
        setHighRiskError('데이터를 불러오는데 실패했습니다')
      } finally {
        setIsLoadingHighRisk(false)
      }
    }

    loadData()
  }, [])

  const handleSelectCompany = useCallback((company: CompanySearchResult) => {
    // 로그인하지 않은 경우 모달 표시
    if (!isAuthenticated) {
      setShowLoginModal(true)
      return
    }
    // 새 검색 시 네비게이션 히스토리 초기화
    clearNavigation()
    // corp_code로 조회해야 CB 데이터가 함께 표시됨
    navigate(`/company/${company.corp_code}/graph`)
  }, [navigate, clearNavigation, isAuthenticated])

  return (
    <>
    <div className="min-h-[calc(100vh-200px)] flex flex-col">
      {/* Hero Section */}
      <section className="flex-1 flex flex-col items-center justify-center py-16 px-4 relative">
        {/* Background grid */}
        <div className="absolute inset-0 bg-grid opacity-50" />

        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-radial from-accent-primary/5 via-transparent to-transparent" />

        <div className="relative z-10 text-center mb-10 animate-fade-in">
          {/* Feature badges */}
          <div className="flex flex-wrap items-center justify-center gap-2 mb-8">
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-dark-card border border-dark-border rounded-full">
              <span className="text-sm">🔍</span>
              <span className="text-xs font-medium text-text-secondary">3단계 관계망 분석</span>
            </div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-dark-card border border-dark-border rounded-full">
              <span className="text-sm">⚡</span>
              <span className="text-xs font-medium text-text-secondary">실시간 리스크 탐지</span>
            </div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-dark-card border border-dark-border rounded-full">
              <span className="text-sm">📊</span>
              <span className="text-xs font-medium text-text-secondary">RaymondsRisk 스코어</span>
            </div>
          </div>

          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-text-primary mb-6 tracking-tight leading-tight">
            기관만 보던 리스크,
            <br />
            <span className="text-gradient">이제 당신도 봅니다.</span>
          </h1>
          <p className="text-lg md:text-xl text-text-secondary max-w-2xl mx-auto leading-relaxed">
            3단계 관계망 분석으로 임원 이력, CB 인수자, 숨겨진 연결고리까지.
            <br className="hidden sm:block" />
            <span className="text-accent-primary font-medium">RaymondsRisk</span>가 개인투자자의 눈이 되어드립니다.
          </p>
        </div>

        {/* Search */}
        <div className="relative z-10 w-full max-w-2xl animate-fade-in-up" style={{ animationDelay: '100ms' }}>
          <SearchInput
            placeholder="회사명 또는 종목코드를 입력하세요"
            onSelect={handleSelectCompany}
            size="lg"
          />
        </div>

        {/* Search hint */}
        <p className="relative z-10 mt-4 text-xs text-text-muted font-mono">
          <kbd className="px-1.5 py-0.5 bg-dark-card border border-dark-border rounded text-text-tertiary">↑↓</kbd>
          {' '}탐색{' '}
          <kbd className="px-1.5 py-0.5 bg-dark-card border border-dark-border rounded text-text-tertiary">Enter</kbd>
          {' '}선택{' '}
          <kbd className="px-1.5 py-0.5 bg-dark-card border border-dark-border rounded text-text-tertiary">Esc</kbd>
          {' '}닫기
        </p>

        {/* Stats row */}
        <div className="relative z-10 mt-12 flex flex-wrap items-center justify-center gap-6 md:gap-8 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
          <div className="text-center">
            <p className="text-xl md:text-2xl font-bold font-mono text-text-primary">
              {stats ? stats.companies.toLocaleString() : '3,922'}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wider">분석 기업</p>
          </div>
          <div className="w-px h-10 bg-dark-border hidden sm:block" />
          <div className="text-center">
            <p className="text-xl md:text-2xl font-bold font-mono text-text-primary">
              {stats ? stats.convertible_bonds.toLocaleString() : '1,463'}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wider">CB 발행</p>
          </div>
          <div className="w-px h-10 bg-dark-border hidden sm:block" />
          <div className="text-center">
            <p className="text-xl md:text-2xl font-bold font-mono text-text-primary">
              {stats ? (stats.officers >= 1000 ? `${Math.floor(stats.officers / 1000)}K+` : stats.officers.toLocaleString()) : '44K+'}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wider">임원 데이터</p>
          </div>
          <div className="w-px h-10 bg-dark-border hidden sm:block" />
          <div className="text-center">
            <p className="text-xl md:text-2xl font-bold font-mono text-text-primary">
              {stats ? (stats.major_shareholders >= 1000 ? `${Math.floor(stats.major_shareholders / 1000)}K+` : stats.major_shareholders.toLocaleString()) : '95K+'}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wider">주주변동</p>
          </div>
          <div className="w-px h-10 bg-dark-border hidden sm:block" />
          <div className="text-center">
            <p className="text-xl md:text-2xl font-bold font-mono text-text-primary">
              {stats ? stats.financial_statements.toLocaleString() : '9,432'}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wider">재무지표</p>
          </div>
        </div>
      </section>

      {/* High Risk Companies - Bloomberg Terminal Style */}
      <section className="py-12 px-4">
        <div className="max-w-6xl mx-auto">
          {/* Section Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-1 h-6 bg-accent-danger rounded-full" />
              <div>
                <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                  <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                  주의 필요 기업
                </h2>
                <p className="text-xs text-text-muted mt-0.5">
                  리스크 레벨이 높은 기업 목록 • 실시간 모니터링
                </p>
              </div>
            </div>
            <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-secondary hover:text-text-primary bg-dark-card border border-dark-border rounded-lg hover:border-accent-primary/50 transition-all">
              전체 보기
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>

          {/* Loading */}
          {isLoadingHighRisk && (
            <div className="flex items-center justify-center py-16">
              <div className="flex flex-col items-center gap-3">
                <div className="w-8 h-8 border-2 border-accent-primary border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-text-muted font-mono">데이터 로딩 중...</span>
              </div>
            </div>
          )}

          {/* Error */}
          {highRiskError && !isLoadingHighRisk && highRiskCompanies.length === 0 && (
            <div className="text-center py-16">
              <div className="w-16 h-16 mx-auto mb-4 bg-dark-card border border-dark-border rounded-xl flex items-center justify-center">
                <svg className="w-8 h-8 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <p className="text-text-secondary">{highRiskError}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-4 px-4 py-2 text-sm text-accent-primary hover:text-accent-primary/80 transition-colors"
              >
                다시 시도
              </button>
            </div>
          )}

          {/* Empty */}
          {!isLoadingHighRisk && !highRiskError && highRiskCompanies.length === 0 && (
            <div className="text-center py-16">
              <div className="w-16 h-16 mx-auto mb-4 bg-dark-card border border-dark-border rounded-xl flex items-center justify-center">
                <svg className="w-8 h-8 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-text-secondary">현재 고위험 기업이 없습니다</p>
            </div>
          )}

          {/* Cards Grid */}
          {!isLoadingHighRisk && highRiskCompanies.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {highRiskCompanies.map((company, index) => {
                const risk = company.risk_level ? riskConfig[company.risk_level] : null
                const gradeColor = company.investment_grade ? gradeConfig[company.investment_grade] : 'text-text-muted'

                return (
                  <button
                    key={company.id}
                    onClick={() => handleSelectCompany(company)}
                    className="group bg-dark-card border border-dark-border rounded-xl p-4
                               hover:border-accent-primary/50 hover:shadow-glow
                               transition-all duration-300 text-left
                               animate-fade-in-up"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    {/* Header */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-text-primary truncate group-hover:text-accent-primary transition-colors">
                          {company.name}
                        </h3>
                        <p className="text-xs font-mono text-text-muted mt-0.5">{company.corp_code}</p>
                      </div>
                      {company.investment_grade && (
                        <span className={`text-xl font-bold font-mono ${gradeColor}`}>
                          {company.investment_grade}
                        </span>
                      )}
                    </div>

                    {/* Stats Row */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {/* CB Count */}
                        <div className="flex items-center gap-1.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-accent-purple" />
                          <span className="text-xs font-mono text-text-secondary">
                            CB <span className="text-accent-purple">{company.cb_count}</span>
                          </span>
                        </div>
                      </div>

                      {/* Risk Badge */}
                      {risk && (
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${risk.bg} ${risk.text} ${risk.border}`}>
                          {risk.label}
                        </span>
                      )}
                    </div>

                    {/* Hover indicator */}
                    <div className="mt-3 pt-3 border-t border-dark-border opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-end text-xs text-accent-primary">
                      관계도 분석
                      <svg className="w-3.5 h-3.5 ml-1 transform group-hover:translate-x-1 transition-transform"
                           fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                      </svg>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 px-4 border-t border-dark-border">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-xl font-semibold text-center text-text-primary mb-12">
            분석 영역
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* CB Network */}
            <div className="group p-6 bg-dark-card border border-dark-border rounded-xl hover:border-accent-purple/50 hover:shadow-glow-purple transition-all">
              <div className="w-12 h-12 mb-4 bg-accent-purple/10 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <svg className="w-6 h-6 text-accent-purple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="font-semibold text-text-primary mb-2">CB 네트워크</h3>
              <p className="text-sm text-text-secondary leading-relaxed">
                전환사채 발행 이력과 인수인 간 연결관계를 분석합니다
              </p>
              <div className="mt-4 pt-4 border-t border-dark-border">
                <div className="flex items-center gap-2 text-xs text-text-muted">
                  <span className="font-mono">1,435</span>
                  <span>건의 CB 발행 분석</span>
                </div>
              </div>
            </div>

            {/* Officer Network */}
            <div className="group p-6 bg-dark-card border border-dark-border rounded-xl hover:border-accent-success/50 hover:shadow-glow-green transition-all">
              <div className="w-12 h-12 mb-4 bg-accent-success/10 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <svg className="w-6 h-6 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <h3 className="font-semibold text-text-primary mb-2">임원 네트워크</h3>
              <p className="text-sm text-text-secondary leading-relaxed">
                임원진의 타사 겸직 및 과거 이력을 통한 회사 간 연결고리를 파악합니다
              </p>
              <div className="mt-4 pt-4 border-t border-dark-border">
                <div className="flex items-center gap-2 text-xs text-text-muted">
                  <span className="font-mono">38,125</span>
                  <span>명의 임원 데이터</span>
                </div>
              </div>
            </div>

            {/* Financial Risk */}
            <div className="group p-6 bg-dark-card border border-dark-border rounded-xl hover:border-accent-warning/50 transition-all">
              <div className="w-12 h-12 mb-4 bg-accent-warning/10 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <svg className="w-6 h-6 text-accent-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="font-semibold text-text-primary mb-2">재무 건전성</h3>
              <p className="text-sm text-text-secondary leading-relaxed">
                부채비율, 영업이익, 자산규모 등 핵심 재무지표를 종합 평가합니다
              </p>
              <div className="mt-4 pt-4 border-t border-dark-border">
                <div className="flex items-center gap-2 text-xs text-text-muted">
                  <span className="font-mono">9,432</span>
                  <span>건의 재무제표</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    {/* Login Required Modal */}
    {showLoginModal && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
        <div className="bg-dark-card border border-dark-border rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl animate-scale-in">
          {/* Icon */}
          <div className="w-14 h-14 mx-auto mb-4 bg-accent-primary/10 rounded-2xl flex items-center justify-center">
            <svg className="w-7 h-7 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>

          {/* Title */}
          <h3 className="text-lg font-semibold text-text-primary text-center mb-2">
            로그인이 필요합니다
          </h3>

          {/* Description */}
          <p className="text-sm text-text-secondary text-center mb-6">
            기업 관계도와 상세 분석 데이터를 보려면
            <br />
            로그인이 필요합니다.
          </p>

          {/* Buttons */}
          <div className="flex flex-col gap-3">
            <button
              onClick={() => {
                setShowLoginModal(false)
                navigate('/login')
              }}
              className="w-full py-3 px-4 bg-accent-primary hover:bg-accent-primary/90 text-white font-medium rounded-xl transition-colors"
            >
              로그인하기
            </button>
            <button
              onClick={() => setShowLoginModal(false)}
              className="w-full py-3 px-4 bg-dark-surface hover:bg-dark-hover border border-dark-border text-text-secondary font-medium rounded-xl transition-colors"
            >
              취소
            </button>
          </div>

          {/* Register link */}
          <p className="mt-4 text-center text-sm text-text-muted">
            계정이 없으신가요?{' '}
            <button
              onClick={() => {
                setShowLoginModal(false)
                navigate('/login')
              }}
              className="text-accent-primary hover:underline"
            >
              회원가입
            </button>
          </p>
        </div>
      </div>
    )}
    </>
  )
}

export default MainSearchPage

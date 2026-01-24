import { useSearchParams, useNavigate } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'
import { searchCompanies } from '../api/company'
import type { CompanySearchResult } from '../types/company'
import { riskLevelConfig, type RiskLevel } from '../types/company'
import { colors } from '../constants/colors'

export default function SearchPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const query = searchParams.get('q') || ''

  const [searchInput, setSearchInput] = useState(query)
  const [results, setResults] = useState<CompanySearchResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 기업 클릭 핸들러 - 상세 페이지로 이동 (이용권 체크는 ReportPage에서)
  const handleCompanyClick = useCallback((company: CompanySearchResult) => {
    // 항상 리포트 페이지로 이동 (이용권 체크는 리포트 페이지에서 수행)
    // 이렇게 하면 사용자가 기업 검색 결과를 볼 수 있고, 상세 조회 시점에 이용권 확인
    navigate(`/report/${company.corp_code}`, {
      state: { companyName: company.name }
    })
  }, [navigate])

  useEffect(() => {
    if (query) {
      setIsLoading(true)
      setError(null)
      searchCompanies(query)
        .then(setResults)
        .catch(() => {
          setError('검색 중 오류가 발생했습니다. 다시 시도해주세요.')
        })
        .finally(() => setIsLoading(false))
    }
  }, [query])

  const handleSearch = () => {
    if (searchInput.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchInput)}`)
    }
  }

  const handleRetry = () => {
    if (query) {
      setIsLoading(true)
      setError(null)
      searchCompanies(query)
        .then(setResults)
        .catch(() => {
          setError('검색 중 오류가 발생했습니다. 다시 시도해주세요.')
        })
        .finally(() => setIsLoading(false))
    }
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: colors.white }}>
      {/* Top Navigation Bar */}
      <header
        style={{
          padding: '12px 20px',
          paddingTop: 'max(env(safe-area-inset-top), 12px)',
          backgroundColor: colors.white,
          position: 'sticky',
          top: 0,
          zIndex: 100,
        }}
        role="banner"
      >
        <h1 style={{
          fontSize: '22px',
          fontWeight: '700',
          margin: 0,
          letterSpacing: '-0.02em'
        }}>
          <span style={{ color: colors.gray900 }}>레이먼즈</span>
          <span style={{ color: colors.red500 }}>리스크</span>
        </h1>
      </header>

      <main style={{ padding: '0 20px 32px' }} role="main">
        {/* 검색 섹션 */}
        <section style={{ marginBottom: '16px' }} aria-label="기업 검색">
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="기업명 검색"
              aria-label="기업명 검색"
              style={{
                flex: 1,
                padding: '14px 16px',
                borderRadius: '12px',
                border: 'none',
                backgroundColor: colors.gray50,
                color: colors.gray900,
                fontSize: '16px',
                fontWeight: '400',
                outline: 'none',
                minHeight: '48px',
              }}
            />
            <button
              onClick={handleSearch}
              aria-label="검색하기"
              style={{
                padding: '14px 20px',
                borderRadius: '12px',
                border: 'none',
                backgroundColor: colors.blue500,
                color: colors.white,
                fontSize: '16px',
                fontWeight: '600',
                cursor: 'pointer',
                minWidth: '48px',
                minHeight: '48px',
              }}
            >
              검색
            </button>
          </div>
        </section>

        {/* 홈으로 버튼 */}
        <section style={{ marginBottom: '20px' }}>
          <button
            onClick={() => navigate('/')}
            aria-label="홈으로 돌아가기"
            style={{
              padding: '10px 16px',
              borderRadius: '8px',
              border: `1px solid ${colors.gray100}`,
              backgroundColor: colors.white,
              color: colors.gray900,
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer',
              minHeight: '44px',
            }}
          >
            ← 홈으로
          </button>
        </section>

        {/* 검색 결과 */}
        <section aria-label="검색 결과" aria-live="polite">
          {isLoading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState message={error} onRetry={handleRetry} />
          ) : results.length === 0 ? (
            <EmptyState hasQuery={!!query} />
          ) : (
            <>
              <p style={{
                fontSize: '14px',
                color: colors.gray500,
                marginBottom: '12px'
              }}>
                검색결과 {results.length}건
              </p>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {results.map((company, index) => (
                  <li key={company.id}>
                    <CompanyListRow
                      company={company}
                      onClick={() => handleCompanyClick(company)}
                      isLast={index === results.length - 1}
                    />
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </main>
    </div>
  )
}

// 로딩 상태 컴포넌트
function LoadingState() {
  return (
    <div
      style={{
        padding: '40px 0',
      }}
      role="status"
      aria-label="검색 중"
    >
      {/* 스켈레톤 UI */}
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          style={{
            padding: '16px 0',
            borderBottom: i < 3 ? `1px solid ${colors.gray100}` : 'none',
          }}
        >
          <div
            style={{
              height: '20px',
              width: '60%',
              backgroundColor: colors.gray100,
              borderRadius: '4px',
              marginBottom: '8px',
              animation: 'pulse 1.5s ease-in-out infinite',
            }}
          />
          <div
            style={{
              height: '16px',
              width: '80%',
              backgroundColor: colors.gray100,
              borderRadius: '4px',
              animation: 'pulse 1.5s ease-in-out infinite',
            }}
          />
        </div>
      ))}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  )
}

// 에러 상태 컴포넌트
function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div
      style={{
        textAlign: 'center',
        padding: '60px 20px',
      }}
      role="alert"
    >
      <div style={{
        width: '64px',
        height: '64px',
        borderRadius: '50%',
        backgroundColor: '#FEE2E2',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '0 auto 16px',
        fontSize: '28px',
      }}>
        ⚠️
      </div>
      <p style={{
        fontSize: '16px',
        color: colors.gray900,
        marginBottom: '8px',
        fontWeight: '500',
      }}>
        오류가 발생했습니다
      </p>
      <p style={{
        fontSize: '14px',
        color: colors.gray500,
        marginBottom: '20px',
      }}>
        {message}
      </p>
      <button
        onClick={onRetry}
        aria-label="다시 시도"
        style={{
          padding: '12px 24px',
          borderRadius: '8px',
          border: 'none',
          backgroundColor: colors.blue500,
          color: colors.white,
          fontSize: '15px',
          fontWeight: '600',
          cursor: 'pointer',
          minHeight: '44px',
        }}
      >
        다시 시도
      </button>
    </div>
  )
}

// 빈 상태 컴포넌트
function EmptyState({ hasQuery }: { hasQuery: boolean }) {
  return (
    <div
      style={{
        textAlign: 'center',
        padding: '60px 20px',
      }}
    >
      <div style={{
        width: '64px',
        height: '64px',
        borderRadius: '50%',
        backgroundColor: colors.gray50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '0 auto 16px',
        fontSize: '28px',
      }}>
        🔍
      </div>
      <p style={{
        fontSize: '16px',
        color: colors.gray900,
        marginBottom: '8px',
        fontWeight: '500',
      }}>
        {hasQuery ? '검색 결과가 없습니다' : '기업을 검색해보세요'}
      </p>
      <p style={{
        fontSize: '14px',
        color: colors.gray500,
      }}>
        {hasQuery
          ? '다른 검색어로 다시 시도해주세요'
          : '기업명을 입력하면 관련 정보를 확인할 수 있습니다'}
      </p>
    </div>
  )
}

function CompanyListRow({
  company,
  onClick,
  isLast = false
}: {
  company: CompanySearchResult
  onClick: () => void
  isLast?: boolean
}) {
  const riskConfig = company.risk_level
    ? riskLevelConfig[company.risk_level as RiskLevel]
    : null

  const getBadgeColors = (color: string) => {
    if (color === '#EF4444') return { bg: '#FEE2E2', text: '#DC2626' }
    if (color === '#F59E0B') return { bg: '#FEF3C7', text: '#D97706' }
    return { bg: '#D1FAE5', text: '#059669' }
  }

  const badgeColors = riskConfig ? getBadgeColors(riskConfig.color) : null

  // 거래정지 여부 확인
  const isSuspended = company.trading_status === 'SUSPENDED' || company.trading_status === 'TRADING_HALT'

  return (
    <div
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      role="button"
      tabIndex={0}
      aria-label={`${company.name} 상세 보기${isSuspended ? ' (거래정지)' : ''}`}
      style={{
        padding: '16px 0',
        borderBottom: isLast ? 'none' : `1px solid ${colors.gray100}`,
        cursor: 'pointer',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        minHeight: '72px',
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: '16px',
          fontWeight: '500',
          color: colors.gray900,
          marginBottom: '4px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}>
          {company.name}
          {isSuspended && (
            <span style={{
              padding: '2px 6px',
              borderRadius: '4px',
              fontSize: '10px',
              fontWeight: '600',
              backgroundColor: '#FEE2E2',
              color: '#DC2626',
              whiteSpace: 'nowrap',
            }}>
              거래정지
            </span>
          )}
        </div>
        <div style={{
          fontSize: '14px',
          color: colors.gray500,
        }}>
          {company.corp_code} · CB {company.cb_count}회
          {company.investment_grade ? ` · ${company.investment_grade}` : ''}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: '12px' }}>
        {riskConfig && badgeColors && (
          <span style={{
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '12px',
            fontWeight: '600',
            backgroundColor: badgeColors.bg,
            color: badgeColors.text,
            whiteSpace: 'nowrap'
          }}>
            {riskConfig.label}
          </span>
        )}
        <span style={{ color: colors.gray500, fontSize: '18px' }} aria-hidden="true">›</span>
      </div>
    </div>
  )
}

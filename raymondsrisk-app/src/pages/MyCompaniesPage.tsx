import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import * as creditService from '../services/creditService'
import type { ViewedCompany } from '../services/creditService'
import { colors } from '../constants/colors'

export default function MyCompaniesPage() {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading: authLoading, credits, login, refreshCredits } = useAuth()

  const [companies, setCompanies] = useState<ViewedCompany[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retentionDays, setRetentionDays] = useState(30)

  // 페이지 진입 시 이용권 잔액 새로고침 (캐시 동기화)
  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      refreshCredits()
    }
  }, [isAuthenticated, authLoading, refreshCredits])

  // 조회한 기업 목록 로드
  useEffect(() => {
    let isMounted = true  // 메모리 릭 방지

    const loadCompanies = async () => {
      if (!isAuthenticated) {
        if (isMounted) setIsLoading(false)
        return
      }

      try {
        const data = await creditService.getViewedCompanies(50, false)
        if (!isMounted) return  // 언마운트 체크
        setCompanies(data.companies)
        setRetentionDays(data.retentionDays)
      } catch {
        if (!isMounted) return  // 언마운트 체크
        setError('목록을 불러올 수 없습니다')
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }

    if (!authLoading) {
      loadCompanies()
    }

    return () => {
      isMounted = false  // cleanup
    }
  }, [isAuthenticated, authLoading])

  // 로그인 필요
  if (!authLoading && !isAuthenticated) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: colors.white }}>
        <Header navigate={navigate} />
        <main style={{ padding: '40px 20px', textAlign: 'center' }}>
          <div style={{
            width: '80px',
            height: '80px',
            borderRadius: '50%',
            backgroundColor: colors.blue500 + '15',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 24px',
            fontSize: '36px',
          }}>
            🔒
          </div>
          <h2 style={{
            fontSize: '20px',
            fontWeight: '700',
            color: colors.gray900,
            margin: '0 0 8px 0',
          }}>
            로그인이 필요해요
          </h2>
          <p style={{
            fontSize: '15px',
            color: colors.gray500,
            margin: '0 0 24px 0',
          }}>
            내 조회 기업을 확인하려면 로그인하세요
          </p>
          <button
            onClick={() => login()}
            style={{
              padding: '16px 32px',
              borderRadius: '12px',
              border: 'none',
              backgroundColor: colors.blue500,
              color: colors.white,
              fontSize: '16px',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            토스로 로그인
          </button>
        </main>
      </div>
    )
  }

  // 로딩 중
  if (authLoading || isLoading) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: colors.white }}>
        <Header navigate={navigate} />
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '60px 20px',
        }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: `3px solid ${colors.gray100}`,
            borderTopColor: colors.blue500,
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
          }} />
          <style>{`
            @keyframes spin {
              to { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: colors.gray50 }}>
      <Header navigate={navigate} />

      <main style={{ padding: '16px 20px 32px' }}>
        {/* 보유 이용권 카드 */}
        <section style={{
          backgroundColor: colors.white,
          borderRadius: '16px',
          padding: '20px',
          marginBottom: '16px',
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div>
              <div style={{ fontSize: '14px', color: colors.gray500, marginBottom: '4px' }}>
                보유 이용권
              </div>
              <div style={{ fontSize: '28px', fontWeight: '700', color: colors.blue500 }}>
                {credits === -1 ? '무제한' : `${credits}건`}
              </div>
            </div>
            <button
              onClick={() => navigate('/purchase')}
              style={{
                padding: '12px 20px',
                borderRadius: '10px',
                border: 'none',
                backgroundColor: colors.blue500,
                color: colors.white,
                fontSize: '14px',
                fontWeight: '600',
                cursor: 'pointer',
              }}
            >
              충전하기
            </button>
          </div>
        </section>

        {/* 안내 문구 */}
        <div style={{
          padding: '12px 16px',
          backgroundColor: colors.blue500 + '10',
          borderRadius: '10px',
          marginBottom: '16px',
        }}>
          <p style={{
            fontSize: '13px',
            color: colors.blue500,
            margin: 0,
          }}>
            조회한 기업은 {retentionDays}일간 무료로 다시 볼 수 있어요
          </p>
        </div>

        {/* 에러 */}
        {error && (
          <div style={{
            padding: '16px',
            backgroundColor: colors.red500 + '10',
            borderRadius: '12px',
            marginBottom: '16px',
          }}>
            <p style={{ fontSize: '14px', color: colors.red500, margin: 0 }}>
              {error}
            </p>
          </div>
        )}

        {/* 기업 목록 */}
        <section>
          <h2 style={{
            fontSize: '14px',
            fontWeight: '600',
            color: colors.gray500,
            margin: '0 0 12px 0',
          }}>
            내 조회 기업 ({companies.length}건)
          </h2>

          {companies.length === 0 ? (
            <div style={{
              backgroundColor: colors.white,
              borderRadius: '16px',
              padding: '40px 20px',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: '48px', marginBottom: '12px' }}>📋</div>
              <p style={{
                fontSize: '15px',
                color: colors.gray500,
                margin: '0 0 16px 0',
              }}>
                아직 조회한 기업이 없어요
              </p>
              <button
                onClick={() => navigate('/search')}
                style={{
                  padding: '12px 24px',
                  borderRadius: '10px',
                  border: `1px solid ${colors.blue500}`,
                  backgroundColor: colors.white,
                  color: colors.blue500,
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                기업 검색하기
              </button>
            </div>
          ) : (
            <div style={{
              backgroundColor: colors.white,
              borderRadius: '16px',
              overflow: 'hidden',
            }}>
              {companies.map((company, index) => (
                <CompanyItem
                  key={company.companyId}
                  company={company}
                  isLast={index === companies.length - 1}
                  onView={() => navigate(`/report/${company.companyId}`, {
                    state: { companyName: company.companyName }
                  })}
                />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

// 헤더 컴포넌트
function Header({ navigate }: { navigate: ReturnType<typeof useNavigate> }) {
  return (
    <header
      style={{
        padding: '12px 20px',
        paddingTop: 'max(env(safe-area-inset-top), 12px)',
        backgroundColor: colors.white,
        position: 'sticky',
        top: 0,
        zIndex: 100,
        borderBottom: `1px solid ${colors.gray100}`,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            padding: '8px',
            border: 'none',
            background: 'none',
            cursor: 'pointer',
            fontSize: '20px',
            color: colors.gray900,
          }}
          aria-label="뒤로가기"
        >
          ←
        </button>
        <h1 style={{
          fontSize: '18px',
          fontWeight: '600',
          margin: 0,
          color: colors.gray900,
        }}>
          내 조회 기업
        </h1>
      </div>
    </header>
  )
}

// 기업 아이템 컴포넌트
function CompanyItem({
  company,
  isLast,
  onView,
}: {
  company: ViewedCompany
  isLast: boolean
  onView: () => void
}) {
  const getDaysRemainingText = () => {
    if (company.daysRemaining === null) return '무제한'
    if (company.daysRemaining === 0) return '오늘 만료'
    if (company.daysRemaining <= 3) return `D-${company.daysRemaining}`
    return `${company.daysRemaining}일 남음`
  }

  const getDaysRemainingColor = () => {
    if (company.daysRemaining === null) return colors.green500
    if (company.daysRemaining <= 3) return colors.red500
    if (company.daysRemaining <= 7) return colors.yellow500
    return colors.gray500
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return `${date.getMonth() + 1}/${date.getDate()}`
  }

  return (
    <div
      onClick={onView}
      style={{
        padding: '16px 20px',
        borderBottom: isLast ? 'none' : `1px solid ${colors.gray100}`,
        cursor: 'pointer',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <div style={{ flex: 1 }}>
        <div style={{
          fontSize: '16px',
          fontWeight: '600',
          color: colors.gray900,
          marginBottom: '4px',
        }}>
          {company.companyName || company.companyId}
        </div>
        <div style={{
          fontSize: '13px',
          color: colors.gray500,
        }}>
          조회일 {formatDate(company.lastViewedAt)} · {company.viewCount}회 조회
        </div>
      </div>

      <div style={{ textAlign: 'right' }}>
        <div style={{
          fontSize: '13px',
          fontWeight: '600',
          color: getDaysRemainingColor(),
          marginBottom: '4px',
        }}>
          {getDaysRemainingText()}
        </div>
        <div style={{
          fontSize: '12px',
          color: colors.gray500,
        }}>
          보기 →
        </div>
      </div>
    </div>
  )
}

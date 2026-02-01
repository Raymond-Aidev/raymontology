import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import apiClient from '../api/client'
import { colors } from '../constants/colors'
import { ListItem } from '../components'

// 백엔드 API 응답 타입
interface ApiCompanyDetail {
  id: string
  name: string
  ticker: string | null
  corp_code: string | null
  sector: string | null
  market: string | null
  cb_count: number
  officer_count: number
}

interface CompanyReport {
  name: string
  corp_code: string
  risk_score: number
  investment_grade: string
  cb_count: number
  officer_count: number
  market: string | null
  sector: string | null
}

// CB 발행 횟수 기반 리스크 점수 추정
function estimateRiskScore(cbCount: number): number {
  if (cbCount >= 10) return 85
  if (cbCount >= 7) return 70
  if (cbCount >= 5) return 55
  if (cbCount >= 3) return 40
  if (cbCount >= 1) return 25
  return 10
}

// CB 발행 횟수 기반 투자등급 추정 (4등급 체계 v2.1)
function estimateInvestmentGrade(cbCount: number): string {
  if (cbCount >= 5) return 'HIGH_RISK'      // 고위험
  if (cbCount >= 3) return 'MEDIUM_RISK'    // 중위험
  if (cbCount >= 1) return 'RISK'           // 위험
  return 'LOW_RISK'                          // 저위험
}

// 등급 라벨 변환
function getGradeLabel(grade: string): string {
  switch (grade) {
    case 'LOW_RISK': return '저위험'
    case 'RISK': return '위험'
    case 'MEDIUM_RISK': return '중위험'
    case 'HIGH_RISK': return '고위험'
    default: return grade
  }
}

// 등급 색상 반환
function getGradeColor(grade: string): string {
  switch (grade) {
    case 'LOW_RISK': return colors.green500
    case 'RISK': return colors.yellow500
    case 'MEDIUM_RISK': return colors.orange500
    case 'HIGH_RISK': return colors.red500
    default: return colors.gray500
  }
}

export default function ReportPage() {
  const { corpCode } = useParams<{ corpCode: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, isLoading: authLoading, credits } = useAuth()

  const [companyData, setCompanyData] = useState<CompanyReport | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 기업명 (URL에서 전달받거나 기본값)
  const companyName = location.state?.companyName || '기업'

  // 이용권 필요 여부 체크 (credits === -1은 무제한)
  const needsPaywall = !isAuthenticated || credits === 0

  // 회사 데이터 로드 (이용권 없어도 기본 정보는 로드)
  useEffect(() => {
    // 인증 로딩 중이면 대기
    if (authLoading) return

    if (!corpCode) {
      navigate('/', { replace: true })
      return
    }

    const loadCompanyData = async () => {
      setIsLoading(true)
      setError(null)

      try {
        // 1. 회사명으로 검색 (corp_code로는 검색 안 됨)
        const searchQuery = companyName !== '기업' ? companyName : corpCode
        const searchResponse = await apiClient.get<{
          total: number
          items: ApiCompanyDetail[]
        }>('/api/companies/search', {
          params: { q: searchQuery, limit: 50 },
        })

        // corp_code가 정확히 일치하는 회사 찾기
        let company = searchResponse.data.items.find(
          item => item.corp_code === corpCode
        )

        // corp_code 매칭 없으면 이름이 정확히 일치하는 것 찾기
        if (!company && companyName !== '기업') {
          company = searchResponse.data.items.find(
            item => item.name === companyName
          )
        }

        // 그래도 없으면 첫 번째 결과 사용
        if (!company && searchResponse.data.items.length > 0) {
          company = searchResponse.data.items[0]
        }

        if (!company) {
          // 검색 결과 없으면 전달받은 이름으로 더미 데이터 생성
          setCompanyData({
            name: companyName,
            corp_code: corpCode,
            risk_score: 25,
            investment_grade: 'LOW_RISK',
            cb_count: 0,
            officer_count: 0,
            market: null,
            sector: null,
          })
        } else {
          setCompanyData({
            name: company.name,
            corp_code: company.corp_code || corpCode,
            risk_score: estimateRiskScore(company.cb_count),
            investment_grade: estimateInvestmentGrade(company.cb_count),
            cb_count: company.cb_count,
            officer_count: company.officer_count,
            market: company.market,
            sector: company.sector,
          })
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : '알 수 없는 오류'
        setError(`데이터를 불러올 수 없습니다: ${errorMsg}`)
      } finally {
        setIsLoading(false)
      }
    }

    loadCompanyData()
  }, [corpCode, navigate, companyName, authLoading])

  // 로딩 중
  if (authLoading || isLoading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: colors.white,
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: `3px solid ${colors.gray100}`,
            borderTopColor: colors.blue500,
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px',
          }} />
          <p style={{ color: colors.gray500, fontSize: '14px' }}>리포트를 불러오는 중...</p>
          <style>{`
            @keyframes spin {
              to { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      </div>
    )
  }

  // 에러 발생
  if (error) {
    return (
      <div style={{
        minHeight: '100vh',
        backgroundColor: colors.gray50,
        padding: '20px',
      }}>
        {/* 헤더 */}
        <header style={{
          marginBottom: '20px',
        }}>
          <button
            onClick={() => navigate(-1)}
            style={{
              padding: '10px 16px',
              borderRadius: '8px',
              border: `1px solid ${colors.gray100}`,
              backgroundColor: colors.white,
              color: colors.gray900,
              fontSize: '14px',
              cursor: 'pointer',
            }}
          >
            ← 뒤로가기
          </button>
        </header>

        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '60px 20px',
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>⚠️</div>
          <h2 style={{
            fontSize: '18px',
            fontWeight: '600',
            color: colors.gray900,
            marginBottom: '8px',
          }}>
            오류가 발생했습니다
          </h2>
          <p style={{
            fontSize: '14px',
            color: colors.gray500,
            marginBottom: '24px',
            textAlign: 'center',
          }}>
            {error}
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '14px 24px',
              borderRadius: '12px',
              border: 'none',
              backgroundColor: colors.blue500,
              color: colors.white,
              fontSize: '16px',
              fontWeight: '600',
              cursor: 'pointer',
              marginBottom: '12px',
            }}
          >
            다시 시도
          </button>
        </div>
      </div>
    )
  }

  // 데이터 없음
  if (!companyData) {
    return null
  }

  // 4등급 체계 점수 기반 색상
  const getRiskColor = (score: number) => {
    if (score < 20) return colors.green500     // LOW_RISK
    if (score < 35) return colors.yellow500    // RISK
    if (score < 50) return colors.orange500    // MEDIUM_RISK
    return colors.red500                       // HIGH_RISK
  }

  // 4등급 체계 점수 기반 라벨
  const getRiskLabel = (score: number) => {
    if (score < 20) return '저위험'
    if (score < 35) return '위험'
    if (score < 50) return '중위험'
    return '고위험'
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: colors.gray50 }}>
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
          fontSize: '18px',
          fontWeight: '600',
          margin: 0,
          color: colors.gray900,
        }}>
          기업 리포트
        </h1>
      </header>

      <main style={{ padding: '16px 20px 32px' }} role="main">
        {/* 뒤로가기 버튼 */}
        <section style={{ marginBottom: '16px' }}>
          <button
            onClick={() => navigate(-1)}
            aria-label="이전 페이지로 돌아가기"
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
            ← 뒤로가기
          </button>
        </section>

        {/* 기업 정보 카드 */}
        <section
          style={{
            backgroundColor: colors.white,
            borderRadius: '16px',
            padding: '20px',
            marginBottom: '12px',
          }}
          aria-label="기업 정보"
        >
          <h2 style={{
            fontSize: '22px',
            fontWeight: '700',
            margin: '0 0 4px 0',
            color: colors.gray900,
            letterSpacing: '-0.02em'
          }}>
            {companyData.name}
          </h2>
          <p style={{
            fontSize: '14px',
            color: colors.gray500,
            margin: 0
          }}>
            {companyData.corp_code}
            {companyData.market && ` · ${companyData.market}`}
          </p>
        </section>

        {/* 이용권 필요 배너 */}
        {needsPaywall && (
          <section
            style={{
              backgroundColor: colors.blue500 + '10',
              borderRadius: '16px',
              padding: '20px',
              marginBottom: '12px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '32px', marginBottom: '12px' }}>🔒</div>
            <h3 style={{
              fontSize: '18px',
              fontWeight: '600',
              color: colors.gray900,
              margin: '0 0 8px 0',
            }}>
              상세 리포트 확인하기
            </h3>
            <p style={{
              fontSize: '14px',
              color: colors.gray600,
              margin: '0 0 16px 0',
            }}>
              {!isAuthenticated
                ? '로그인하고 이용권을 구매하면 상세 분석을 확인할 수 있어요'
                : '이용권을 구매하면 상세 분석을 확인할 수 있어요'}
            </p>
            <button
              onClick={() => navigate('/paywall', {
                state: { returnTo: location.pathname, companyName: companyData.name }
              })}
              style={{
                padding: '14px 28px',
                borderRadius: '12px',
                border: 'none',
                backgroundColor: colors.blue500,
                color: colors.white,
                fontSize: '16px',
                fontWeight: '600',
                cursor: 'pointer',
              }}
            >
              {!isAuthenticated ? '토스로 시작하기' : '이용권 구매하기'}
            </button>
          </section>
        )}

        {/* 리스크 점수 카드 */}
        <section
          style={{
            backgroundColor: colors.white,
            borderRadius: '16px',
            padding: '24px 20px',
            marginBottom: '12px',
            position: 'relative',
            overflow: 'hidden',
          }}
          aria-label="리스크 점수"
        >
          {/* 이용권 없으면 블러 처리 */}
          {needsPaywall && (
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(255,255,255,0.7)',
              backdropFilter: 'blur(4px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10,
            }}>
              <span style={{ fontSize: '24px' }}>🔒</span>
            </div>
          )}
          <div style={{
            fontSize: '14px',
            color: colors.gray500,
            marginBottom: '12px',
            fontWeight: '500'
          }}>
            종합 리스크 점수
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: '8px',
            marginBottom: '16px'
          }}>
            <span
              style={{
                fontSize: '48px',
                fontWeight: '700',
                color: needsPaywall ? colors.gray300 : getRiskColor(companyData.risk_score),
                letterSpacing: '-0.02em'
              }}
              aria-label={`리스크 점수 ${needsPaywall ? '?' : companyData.risk_score}점`}
            >
              {needsPaywall ? '??' : companyData.risk_score}
            </span>
            <span style={{
              fontSize: '16px',
              color: colors.gray500,
              fontWeight: '400'
            }}>
              / 100
            </span>
            <span
              style={{
                marginLeft: 'auto',
                padding: '6px 12px',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: '600',
                backgroundColor: needsPaywall ? colors.gray100 : getRiskColor(companyData.risk_score) + '20',
                color: needsPaywall ? colors.gray400 : getRiskColor(companyData.risk_score),
              }}
              aria-label={`위험 등급: ${needsPaywall ? '?' : getRiskLabel(companyData.risk_score)}`}
            >
              {needsPaywall ? '?' : getRiskLabel(companyData.risk_score)}
            </span>
          </div>
          {/* Progress Bar */}
          <div
            style={{
              height: '8px',
              backgroundColor: colors.gray100,
              borderRadius: '4px',
              overflow: 'hidden'
            }}
            role="progressbar"
            aria-valuenow={companyData.risk_score}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="리스크 점수 바"
          >
            <div style={{
              height: '100%',
              width: needsPaywall ? '50%' : `${companyData.risk_score}%`,
              backgroundColor: needsPaywall ? colors.gray200 : getRiskColor(companyData.risk_score),
              borderRadius: '4px',
              transition: 'width 0.3s ease'
            }} />
          </div>
        </section>

        {/* 통계 카드 그리드 - 이용권 없으면 블러 */}
        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '12px',
            marginBottom: '12px',
            position: 'relative',
          }}
          aria-label="기업 통계"
        >
          <article
            style={{
              backgroundColor: colors.white,
              padding: '20px 16px',
              borderRadius: '16px',
              position: 'relative',
              overflow: 'hidden',
            }}
            aria-label={`투자등급: ${companyData.investment_grade}`}
          >
            {needsPaywall && (
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(255,255,255,0.7)',
                backdropFilter: 'blur(4px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10,
              }}>
                <span style={{ fontSize: '18px' }}>🔒</span>
              </div>
            )}
            <div style={{
              fontSize: '13px',
              color: colors.gray500,
              marginBottom: '8px',
              fontWeight: '500'
            }}>
              관계형리스크 등급
            </div>
            <div style={{
              fontSize: '20px',
              fontWeight: '700',
              color: needsPaywall ? colors.gray300 : getGradeColor(companyData.investment_grade),
              letterSpacing: '-0.02em'
            }}>
              {needsPaywall ? '?' : getGradeLabel(companyData.investment_grade)}
            </div>
          </article>
          <article
            style={{
              backgroundColor: colors.white,
              padding: '20px 16px',
              borderRadius: '16px',
              position: 'relative',
              overflow: 'hidden',
            }}
            aria-label={`CB 발행: ${companyData.cb_count}회`}
          >
            {needsPaywall && (
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(255,255,255,0.7)',
                backdropFilter: 'blur(4px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10,
              }}>
                <span style={{ fontSize: '18px' }}>🔒</span>
              </div>
            )}
            <div style={{
              fontSize: '13px',
              color: colors.gray500,
              marginBottom: '8px',
              fontWeight: '500'
            }}>
              CB 발행
            </div>
            <div style={{
              fontSize: '28px',
              fontWeight: '700',
              color: needsPaywall ? colors.gray300 : (companyData.cb_count > 0 ? colors.red500 : colors.green500),
              letterSpacing: '-0.02em'
            }}>
              {needsPaywall ? '?' : `${companyData.cb_count}회`}
            </div>
          </article>
        </section>

        {/* 추가 정보 카드 - 이용권 없으면 블러 */}
        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '12px',
            marginBottom: '12px'
          }}
        >
          <article style={{
            backgroundColor: colors.white,
            padding: '20px 16px',
            borderRadius: '16px',
            position: 'relative',
            overflow: 'hidden',
          }}>
            {needsPaywall && (
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(255,255,255,0.7)',
                backdropFilter: 'blur(4px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10,
              }}>
                <span style={{ fontSize: '18px' }}>🔒</span>
              </div>
            )}
            <div style={{
              fontSize: '13px',
              color: colors.gray500,
              marginBottom: '8px',
              fontWeight: '500'
            }}>
              등기임원 수
            </div>
            <div style={{
              fontSize: '28px',
              fontWeight: '700',
              color: needsPaywall ? colors.gray300 : colors.blue500,
              letterSpacing: '-0.02em'
            }}>
              {needsPaywall ? '?' : `${companyData.officer_count}명`}
            </div>
          </article>
          <article style={{
            backgroundColor: colors.white,
            padding: '20px 16px',
            borderRadius: '16px',
          }}>
            <div style={{
              fontSize: '13px',
              color: colors.gray500,
              marginBottom: '8px',
              fontWeight: '500'
            }}>
              시장
            </div>
            <div style={{
              fontSize: '24px',
              fontWeight: '700',
              color: colors.gray900,
              letterSpacing: '-0.02em'
            }}>
              {companyData.market || '-'}
            </div>
          </article>
        </section>

        {/* 상세 정보 목록 */}
        <nav
          style={{
            backgroundColor: colors.white,
            borderRadius: '16px',
            overflow: 'hidden',
            position: 'relative',
          }}
          aria-label="상세 분석 메뉴"
        >
          {needsPaywall && (
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(255,255,255,0.7)',
              backdropFilter: 'blur(4px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10,
            }}>
              <span style={{ fontSize: '24px' }}>🔒</span>
            </div>
          )}
          <ListItem
            title="이해관계자 네트워크"
            description="임원, CB 투자자, 대주주 간의 연결 관계 분석"
            onClick={needsPaywall ? undefined : () => navigate(`/graph/${companyData.corp_code}`, {
              state: { companyName: companyData.name }
            })}
          />
          <ListItem
            title="리스크 신호"
            description={companyData.cb_count > 3 ? `CB ${companyData.cb_count}회 발행 - 주의 필요` : '탐지된 리스크 패턴이 없습니다'}
          />
          <ListItem
            title="재무제표"
            description="재무 데이터 분석 (준비중)"
            isLast
          />
        </nav>

        {/* 법적 면책 고지 */}
        <section
          style={{
            marginTop: '24px',
            padding: '16px',
            backgroundColor: colors.yellow500 + '10',
            borderRadius: '12px',
            border: `1px solid ${colors.yellow500}30`,
          }}
          aria-label="투자 유의사항"
        >
          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '16px', flexShrink: 0, marginTop: '2px' }}>⚠️</span>
            <div style={{ fontSize: '12px', color: colors.gray600, lineHeight: '1.6' }}>
              <p style={{ margin: '0 0 8px 0' }}>
                <strong style={{ color: colors.gray900 }}>투자 유의사항:</strong> 본 서비스에서 제공하는 정보는
                투자 권유나 추천이 아니며, 정보 제공 목적으로만 제공됩니다.
              </p>
              <p style={{ margin: '0 0 8px 0' }}>
                모든 투자 결정은 본인의 판단과 책임 하에 이루어져야 하며,
                본 서비스 이용으로 인한 투자 손실에 대해 당사는 책임지지 않습니다.
              </p>
              <p style={{ margin: 0, color: colors.gray500 }}>
                데이터 출처: 금융감독원 DART OpenAPI
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}

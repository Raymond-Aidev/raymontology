import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import apiClient from '../api/client'
import { colors } from '../constants/colors'
import { ListItem } from '../components'

// 디버그 로그 저장
const debugLogs: string[] = []
function debugLog(message: string) {
  const timestamp = new Date().toLocaleTimeString()
  const log = `[${timestamp}] ${message}`
  debugLogs.push(log)
  console.log(log)
  if (debugLogs.length > 100) debugLogs.shift()
}

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

// CB 발행 횟수 기반 투자등급 추정
function estimateInvestmentGrade(cbCount: number): string {
  if (cbCount >= 8) return 'CCC'
  if (cbCount >= 5) return 'B'
  if (cbCount >= 3) return 'BB'
  if (cbCount >= 1) return 'BBB'
  return 'A'
}

export default function ReportPage() {
  const { corpCode } = useParams<{ corpCode: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, isLoading: authLoading, credits } = useAuth()

  const [companyData, setCompanyData] = useState<CompanyReport | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showDebug, setShowDebug] = useState(false)
  const [, forceUpdate] = useState(0)

  // 기업명 (URL에서 전달받거나 기본값)
  const companyName = location.state?.companyName || '기업'

  // 인증 및 이용권 체크
  useEffect(() => {
    // 인증 로딩 중이면 대기
    if (authLoading) return

    // 미인증 시 Paywall로 리다이렉트
    if (!isAuthenticated) {
      debugLog(`미인증 - Paywall로 리다이렉트`)
      navigate('/paywall', {
        state: { returnTo: location.pathname, companyName },
        replace: true
      })
      return
    }

    // 이용권 없으면 Paywall로 리다이렉트 (credits === -1은 무제한)
    if (credits === 0) {
      debugLog(`이용권 없음 (${credits}건) - Paywall로 리다이렉트`)
      navigate('/paywall', {
        state: { returnTo: location.pathname, companyName },
        replace: true
      })
      return
    }
  }, [authLoading, isAuthenticated, credits, navigate, location.pathname, companyName])

  // 회사 데이터 로드
  useEffect(() => {
    // 인증 로딩 중이면 대기
    if (authLoading) return

    // 인증 및 이용권 체크 (위의 useEffect에서 리다이렉트 처리)
    // credits === -1은 무제한
    if (!isAuthenticated || credits === 0) return

    if (!corpCode) {
      navigate('/', { replace: true })
      return
    }

    const loadCompanyData = async () => {
      setIsLoading(true)
      setError(null)
      debugLog(`리포트 로딩 시작: corpCode=${corpCode}`)
      debugLog(`환경: DEV=${import.meta.env.DEV}, MODE=${import.meta.env.MODE}`)
      debugLog(`인증상태: isAuthenticated=${isAuthenticated}, credits=${credits}`)

      try {
        // 1. 회사명으로 검색 (corp_code로는 검색 안 됨)
        const searchQuery = companyName !== '기업' ? companyName : corpCode
        debugLog(`API 호출: /api/companies/search?q=${searchQuery}`)
        const searchResponse = await apiClient.get<{
          total: number
          items: ApiCompanyDetail[]
        }>('/api/companies/search', {
          params: { q: searchQuery, limit: 50 },
        })
        debugLog(`검색 결과: ${searchResponse.data.total}건`)

        // corp_code가 정확히 일치하는 회사 찾기
        let company = searchResponse.data.items.find(
          item => item.corp_code === corpCode
        )

        // corp_code 매칭 없으면 이름이 정확히 일치하는 것 찾기
        if (!company && companyName !== '기업') {
          company = searchResponse.data.items.find(
            item => item.name === companyName
          )
          if (company) {
            debugLog(`이름 매칭 성공: ${company.name}`)
          }
        }

        // 그래도 없으면 첫 번째 결과 사용
        if (!company && searchResponse.data.items.length > 0) {
          company = searchResponse.data.items[0]
          debugLog(`첫 번째 결과 사용: ${company.name}`)
        }

        if (!company) {
          // 검색 결과 없으면 전달받은 이름으로 더미 데이터 생성
          debugLog(`검색 결과 없음, 더미 데이터 생성`)
          setCompanyData({
            name: companyName,
            corp_code: corpCode,
            risk_score: 50,
            investment_grade: 'BB',
            cb_count: 0,
            officer_count: 0,
            market: null,
            sector: null,
          })
        } else {
          debugLog(`회사 데이터 로드 성공: ${company.name}`)
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
        debugLog(`API 에러: ${errorMsg}`)

        if (err && typeof err === 'object' && 'response' in err) {
          const axiosErr = err as { response?: { status?: number; data?: unknown } }
          debugLog(`HTTP Status: ${axiosErr.response?.status}`)
          debugLog(`Response: ${JSON.stringify(axiosErr.response?.data)}`)
        }

        setError(`데이터를 불러올 수 없습니다: ${errorMsg}`)
      } finally {
        setIsLoading(false)
        debugLog(`리포트 로딩 완료`)
      }
    }

    loadCompanyData()
  }, [corpCode, navigate, companyName, isAuthenticated, credits])

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

        {/* 디버그 패널 - 개발 환경에서만 표시 */}
        {import.meta.env.DEV && (
          <DebugPanel
            showDebug={showDebug}
            setShowDebug={setShowDebug}
            forceUpdate={forceUpdate}
            isAuthenticated={isAuthenticated}
            authLoading={authLoading}
            credits={credits}
            corpCode={corpCode}
          />
        )}
      </div>
    )
  }

  // 데이터 없음
  if (!companyData) {
    return null
  }

  const getRiskColor = (score: number) => {
    if (score <= 30) return colors.green500
    if (score <= 60) return colors.yellow500
    return colors.red500
  }

  const getRiskLabel = (score: number) => {
    if (score <= 30) return '안전'
    if (score <= 60) return '주의'
    return '위험'
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

        {/* 리스크 점수 카드 */}
        <section
          style={{
            backgroundColor: colors.white,
            borderRadius: '16px',
            padding: '24px 20px',
            marginBottom: '12px',
          }}
          aria-label="리스크 점수"
        >
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
                color: getRiskColor(companyData.risk_score),
                letterSpacing: '-0.02em'
              }}
              aria-label={`리스크 점수 ${companyData.risk_score}점`}
            >
              {companyData.risk_score}
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
                backgroundColor: getRiskColor(companyData.risk_score) + '20',
                color: getRiskColor(companyData.risk_score),
              }}
              aria-label={`위험 등급: ${getRiskLabel(companyData.risk_score)}`}
            >
              {getRiskLabel(companyData.risk_score)}
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
              width: `${companyData.risk_score}%`,
              backgroundColor: getRiskColor(companyData.risk_score),
              borderRadius: '4px',
              transition: 'width 0.3s ease'
            }} />
          </div>
        </section>

        {/* 통계 카드 그리드 */}
        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '12px',
            marginBottom: '12px'
          }}
          aria-label="기업 통계"
        >
          <article
            style={{
              backgroundColor: colors.white,
              padding: '20px 16px',
              borderRadius: '16px',
            }}
            aria-label={`투자등급: ${companyData.investment_grade}`}
          >
            <div style={{
              fontSize: '13px',
              color: colors.gray500,
              marginBottom: '8px',
              fontWeight: '500'
            }}>
              투자등급
            </div>
            <div style={{
              fontSize: '28px',
              fontWeight: '700',
              color: colors.yellow500,
              letterSpacing: '-0.02em'
            }}>
              {companyData.investment_grade}
            </div>
          </article>
          <article
            style={{
              backgroundColor: colors.white,
              padding: '20px 16px',
              borderRadius: '16px',
            }}
            aria-label={`CB 발행: ${companyData.cb_count}회`}
          >
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
              color: companyData.cb_count > 0 ? colors.red500 : colors.green500,
              letterSpacing: '-0.02em'
            }}>
              {companyData.cb_count}회
            </div>
          </article>
        </section>

        {/* 추가 정보 카드 */}
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
          }}>
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
              color: colors.blue500,
              letterSpacing: '-0.02em'
            }}>
              {companyData.officer_count}명
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
          }}
          aria-label="상세 분석 메뉴"
        >
          <ListItem
            title="이해관계자 네트워크"
            description="임원, CB 투자자, 대주주 간의 연결 관계 분석"
            onClick={() => navigate(`/graph/${companyData.corp_code}`, {
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

        {/* 디버그 패널 - 개발 환경에서만 표시 */}
        {import.meta.env.DEV && (
          <DebugPanel
            showDebug={showDebug}
            setShowDebug={setShowDebug}
            forceUpdate={forceUpdate}
            isAuthenticated={isAuthenticated}
            authLoading={authLoading}
            credits={credits}
            corpCode={corpCode}
          />
        )}
      </main>
    </div>
  )
}

// 디버그 패널 컴포넌트
function DebugPanel({
  showDebug,
  setShowDebug,
  forceUpdate,
  isAuthenticated,
  authLoading,
  credits,
  corpCode,
}: {
  showDebug: boolean
  setShowDebug: (v: boolean) => void
  forceUpdate: React.Dispatch<React.SetStateAction<number>>
  isAuthenticated: boolean
  authLoading: boolean
  credits: number
  corpCode?: string
}) {
  return (
    <div style={{ marginTop: '24px' }}>
      {/* 디버그 토글 버튼 */}
      <div style={{ textAlign: 'center', marginBottom: '12px' }}>
        <button
          onClick={() => {
            setShowDebug(!showDebug)
            forceUpdate(n => n + 1)
          }}
          style={{
            padding: '8px 16px',
            fontSize: '12px',
            backgroundColor: colors.gray100,
            border: 'none',
            borderRadius: '8px',
            color: colors.gray600,
            cursor: 'pointer',
          }}
        >
          {showDebug ? '디버그 숨기기' : '디버그 보기'}
        </button>
      </div>

      {/* 디버그 로그 패널 */}
      {showDebug && (
        <div style={{
          padding: '12px',
          backgroundColor: '#1a1a2e',
          borderRadius: '8px',
          maxHeight: '400px',
          overflowY: 'auto',
        }}>
          <div style={{
            fontFamily: 'monospace',
            fontSize: '11px',
            color: '#00ff00',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
          }}>
            <div style={{ marginBottom: '8px', color: '#ffff00' }}>
              === 환경 정보 ===
            </div>
            <div>DEV: {String(import.meta.env.DEV)}</div>
            <div>MODE: {import.meta.env.MODE}</div>
            <div>PROD: {String(import.meta.env.PROD)}</div>
            <div>API_URL: {import.meta.env.VITE_API_URL || '(default)'}</div>
            <div>corpCode: {corpCode || 'null'}</div>
            <div style={{ marginTop: '8px', marginBottom: '8px', color: '#ffff00' }}>
              === 인증 상태 ===
            </div>
            <div>isAuthenticated: {String(isAuthenticated)}</div>
            <div>authLoading: {String(authLoading)}</div>
            <div>credits: {credits}</div>
            <div style={{ marginTop: '8px', marginBottom: '8px', color: '#ffff00' }}>
              === 디버그 로그 ===
            </div>
            {debugLogs.length === 0 ? (
              <div style={{ color: '#888' }}>(로그 없음)</div>
            ) : (
              debugLogs.map((log, i) => (
                <div key={i} style={{ marginBottom: '2px' }}>{log}</div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

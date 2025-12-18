import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { RiskGauge, ScoreBreakdown, GradeCard, DataTabs, RiskSignalList } from '../components/report'
import { getCompanyReport, type CompanyReportData } from '../api/report'

function ReportPage() {
  const { companyId } = useParams<{ companyId: string }>()
  const [reportData, setReportData] = useState<CompanyReportData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isApiConnected, setIsApiConnected] = useState<boolean | null>(null)

  // 보고서 데이터 로드
  useEffect(() => {
    const loadReportData = async () => {
      if (!companyId) return

      setIsLoading(true)
      setError(null)

      try {
        const data = await getCompanyReport(companyId)
        setReportData(data)
        // API 연결 여부 판단 (더미 데이터가 아닌 경우)
        setIsApiConnected(data.calculatedAt !== new Date().toISOString().slice(0, 10))
      } catch (err) {
        setError('보고서 데이터를 불러오는데 실패했습니다')
        setIsApiConnected(false)
      } finally {
        setIsLoading(false)
      }
    }

    loadReportData()
  }, [companyId])

  const handleRetry = useCallback(() => {
    if (!companyId) return
    setIsLoading(true)
    setError(null)
    getCompanyReport(companyId)
      .then(data => {
        setReportData(data)
        setIsApiConnected(true)
      })
      .catch(() => {
        setError('보고서 데이터를 불러오는데 실패했습니다')
        setIsApiConnected(false)
      })
      .finally(() => setIsLoading(false))
  }, [companyId])

  // 로딩 상태
  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-accent-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-text-secondary">보고서 로딩 중...</p>
        </div>
      </div>
    )
  }

  // 에러 상태
  if (error) {
    return (
      <div className="max-w-6xl mx-auto flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3 text-center">
          <svg className="w-12 h-12 text-accent-danger" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-text-secondary">{error}</p>
          <button
            onClick={handleRetry}
            className="px-4 py-2 bg-accent-primary text-white rounded-lg hover:bg-accent-primary/80"
          >
            다시 시도
          </button>
        </div>
      </div>
    )
  }

  // 데이터 없음
  if (!reportData) {
    return (
      <div className="max-w-6xl mx-auto flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3 text-center">
          <svg className="w-12 h-12 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-text-muted">보고서 데이터가 없습니다</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* API 연결 상태 배너 */}
      {isApiConnected === false && !isLoading && (
        <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-center gap-2 text-amber-400">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="text-sm">API 연결 실패 - 더미 데이터를 표시합니다</span>
        </div>
      )}

      {/* 상단 네비게이션 */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/" className="text-accent-primary hover:underline flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            검색으로
          </Link>
          <span className="text-dark-border">|</span>
          <Link
            to={`/company/${companyId}/graph`}
            className="text-accent-primary hover:underline flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            관계도 보기
          </Link>
        </div>
      </div>

      {/* 타이틀 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary">{reportData.companyName}</h1>
        <p className="text-text-secondary mt-1">RaymondsRisk 분석보고서</p>
      </div>

      {/* 리스크 대시보드 */}
      <div className="bg-dark-card border border-dark-border rounded-xl shadow-card p-6 mb-6">
        <h2 className="text-lg font-bold text-text-primary mb-6">리스크 대시보드</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* 종합 리스크 게이지 */}
          <div className="flex justify-center">
            <RiskGauge score={reportData.riskScore.total} size={220} />
          </div>

          {/* 투자등급 */}
          <div className="flex justify-center">
            <GradeCard grade={reportData.investmentGrade} />
          </div>

          {/* 점수 구성 */}
          <div>
            <ScoreBreakdown scores={reportData.riskScore} />
          </div>
        </div>

        {/* 경고 요약 */}
        {reportData.warnings.length > 0 && (
          <div className="mt-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
            <div className="flex items-start gap-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <h3 className="font-semibold text-amber-400">주의 필요</h3>
                <ul className="text-sm text-amber-300 mt-1 list-disc list-inside">
                  {reportData.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 리스크 신호 목록 */}
      <div className="bg-dark-card border border-dark-border rounded-xl shadow-card p-6 mb-6">
        <h2 className="text-lg font-bold text-text-primary mb-4">리스크 신호 탐지</h2>
        <RiskSignalList signals={reportData.riskSignals} />
      </div>

      {/* 데이터 탭 */}
      <div className="bg-dark-card border border-dark-border rounded-xl shadow-card p-6">
        <h2 className="text-lg font-bold text-text-primary mb-6">세부 데이터</h2>
        <DataTabs
          cbIssuances={reportData.cbIssuances}
          cbSubscribers={reportData.cbSubscribers}
          officers={reportData.officers}
          financials={reportData.financials}
          shareholders={reportData.shareholders}
          affiliates={reportData.affiliates}
        />
      </div>

      {/* 면책조항 */}
      <div className="mt-6 p-4 bg-dark-surface border border-dark-border rounded-lg text-xs text-text-muted">
        <p className="font-semibold mb-1 text-text-secondary">면책조항</p>
        <p>
          본 보고서는 금융감독원 DART 공시 데이터를 기반으로 자동 생성되었으며, 투자 권유를 목적으로 하지 않습니다.
          투자 결정 시 반드시 전문가와 상담하시기 바랍니다. 데이터의 정확성을 보장하지 않으며,
          본 보고서로 인한 손실에 대해 책임을 지지 않습니다.
        </p>
        {reportData.calculatedAt && (
          <p className="mt-2 text-text-tertiary">
            분석 시점: {new Date(reportData.calculatedAt).toLocaleString('ko-KR')}
          </p>
        )}
      </div>
    </div>
  )
}

export default ReportPage

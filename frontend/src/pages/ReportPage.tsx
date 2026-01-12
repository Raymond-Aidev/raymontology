import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { RiskGauge, ScoreBreakdown, GradeCard, DataTabs, RiskSignalList, StockPriceCard, RaymondsIndexMiniCard } from '../components/report'
import { getCompanyReport, type CompanyReportData } from '../api/report'
import { getRaymondsIndexByName } from '../api/raymondsIndex'
import type { RaymondsIndexData } from '../types/raymondsIndex'
import { RaymondsIndexCard, SubIndexRadar, InvestmentGapMeter, RiskFlagsPanel } from '../components/RaymondsIndex'
import { MarketBadge } from '../components/common'

function ReportPage() {
  const { companyId } = useParams<{ companyId: string }>()
  const [reportData, setReportData] = useState<CompanyReportData | null>(null)
  const [raymondsIndex, setRaymondsIndex] = useState<RaymondsIndexData | null>(null)
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

        // RaymondsIndex 데이터 로드 (별도로 - 실패해도 보고서는 표시)
        if (data.companyName) {
          try {
            const indexData = await getRaymondsIndexByName(data.companyName)
            setRaymondsIndex(indexData)
          } catch {
            // RaymondsIndex 로드 실패는 무시 (Optional 데이터)
            console.log('RaymondsIndex 데이터 없음')
          }
        }
      } catch (err) {
        setError('보고서 데이터를 불러오는데 실패했습니다')
        setIsApiConnected(false)
      } finally {
        setIsLoading(false)
      }
    }

    loadReportData()
  }, [companyId])

  const handleRetry = useCallback(async () => {
    if (!companyId) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await getCompanyReport(companyId)
      setReportData(data)
      setIsApiConnected(true)

      // RaymondsIndex도 다시 로드
      if (data.companyName) {
        try {
          const indexData = await getRaymondsIndexByName(data.companyName)
          setRaymondsIndex(indexData)
        } catch {
          // 무시
        }
      }
    } catch {
      setError('보고서 데이터를 불러오는데 실패했습니다')
      setIsApiConnected(false)
    } finally {
      setIsLoading(false)
    }
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
      {/* API 연결 상태 배너 - 모바일에서 숨김 */}
      {isApiConnected === false && !isLoading && (
        <div className="hidden md:flex mb-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg items-center gap-2 text-amber-400">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="text-sm">API 연결 실패 - 더미 데이터를 표시합니다</span>
        </div>
      )}

      {/* 상단 네비게이션 - 모바일 최적화 */}
      <div className="mb-4 md:mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2 md:gap-4">
          <Link to="/" className="text-accent-primary hover:underline flex items-center gap-1 p-1.5 md:p-0">
            <svg className="w-5 h-5 md:w-4 md:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            <span className="hidden md:inline">검색으로</span>
          </Link>
          <span className="hidden md:inline text-dark-border">|</span>
          <Link
            to={`/company/${companyId}/graph`}
            className="text-accent-primary hover:underline flex items-center gap-1 p-1.5 md:p-0"
          >
            <svg className="w-5 h-5 md:w-4 md:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span className="hidden md:inline">관계도 보기</span>
          </Link>
        </div>
      </div>

      {/* 타이틀 - 모바일 최적화 */}
      <div className="mb-4 md:mb-8">
        <div className="flex items-center gap-3">
          <h1 className="text-xl md:text-3xl font-bold text-text-primary truncate">{reportData.companyName}</h1>
          {reportData.market && (
            <MarketBadge
              market={reportData.market}
              tradingStatus={reportData.tradingStatus}
              size="md"
            />
          )}
        </div>
        <p className="text-sm md:text-base text-text-secondary mt-1">RaymondsRisk 분석보고서</p>
      </div>

      {/* 관계형 리스크 대시보드 - 모바일 최적화 */}
      <div className="bg-dark-card border border-dark-border rounded-xl shadow-card p-4 md:p-6 mb-4 md:mb-6">
        <h2 className="text-base md:text-lg font-bold text-text-primary mb-4 md:mb-6">관계형 리스크 대시보드</h2>

        {/* 5개 박스 그리드: 종합리스크, 관계형리스크등급, RaymondsIndex, 주가차트, 구성요소 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 md:gap-4">
          {/* 1. 종합 리스크 게이지 */}
          <div className="flex justify-center items-center">
            <div className="md:hidden">
              <RiskGauge score={reportData.riskScore.total} size={140} />
            </div>
            <div className="hidden md:block">
              <RiskGauge score={reportData.riskScore.total} size={160} />
            </div>
          </div>

          {/* 2. 관계형 리스크 등급 */}
          <div className="flex justify-center items-center">
            <GradeCard grade={reportData.investmentGrade} />
          </div>

          {/* 3. RaymondsIndex (데이터 있을 때만 표시) */}
          <div className="flex justify-center items-center">
            {raymondsIndex ? (
              <RaymondsIndexMiniCard
                score={raymondsIndex.totalScore}
                grade={raymondsIndex.grade}
              />
            ) : (
              <div className="flex flex-col items-center justify-center p-6 bg-dark-surface rounded-xl border border-dark-border text-center h-full min-h-[160px]">
                <span className="text-sm text-text-secondary mb-2">RaymondsIndex</span>
                <span className="text-text-muted text-sm">데이터 없음</span>
              </div>
            )}
          </div>

          {/* 4. 최근 1년 주가 차트 */}
          <div className="flex justify-center items-center">
            {companyId && (
              <div className="bg-dark-surface/50 rounded-xl border border-dark-border/50 w-full h-full">
                <StockPriceCard companyId={companyId} companyName={reportData.companyName} />
              </div>
            )}
          </div>

          {/* 5. 관계형 리스크 구성 요소 */}
          <div className="flex justify-center items-center">
            <ScoreBreakdown scores={reportData.riskScore} />
          </div>
        </div>

        {/* 경고 요약 */}
        {reportData.warnings.length > 0 && (
          <div className="mt-4 md:mt-6 p-3 md:p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
            <div className="flex items-start gap-2 md:gap-3">
              <span className="text-xl md:text-2xl">⚠️</span>
              <div>
                <h3 className="font-semibold text-amber-400 text-sm md:text-base">주의 필요</h3>
                <ul className="text-xs md:text-sm text-amber-300 mt-1 list-disc list-inside">
                  {reportData.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 리스크 신호 목록 - 모바일 최적화 */}
      <div className="bg-dark-card border border-dark-border rounded-xl shadow-card p-4 md:p-6 mb-4 md:mb-6">
        <h2 className="text-base md:text-lg font-bold text-text-primary mb-3 md:mb-4">리스크 신호 탐지</h2>
        <RiskSignalList signals={reportData.riskSignals} />
      </div>

      {/* RaymondsIndex 섹션 - 데이터가 있을 때만 표시 */}
      {raymondsIndex && (
        <div className="bg-dark-card border border-dark-border rounded-xl shadow-card p-4 md:p-6 mb-4 md:mb-6">
          <div className="flex items-center justify-between mb-4 md:mb-6">
            <h2 className="text-base md:text-lg font-bold text-text-primary">
              자본 배분 효율성 (RaymondsIndex)
            </h2>
            <span className="text-xs md:text-sm text-text-secondary">
              {raymondsIndex.fiscalYear}년 기준
            </span>
          </div>

          {/* 메인 그리드 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 mb-4 md:mb-6">
            {/* 점수 카드 */}
            <RaymondsIndexCard
              score={raymondsIndex.totalScore}
              grade={raymondsIndex.grade}
              investmentGap={raymondsIndex.coreMetrics.investmentGap}
              redFlags={raymondsIndex.redFlags}
              yellowFlags={raymondsIndex.yellowFlags}
              fiscalYear={raymondsIndex.fiscalYear}
            />

            {/* Sub-Index 레이더 */}
            <SubIndexRadar
              cei={raymondsIndex.subIndexScores.cei}
              rii={raymondsIndex.subIndexScores.rii}
              cgi={raymondsIndex.subIndexScores.cgi}
              mai={raymondsIndex.subIndexScores.mai}
            />
          </div>

          {/* 투자괴리율 게이지 */}
          <div className="mb-4 md:mb-6">
            <InvestmentGapMeter
              gap={raymondsIndex.coreMetrics.investmentGap}
              cashGrowth={raymondsIndex.coreMetrics.cashCagr}
              capexGrowth={raymondsIndex.coreMetrics.capexGrowth}
            />
          </div>

          {/* 리스크 분석 패널 */}
          <RiskFlagsPanel
            redFlags={raymondsIndex.redFlags}
            yellowFlags={raymondsIndex.yellowFlags}
            verdict={raymondsIndex.verdict}
            keyRisk={raymondsIndex.keyRisk}
            recommendation={raymondsIndex.recommendation}
          />
        </div>
      )}

      {/* 데이터 탭 - 모바일 최적화 */}
      <div className="bg-dark-card border border-dark-border rounded-xl shadow-card p-4 md:p-6">
        <h2 className="text-base md:text-lg font-bold text-text-primary mb-4 md:mb-6">세부 데이터</h2>
        <DataTabs
          cbIssuances={reportData.cbIssuances}
          cbSubscribers={reportData.cbSubscribers}
          officers={reportData.officers}
          financials={reportData.financials}
          shareholders={reportData.shareholders}
          affiliates={reportData.affiliates}
        />
      </div>

      {/* 면책조항 - 모바일 최적화 */}
      <div className="mt-4 md:mt-6 p-3 md:p-4 bg-dark-surface border border-dark-border rounded-lg text-[10px] md:text-xs text-text-muted">
        <p className="font-semibold mb-1 text-text-secondary">면책조항</p>
        <p className="leading-relaxed">
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

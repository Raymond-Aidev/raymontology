/**
 * RaymondsIndex 타입 정의
 *
 * 자본 배분 효율성 지수 관련 타입
 */

// ============================================================================
// 기본 타입
// ============================================================================

/** RaymondsIndex 등급 */
export type RaymondsIndexGrade = 'A+' | 'A' | 'B' | 'C' | 'D'

/** Sub-Index 점수 */
export interface SubIndexScores {
  /** Capital Efficiency Index (자본효율성 지수) - 20% */
  cei: number
  /** Reinvestment Intensity Index (재투자 강도 지수) - 35% ⭐ 핵심 */
  rii: number
  /** Cash Governance Index (현금 거버넌스 지수) - 25% */
  cgi: number
  /** Momentum Alignment Index (모멘텀 정렬 지수) - 20% */
  mai: number
}

/** 핵심 지표 */
export interface CoreMetrics {
  /** 투자괴리율 (%) = Cash CAGR - CAPEX Growth */
  investmentGap: number
  /** 현금 증가율 CAGR (%) */
  cashCagr: number
  /** CAPEX 증가율 (%) */
  capexGrowth: number
  /** 유휴현금비율 (%) */
  idleCashRatio: number
  /** 자산회전율 (회) */
  assetTurnover: number
  /** 재투자율 (%) */
  reinvestmentRate: number
  /** 주주환원율 (%) */
  shareholderReturn: number
}

/** 위험 신호 */
export interface RiskFlag {
  code: string
  message: string
  severity: 'red' | 'yellow'
}

// ============================================================================
// API 응답 타입
// ============================================================================

/** API 응답: RaymondsIndex */
export interface ApiRaymondsIndex {
  id: string
  company_id: string
  company_name?: string
  company_ticker?: string
  company_market?: string
  fiscal_year: number
  calculation_date: string | null
  total_score: number
  grade: RaymondsIndexGrade

  // Sub-Index
  cei_score: number | null
  rii_score: number | null
  cgi_score: number | null
  mai_score: number | null

  // Core Metrics
  investment_gap: number | null
  cash_cagr: number | null
  capex_growth: number | null
  idle_cash_ratio: number | null
  asset_turnover: number | null
  reinvestment_rate: number | null
  shareholder_return: number | null

  // Flags
  red_flags: string[]
  yellow_flags: string[]

  // Interpretation
  verdict: string | null
  key_risk: string | null
  recommendation: string | null
  watch_trigger: string | null

  // Metadata
  data_quality_score: number | null
  rank?: number
}

/** API 응답: 랭킹 목록 */
export interface ApiRaymondsIndexRanking {
  total: number
  offset: number
  limit: number
  rankings: ApiRaymondsIndex[]
}

/** API 응답: 히스토리 */
export interface ApiRaymondsIndexHistory {
  company_id: string
  company_name: string
  history: ApiRaymondsIndex[]
}

/** API 응답: 통계 */
export interface ApiRaymondsIndexStatistics {
  total_companies: number
  average_score: number
  min_score: number
  max_score: number
  average_investment_gap: number
  grade_distribution: Record<RaymondsIndexGrade, number>
  year: number | null
}

// ============================================================================
// 프론트엔드 타입
// ============================================================================

/** 프론트엔드용 RaymondsIndex */
export interface RaymondsIndexData {
  id: string
  companyId: string
  companyName?: string
  companyTicker?: string
  companyMarket?: string
  fiscalYear: number
  calculationDate: string | null

  // 종합
  totalScore: number
  grade: RaymondsIndexGrade

  // Sub-Index
  subIndexScores: SubIndexScores

  // Core Metrics
  coreMetrics: CoreMetrics

  // Flags
  redFlags: string[]
  yellowFlags: string[]

  // Interpretation
  verdict: string | null
  keyRisk: string | null
  recommendation: string | null
  watchTrigger: string | null

  // Metadata
  dataQualityScore: number | null
  rank?: number
}

// ============================================================================
// 유틸리티 함수
// ============================================================================

/** API 응답을 프론트엔드 타입으로 변환 */
export function mapApiToRaymondsIndex(api: ApiRaymondsIndex): RaymondsIndexData {
  return {
    id: api.id,
    companyId: api.company_id,
    companyName: api.company_name,
    companyTicker: api.company_ticker,
    companyMarket: api.company_market,
    fiscalYear: api.fiscal_year,
    calculationDate: api.calculation_date,
    totalScore: api.total_score,
    grade: api.grade,
    subIndexScores: {
      cei: api.cei_score ?? 0,
      rii: api.rii_score ?? 0,
      cgi: api.cgi_score ?? 0,
      mai: api.mai_score ?? 0,
    },
    coreMetrics: {
      investmentGap: api.investment_gap ?? 0,
      cashCagr: api.cash_cagr ?? 0,
      capexGrowth: api.capex_growth ?? 0,
      idleCashRatio: api.idle_cash_ratio ?? 0,
      assetTurnover: api.asset_turnover ?? 0,
      reinvestmentRate: api.reinvestment_rate ?? 0,
      shareholderReturn: api.shareholder_return ?? 0,
    },
    redFlags: api.red_flags || [],
    yellowFlags: api.yellow_flags || [],
    verdict: api.verdict,
    keyRisk: api.key_risk,
    recommendation: api.recommendation,
    watchTrigger: api.watch_trigger,
    dataQualityScore: api.data_quality_score,
    rank: api.rank,
  }
}

/** 등급별 색상 */
export function getGradeColor(grade: RaymondsIndexGrade): string {
  const colors: Record<RaymondsIndexGrade, string> = {
    'A+': '#22c55e', // green-500
    'A': '#84cc16',  // lime-500
    'B': '#eab308',  // yellow-500
    'C': '#f97316',  // orange-500
    'D': '#ef4444',  // red-500
  }
  return colors[grade] || '#6b7280'
}

/** 등급별 배경색 */
export function getGradeBgColor(grade: RaymondsIndexGrade): string {
  const colors: Record<RaymondsIndexGrade, string> = {
    'A+': 'bg-green-100 text-green-800',
    'A': 'bg-lime-100 text-lime-800',
    'B': 'bg-yellow-100 text-yellow-800',
    'C': 'bg-orange-100 text-orange-800',
    'D': 'bg-red-100 text-red-800',
  }
  return colors[grade] || 'bg-gray-100 text-gray-800'
}

// ============================================================================
// 랭킹 페이지용 타입
// ============================================================================

/** 랭킹 페이지 아이템 */
export interface RaymondsIndexRankingItem {
  company_id: string
  company_name: string
  stock_code?: string
  market?: string
  total_score: number
  grade: RaymondsIndexGrade
  investment_gap: number
  cei_score?: number
  rii_score?: number
  cgi_score?: number
  mai_score?: number
  fiscal_year: number
}

/** 통계 타입 (랭킹 페이지용) */
export interface RaymondsIndexStatistics {
  total_companies: number
  average_score: number
  min_score?: number
  max_score?: number
  average_investment_gap: number
  grade_distribution: Record<string, number>
  year?: number
}

/** 투자괴리율 해석 */
export function getInvestmentGapInterpretation(gap: number): {
  status: 'good' | 'warning' | 'danger'
  message: string
} {
  if (gap >= -5 && gap <= 5) {
    return { status: 'good', message: '균형 잡힌 자본 배분' }
  } else if (gap > 5 && gap <= 15) {
    return { status: 'warning', message: '현금 축적 경향' }
  } else if (gap > 15) {
    return { status: 'danger', message: '과다 현금 축적 - 투자 부족' }
  } else if (gap < -5 && gap >= -15) {
    return { status: 'warning', message: '적극적 투자 중' }
  } else {
    return { status: 'danger', message: '과잉 투자 - 현금 고갈 위험' }
  }
}

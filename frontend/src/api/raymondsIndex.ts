/**
 * RaymondsIndex API 클라이언트
 */
import apiClient from './client'
import type {
  ApiRaymondsIndex,
  ApiRaymondsIndexRanking,
  ApiRaymondsIndexHistory,
  ApiRaymondsIndexStatistics,
  RaymondsIndexData,
  RaymondsIndexGrade,
  RaymondsIndexRankingItem,
  RaymondsIndexStatistics,
} from '../types/raymondsIndex'

// Re-export types for convenience
export type { RaymondsIndexRankingItem, RaymondsIndexStatistics }

// ============================================================================
// API 함수
// ============================================================================

/**
 * 회사명으로 RaymondsIndex 조회
 * ReportPage에서 사용
 */
export async function getRaymondsIndexByName(
  companyName: string
): Promise<RaymondsIndexData | null> {
  try {
    const response = await apiClient.get<ApiRaymondsIndex | null>(
      `/api/raymonds-index/company/name/${encodeURIComponent(companyName)}`
    )

    if (!response.data) {
      return null
    }

    return mapApiToRaymondsIndexData(response.data)
  } catch (error) {
    console.warn('RaymondsIndex API 호출 실패:', error)
    return null
  }
}

/**
 * 회사 ID로 RaymondsIndex 조회
 */
export async function getRaymondsIndexById(
  companyId: string,
  year?: number
): Promise<RaymondsIndexData | null> {
  try {
    const params = year ? { year } : {}
    const response = await apiClient.get<ApiRaymondsIndex>(
      `/api/raymonds-index/${companyId}`,
      { params }
    )

    return mapApiToRaymondsIndexData(response.data)
  } catch (error) {
    console.warn('RaymondsIndex API 호출 실패:', error)
    return null
  }
}

/**
 * 회사의 RaymondsIndex 히스토리 조회
 */
export async function getRaymondsIndexHistory(
  companyId: string
): Promise<{ companyName: string; history: RaymondsIndexData[] } | null> {
  try {
    const response = await apiClient.get<ApiRaymondsIndexHistory>(
      `/api/raymonds-index/${companyId}/history`
    )

    return {
      companyName: response.data.company_name,
      history: response.data.history.map(mapApiToRaymondsIndexData),
    }
  } catch (error) {
    console.warn('RaymondsIndex 히스토리 조회 실패:', error)
    return null
  }
}

/**
 * RaymondsIndex 검색
 */
export interface SearchParams {
  minScore?: number
  maxScore?: number
  minGap?: number
  maxGap?: number
  hasRedFlags?: boolean
  grade?: RaymondsIndexGrade[]
  market?: string[]
  year?: number
  limit?: number
  offset?: number
}

export async function searchRaymondsIndex(
  params: SearchParams = {}
): Promise<RaymondsIndexData[]> {
  try {
    const queryParams: Record<string, string | number | boolean> = {}

    if (params.minScore !== undefined) queryParams.min_score = params.minScore
    if (params.maxScore !== undefined) queryParams.max_score = params.maxScore
    if (params.minGap !== undefined) queryParams.min_gap = params.minGap
    if (params.maxGap !== undefined) queryParams.max_gap = params.maxGap
    if (params.hasRedFlags !== undefined) queryParams.has_red_flags = params.hasRedFlags
    if (params.grade?.length) queryParams.grade = params.grade.join(',')
    if (params.market?.length) queryParams.market = params.market.join(',')
    if (params.year) queryParams.year = params.year
    if (params.limit) queryParams.limit = params.limit
    if (params.offset) queryParams.offset = params.offset

    const response = await apiClient.get<{ results: ApiRaymondsIndex[] }>(
      '/api/raymonds-index/search/filter',
      { params: queryParams }
    )

    return response.data.results.map(mapApiToRaymondsIndexData)
  } catch (error) {
    console.warn('RaymondsIndex 검색 실패:', error)
    return []
  }
}

/**
 * RaymondsIndex 통계 조회
 */
export async function getRaymondsIndexStatistics(
  year?: number
): Promise<RaymondsIndexStatistics | null> {
  try {
    const params = year ? { year } : {}
    const response = await apiClient.get<ApiRaymondsIndexStatistics>(
      '/api/raymonds-index/statistics/summary',
      { params }
    )

    // API 응답을 프론트엔드 타입으로 변환
    return {
      total_companies: response.data.total_companies,
      average_score: response.data.average_score,
      min_score: response.data.min_score,
      max_score: response.data.max_score,
      average_investment_gap: response.data.average_investment_gap,
      grade_distribution: response.data.grade_distribution,
      year: response.data.year ?? undefined
    }
  } catch (error) {
    console.warn('RaymondsIndex 통계 조회 실패:', error)
    return null
  }
}

// ============================================================================
// 랭킹 페이지용 함수
// ============================================================================

interface RankingPageParams {
  sort?: 'score_desc' | 'score_asc' | 'gap_asc' | 'gap_desc'
  grades?: string[]
  limit?: number
}

/**
 * 랭킹 페이지용 간소화된 랭킹 조회
 */
export async function getRaymondsIndexRanking(
  params: RankingPageParams = {}
): Promise<RaymondsIndexRankingItem[]> {
  try {
    const queryParams: Record<string, string | number> = {}

    if (params.sort) queryParams.sort = params.sort
    if (params.grades?.length) queryParams.grade = params.grades.join(',')
    if (params.limit) queryParams.limit = params.limit

    const response = await apiClient.get<ApiRaymondsIndexRanking>(
      '/api/raymonds-index/ranking/list',
      { params: queryParams }
    )

    // API 응답을 랭킹 아이템으로 변환
    return response.data.rankings.map((item: ApiRaymondsIndex): RaymondsIndexRankingItem => ({
      company_id: item.company_id,
      company_name: item.company_name || '',
      stock_code: item.company_ticker,
      market: item.company_market,
      total_score: item.total_score,
      grade: item.grade,
      investment_gap: item.investment_gap ?? 0,
      cei_score: item.cei_score ?? undefined,
      rii_score: item.rii_score ?? undefined,
      cgi_score: item.cgi_score ?? undefined,
      mai_score: item.mai_score ?? undefined,
      fiscal_year: item.fiscal_year
    }))
  } catch (error) {
    console.warn('RaymondsIndex 랭킹 조회 실패:', error)
    return []
  }
}

// ============================================================================
// 헬퍼 함수
// ============================================================================

/** API 응답을 프론트엔드 타입으로 변환 */
function mapApiToRaymondsIndexData(api: ApiRaymondsIndex): RaymondsIndexData {
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

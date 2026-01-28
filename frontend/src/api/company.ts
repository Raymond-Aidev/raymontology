import apiClient from './client'
import type { CompanySearchResult } from '../types/company'

// Platform Stats 응답 타입
export interface PlatformStats {
  companies: number
  convertible_bonds: number
  officers: number
  major_shareholders: number
  financial_statements: number
}

// Backend API 응답 타입
interface ApiCompanySearchResponse {
  total: number
  page: number
  page_size: number
  items: ApiCompanyItem[]
}

interface ApiCompanyItem {
  id: string
  name: string
  ticker: string | null
  corp_code: string | null  // DART 기업코드
  sector: string | null
  market: string | null
  market_cap: number | null
  cb_count: number
  officer_count: number
  listing_status?: string | null  // LISTED, DELISTED, ETF 등
  company_type?: string | null  // NORMAL, SPAC, REIT, ETF
  trading_status?: string | null  // NORMAL, SUSPENDED, TRADING_HALT
}

// CB 발행 횟수 기반 리스크 레벨 추정
function estimateRiskLevel(cbCount: number): string {
  if (cbCount >= 8) return 'CRITICAL'
  if (cbCount >= 5) return 'HIGH'
  if (cbCount >= 3) return 'MEDIUM'
  if (cbCount >= 1) return 'LOW'
  return 'VERY_LOW'
}

// CB 발행 횟수 기반 투자등급 추정
function estimateInvestmentGrade(cbCount: number): string {
  if (cbCount >= 8) return 'CCC'
  if (cbCount >= 5) return 'B'
  if (cbCount >= 3) return 'BB'
  if (cbCount >= 1) return 'BBB'
  return 'A'
}

// API 응답을 Frontend 타입으로 변환
function mapApiResponseToFrontend(item: ApiCompanyItem): CompanySearchResult {
  return {
    id: item.id,
    corp_code: item.corp_code || '',  // 백엔드 corp_code 사용 (수정됨)
    name: item.name,
    cb_count: item.cb_count,
    risk_level: estimateRiskLevel(item.cb_count),
    investment_grade: estimateInvestmentGrade(item.cb_count),
    market: item.market || undefined,
    company_type: item.company_type || undefined,
    trading_status: item.trading_status || undefined,
  }
}

/**
 * 회사 검색 API
 * @param query 검색어 (회사명)
 * @param limit 결과 개수 (기본값: 20)
 * @returns 검색 결과 목록
 */
export async function searchCompanies(
  query: string,
  limit: number = 20
): Promise<CompanySearchResult[]> {
  try {
    const response = await apiClient.get<ApiCompanySearchResponse>('/api/companies/search', {
      params: { q: query, limit },
    })
    return response.data.items.map(mapApiResponseToFrontend)
  } catch (error) {
    console.error('회사 검색 API 호출 실패:', error)
    return []
  }
}

/**
 * 주의 필요 기업 목록 API
 * 관계형리스크등급 B 이하 기업을 랜덤으로 조회
 * CB 발행 기업 우선, 상장폐지 기업 제외
 * @param limit 결과 개수 (기본값: 6)
 * @returns 주의 필요 기업 목록
 */
export async function getHighRiskCompanies(
  _minCbCount: number = 5, // 호환성 유지 (미사용)
  limit: number = 6
): Promise<CompanySearchResult[]> {
  try {
    // 새 API: 관계형리스크등급 HIGH_RISK (고위험) 기업만 랜덤 조회 (4등급 체계)
    const response = await apiClient.get<ApiCompanySearchResponse>('/api/companies/high-risk', {
      params: { limit, min_grade: 'HIGH_RISK', has_cb: true },
    })

    return response.data.items.map(mapApiResponseToFrontend)
  } catch (error) {
    console.error('주의 필요 기업 목록 API 호출 실패:', error)
    return []
  }
}

// API 연결 상태 확인
export async function checkApiHealth(): Promise<boolean> {
  try {
    await apiClient.get('/health', { timeout: 3000 })
    return true
  } catch {
    return false
  }
}

/**
 * 플랫폼 통계 API
 * 분석 기업, CB 발행, 임원, 주주변동, 재무제표 수량 조회
 */
export async function getPlatformStats(): Promise<PlatformStats> {
  try {
    const response = await apiClient.get<PlatformStats>('/api/companies/stats')
    return response.data
  } catch (error) {
    console.error('플랫폼 통계 API 호출 실패:', error)
    // Fallback 데이터
    return {
      companies: 3922,
      convertible_bonds: 1463,
      officers: 44673,
      major_shareholders: 95191,
      financial_statements: 9432
    }
  }
}

// 조회 기록 아이템 타입
export interface ViewHistoryItem {
  id: string
  company_id: string
  company_name: string | null
  ticker: string | null
  market: string | null
  viewed_at: string
}

// 조회 기록 응답 타입
export interface ViewHistoryResponse {
  items: ViewHistoryItem[]
  total: number
  page: number
  page_size: number
}

// 조회 기록 API 에러 코드
export type ViewHistoryErrorCode =
  | 'FREE_USER'
  | 'TRIAL_EXPIRED'
  | 'SUBSCRIPTION_EXPIRED'
  | 'UNAUTHORIZED'

// 조회 기록 API 에러 응답
export interface ViewHistoryError {
  message: string
  code: ViewHistoryErrorCode
}

/**
 * 조회한 기업 목록 API
 * 유료 회원 전용 (trial, light, max)
 * @param page 페이지 번호 (기본값: 1)
 * @param pageSize 페이지 크기 (기본값: 20)
 * @returns 조회 기록 목록
 */
export async function getViewHistory(
  page: number = 1,
  pageSize: number = 20
): Promise<ViewHistoryResponse> {
  const response = await apiClient.get<ViewHistoryResponse>('/api/companies/view-history/list', {
    params: { page, page_size: pageSize },
  })
  return response.data
}

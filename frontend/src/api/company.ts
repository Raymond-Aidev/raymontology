import apiClient from './client'
import type { CompanySearchResult } from '../types/company'

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
 * 고위험 회사 목록 API
 * CB 발행 횟수가 5회 이상인 회사를 고위험으로 분류
 * @param minCbCount 최소 CB 발행 횟수 (기본값: 5)
 * @param limit 결과 개수 (기본값: 50)
 * @returns 고위험 회사 목록
 */
export async function getHighRiskCompanies(
  minCbCount: number = 5,
  limit: number = 50
): Promise<CompanySearchResult[]> {
  try {
    // /api/companies/ 사용하여 CB가 있는 회사만 조회
    const response = await apiClient.get<ApiCompanySearchResponse>('/api/companies/', {
      params: { page_size: 100, has_cb: true }, // CB 있는 회사만 조회 (max 100)
    })

    // CB 발행 횟수 기준으로 고위험 회사 필터링
    return response.data.items
      .filter(item => item.cb_count >= minCbCount)
      .sort((a, b) => b.cb_count - a.cb_count)
      .slice(0, limit)
      .map(mapApiResponseToFrontend)
  } catch (error) {
    console.error('고위험 회사 목록 API 호출 실패:', error)
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

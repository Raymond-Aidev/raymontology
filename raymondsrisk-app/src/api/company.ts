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
  corp_code: string | null
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
    corp_code: item.corp_code || '',
    name: item.name,
    cb_count: item.cb_count,
    risk_level: estimateRiskLevel(item.cb_count),
    investment_grade: estimateInvestmentGrade(item.cb_count),
  }
}

/**
 * 회사 검색 API
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
  } catch {
    return []
  }
}

/**
 * 고위험 회사 목록 API
 */
export async function getHighRiskCompanies(
  minCbCount: number = 5,
  limit: number = 50
): Promise<CompanySearchResult[]> {
  try {
    const response = await apiClient.get<ApiCompanySearchResponse>('/api/companies/', {
      params: { page_size: 100, has_cb: true },
    })

    return response.data.items
      .filter(item => item.cb_count >= minCbCount)
      .sort((a, b) => b.cb_count - a.cb_count)
      .slice(0, limit)
      .map(mapApiResponseToFrontend)
  } catch {
    return []
  }
}

/**
 * API 연결 상태 확인
 */
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
 */
export async function getPlatformStats(): Promise<PlatformStats> {
  try {
    const response = await apiClient.get<PlatformStats>('/api/companies/stats')
    return response.data
  } catch {
    return {
      companies: 3922,
      convertible_bonds: 1463,
      officers: 44673,
      major_shareholders: 95191,
      financial_statements: 9432
    }
  }
}

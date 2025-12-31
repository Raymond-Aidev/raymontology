import apiClient from '../api/client'

// 로컬 스토리지 키
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'raymondsrisk_access_token',
}

// ============================================================================
// Types
// ============================================================================

export interface CreditProduct {
  id: string
  name: string
  credits: number
  price: number
  badge: string | null
}

export interface CreditBalance {
  credits: number
  lastPurchaseAt: string | null
}

export interface PurchaseResult {
  success: boolean
  credits: number
  message: string
}

export interface CreditTransaction {
  id: string
  type: 'purchase' | 'use' | 'refund' | 'bonus'
  amount: number
  balanceAfter: number
  description: string | null
  createdAt: string
}

export interface ViewedCompany {
  companyId: string
  companyName: string | null
  firstViewedAt: string
  lastViewedAt: string
  viewCount: number
}

export interface UseCreditsResult {
  success: boolean
  credits: number
  deducted: boolean
  message: string
}

// ============================================================================
// Helper
// ============================================================================

function getAuthHeaders(): Record<string, string> {
  const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)
  if (!accessToken) {
    throw new Error('인증이 필요합니다')
  }
  return {
    Authorization: `Bearer ${accessToken}`,
  }
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * 이용권 잔액 조회
 */
export async function getBalance(): Promise<CreditBalance> {
  const response = await apiClient.get<CreditBalance>('/api/credits/balance', {
    headers: getAuthHeaders(),
  })
  return response.data
}

/**
 * 이용권 상품 목록 조회
 */
export async function getProducts(): Promise<CreditProduct[]> {
  try {
    const response = await apiClient.get<{ products: CreditProduct[] }>('/api/credits/products')
    return response.data.products
  } catch {
    // API 실패 시 기본 상품 반환
    console.warn('상품 목록 조회 실패, 기본 상품 사용')
    return [
      { id: 'report_1', name: '리포트 1건', credits: 1, price: 500, badge: null },
      { id: 'report_10', name: '리포트 10건', credits: 10, price: 3000, badge: '추천' },
      { id: 'report_30', name: '리포트 30건', credits: 30, price: 7000, badge: '최저가' },
    ]
  }
}

/**
 * 이용권 구매
 */
export async function purchaseCredits(
  productId: string,
  receiptData?: string
): Promise<PurchaseResult> {

  const response = await apiClient.post<PurchaseResult>(
    '/api/credits/purchase',
    {
      productId,
      receiptData,
    },
    {
      headers: getAuthHeaders(),
    }
  )
  return response.data
}

/**
 * 리포트 조회를 위한 이용권 차감
 */
export async function useCreditsForReport(
  companyId: string,
  companyName?: string
): Promise<UseCreditsResult> {

  const response = await apiClient.post<UseCreditsResult>(
    '/api/credits/use',
    null,
    {
      headers: getAuthHeaders(),
      params: {
        company_id: companyId,
        company_name: companyName,
      },
    }
  )
  return response.data
}

/**
 * 거래 내역 조회
 */
export async function getTransactionHistory(
  limit: number = 20,
  offset: number = 0
): Promise<{ transactions: CreditTransaction[]; total: number }> {
  const response = await apiClient.get<{ transactions: CreditTransaction[]; total: number }>(
    '/api/credits/history',
    {
      headers: getAuthHeaders(),
      params: { limit, offset },
    }
  )
  return response.data
}

/**
 * 조회한 기업 목록 (재조회 가능)
 */
export async function getViewedCompanies(
  limit: number = 50
): Promise<{ companies: ViewedCompany[]; total: number }> {
  const response = await apiClient.get<{ companies: ViewedCompany[]; total: number }>(
    '/api/credits/viewed-companies',
    {
      headers: getAuthHeaders(),
      params: { limit },
    }
  )
  return response.data
}

/**
 * 특정 기업 조회 여부 확인 (로컬 캐시 용)
 */
export function hasViewedCompany(companyId: string): boolean {
  try {
    const viewed = localStorage.getItem('raymondsrisk_viewed_companies')
    if (!viewed) return false
    const companies = JSON.parse(viewed) as string[]
    return companies.includes(companyId)
  } catch {
    return false
  }
}

/**
 * 조회 기업 로컬 캐시 저장
 */
export function cacheViewedCompany(companyId: string): void {
  try {
    const viewed = localStorage.getItem('raymondsrisk_viewed_companies')
    const companies = viewed ? (JSON.parse(viewed) as string[]) : []
    if (!companies.includes(companyId)) {
      companies.push(companyId)
      localStorage.setItem('raymondsrisk_viewed_companies', JSON.stringify(companies))
    }
  } catch {
    // 캐시 실패는 무시
  }
}

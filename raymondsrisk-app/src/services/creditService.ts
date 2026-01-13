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
  expiresAt: string | null
  isExpired: boolean
  daysRemaining: number | null
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
    // API 실패 시 기본 상품 반환 (2026-01-07 가격 개편)
    return [
      { id: 'report_10', name: '리포트 10건', credits: 10, price: 1000, badge: null },
      { id: 'report_30', name: '리포트 30건', credits: 30, price: 3000, badge: '추천' },
      { id: 'report_unlimited', name: '무제한 이용권', credits: -1, price: 10000, badge: 'BEST' },
    ]
  }
}

/**
 * 이용권 구매
 *
 * @param productId - 상품 SKU (예: report_10, report_30, report_unlimited)
 * @param orderId - 토스 인앱결제 주문 ID (프로덕션) 또는 undefined (개발환경에서 자동 생성)
 */
export async function purchaseCredits(
  productId: string,
  orderId?: string
): Promise<PurchaseResult> {
  // 개발환경에서 orderId가 없으면 mock_ prefix로 자동 생성
  const effectiveOrderId = orderId || `mock_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

  console.log('[creditService] purchaseCredits 호출:', {
    productId,
    orderId: effectiveOrderId,
    isProduction: !!orderId,
  })

  const response = await apiClient.post<PurchaseResult>(
    '/api/credits/purchase',
    {
      productId,
      orderId: effectiveOrderId,
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
  console.log('[creditService] useCreditsForReport called:', { companyId, companyName })

  // 토큰 확인 (디버깅용)
  const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)
  console.log('[creditService] accessToken exists:', !!accessToken, accessToken ? `${accessToken.substring(0, 20)}...` : 'null')

  if (!accessToken) {
    console.error('[creditService] No access token - throwing error')
    throw new Error('인증이 필요합니다')
  }

  try {
    console.log('[creditService] Calling POST /api/credits/use')
    const response = await apiClient.post<UseCreditsResult>(
      '/api/credits/use',
      null,
      {
        headers: { Authorization: `Bearer ${accessToken}` },
        params: {
          company_id: companyId,
          company_name: companyName,
        },
      }
    )
    console.log('[creditService] API response:', response.data)
    return response.data
  } catch (error) {
    console.error('[creditService] API call failed:', error)
    throw error
  }
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
 * - 30일 보관 기간 적용
 * - includeExpired=true 시 만료된 기업도 포함
 */
export async function getViewedCompanies(
  limit: number = 50,
  includeExpired: boolean = false
): Promise<{ companies: ViewedCompany[]; total: number; retentionDays: number }> {
  console.log('[creditService] getViewedCompanies called:', { limit, includeExpired })

  const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)
  console.log('[creditService] accessToken exists:', !!accessToken)

  if (!accessToken) {
    console.error('[creditService] No access token for getViewedCompanies')
    throw new Error('인증이 필요합니다')
  }

  try {
    const response = await apiClient.get<{ companies: ViewedCompany[]; total: number; retentionDays: number }>(
      '/api/credits/viewed-companies',
      {
        headers: { Authorization: `Bearer ${accessToken}` },
        params: { limit, include_expired: includeExpired },
      }
    )
    console.log('[creditService] getViewedCompanies response:', response.data)
    return response.data
  } catch (error) {
    console.error('[creditService] getViewedCompanies failed:', error)
    throw error
  }
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

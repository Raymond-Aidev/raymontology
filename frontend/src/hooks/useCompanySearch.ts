import { useQuery, useQueryClient } from '@tanstack/react-query'
import { searchCompanies, getHighRiskCompanies } from '../api/company'
import type { CompanySearchResult } from '../types/company'

// Query Key 상수
export const companySearchKeys = {
  all: ['company-search'] as const,
  search: (query: string) => [...companySearchKeys.all, 'search', query] as const,
  highRisk: (minCbCount: number) => [...companySearchKeys.all, 'high-risk', minCbCount] as const,
}

// 회사 검색 훅
export function useCompanySearch(
  query: string,
  options?: {
    enabled?: boolean
    staleTime?: number
    limit?: number
  }
) {
  const limit = options?.limit ?? 20

  return useQuery<CompanySearchResult[], Error>({
    queryKey: companySearchKeys.search(query),
    queryFn: () => searchCompanies(query, limit),
    enabled: query.length >= 2 && (options?.enabled !== false),
    staleTime: options?.staleTime ?? 30 * 1000, // 30초
    gcTime: 5 * 60 * 1000, // 5분
    placeholderData: (previousData) => previousData, // 검색 중 이전 결과 유지
  })
}

// 고위험 회사 목록 훅
export function useHighRiskCompanies(
  minCbCount: number = 5,
  options?: {
    enabled?: boolean
    staleTime?: number
    limit?: number
  }
) {
  const limit = options?.limit ?? 50

  return useQuery<CompanySearchResult[], Error>({
    queryKey: companySearchKeys.highRisk(minCbCount),
    queryFn: () => getHighRiskCompanies(minCbCount, limit),
    enabled: options?.enabled !== false,
    staleTime: options?.staleTime ?? 5 * 60 * 1000, // 5분
    gcTime: 10 * 60 * 1000, // 10분
  })
}

// 검색 캐시 관리 훅
export function useCompanySearchCache() {
  const queryClient = useQueryClient()

  return {
    // 특정 검색어 캐시 무효화
    invalidateSearch: (query: string) => {
      queryClient.invalidateQueries({ queryKey: companySearchKeys.search(query) })
    },
    // 모든 검색 캐시 무효화
    invalidateAll: () => {
      queryClient.invalidateQueries({ queryKey: companySearchKeys.all })
    },
    // 캐시에서 검색 결과 읽기
    getFromCache: (query: string): CompanySearchResult[] | undefined => {
      return queryClient.getQueryData<CompanySearchResult[]>(companySearchKeys.search(query))
    },
  }
}

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getCompanyReport, type CompanyReportData } from '../api/report'

// Query Key 상수
export const reportKeys = {
  all: ['report'] as const,
  company: (companyId: string) => [...reportKeys.all, 'company', companyId] as const,
}

// 보고서 데이터 조회 훅
export function useReportQuery(
  companyId: string | undefined,
  options?: {
    enabled?: boolean
    staleTime?: number
    refetchOnWindowFocus?: boolean
  }
) {
  return useQuery<CompanyReportData, Error>({
    queryKey: reportKeys.company(companyId || ''),
    queryFn: async () => {
      if (!companyId) {
        throw new Error('Company ID is required')
      }
      return getCompanyReport(companyId)
    },
    enabled: !!companyId && (options?.enabled !== false),
    staleTime: options?.staleTime ?? 10 * 60 * 1000, // 10분
    gcTime: 30 * 60 * 1000, // 30분 (구 cacheTime)
    refetchOnWindowFocus: options?.refetchOnWindowFocus ?? false,
    retry: 1,
  })
}

// 보고서 데이터 프리페치 훅
export function usePrefetchReport() {
  const queryClient = useQueryClient()

  return async (companyId: string) => {
    await queryClient.prefetchQuery({
      queryKey: reportKeys.company(companyId),
      queryFn: () => getCompanyReport(companyId),
      staleTime: 10 * 60 * 1000,
    })
  }
}

// 보고서 캐시 관리 훅
export function useReportCache() {
  const queryClient = useQueryClient()

  return {
    // 캐시에서 데이터 읽기
    getFromCache: (companyId: string): CompanyReportData | undefined => {
      return queryClient.getQueryData<CompanyReportData>(reportKeys.company(companyId))
    },
    // 특정 회사 보고서 무효화
    invalidate: (companyId: string) => {
      queryClient.invalidateQueries({ queryKey: reportKeys.company(companyId) })
    },
    // 모든 보고서 무효화
    invalidateAll: () => {
      queryClient.invalidateQueries({ queryKey: reportKeys.all })
    },
    // 캐시에서 제거
    remove: (companyId: string) => {
      queryClient.removeQueries({ queryKey: reportKeys.company(companyId) })
    },
    // 캐시에 직접 데이터 설정
    setData: (companyId: string, data: CompanyReportData) => {
      queryClient.setQueryData(reportKeys.company(companyId), data)
    },
  }
}

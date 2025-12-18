import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchOfficerCareer, getOfficerCareerNetwork, type OfficerCareer } from '../api/graph'
import type { GraphData } from '../types/graph'

// Query Key 상수
export const officerCareerKeys = {
  all: ['officer-career'] as const,
  career: (officerId: string) => [...officerCareerKeys.all, 'career', officerId] as const,
  network: (officerId: string) => [...officerCareerKeys.all, 'network', officerId] as const,
}

// 임원 경력 조회 훅
export function useOfficerCareer(
  officerId: string | undefined,
  options?: {
    enabled?: boolean
    staleTime?: number
  }
) {
  return useQuery<OfficerCareer[], Error>({
    queryKey: officerCareerKeys.career(officerId || ''),
    queryFn: () => fetchOfficerCareer(officerId!),
    enabled: !!officerId && (options?.enabled !== false),
    staleTime: options?.staleTime ?? 10 * 60 * 1000, // 10분
    gcTime: 30 * 60 * 1000, // 30분
  })
}

// 임원 경력 네트워크 조회 훅
export function useOfficerCareerNetwork(
  officerId: string | undefined,
  options?: {
    enabled?: boolean
    staleTime?: number
  }
) {
  return useQuery<GraphData, Error>({
    queryKey: officerCareerKeys.network(officerId || ''),
    queryFn: () => getOfficerCareerNetwork(officerId!),
    enabled: !!officerId && (options?.enabled !== false),
    staleTime: options?.staleTime ?? 5 * 60 * 1000, // 5분
    gcTime: 10 * 60 * 1000, // 10분
  })
}

// 임원 경력 캐시 관리 훅
export function useOfficerCareerCache() {
  const queryClient = useQueryClient()

  return {
    // 특정 임원 경력 프리페치
    prefetch: async (officerId: string) => {
      await queryClient.prefetchQuery({
        queryKey: officerCareerKeys.career(officerId),
        queryFn: () => fetchOfficerCareer(officerId),
        staleTime: 10 * 60 * 1000,
      })
    },
    // 캐시 무효화
    invalidate: (officerId: string) => {
      queryClient.invalidateQueries({ queryKey: officerCareerKeys.career(officerId) })
    },
    // 캐시에서 읽기
    getFromCache: (officerId: string): OfficerCareer[] | undefined => {
      return queryClient.getQueryData<OfficerCareer[]>(officerCareerKeys.career(officerId))
    },
  }
}

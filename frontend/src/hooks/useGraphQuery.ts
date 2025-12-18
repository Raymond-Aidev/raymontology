import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getCompanyNetwork, NODE_LIMIT, DEFAULT_DEPTH, type DateRangeParams } from '../api/graph'
import type { GraphData, GraphNode } from '../types/graph'

// Query Key 상수
export const graphKeys = {
  all: ['graph'] as const,
  company: (companyId: string) => [...graphKeys.all, 'company', companyId] as const,
  companyWithParams: (companyId: string, depth: number, dateRange?: DateRangeParams) =>
    [...graphKeys.company(companyId), { depth, dateRange }] as const,
}

// 그래프 데이터 응답 타입
export interface GraphQueryResult extends GraphData {
  isLimited: boolean
  originalCount: number
}

// 그래프 데이터 조회 훅
export function useGraphQuery(
  companyId: string | undefined,
  depth: number = DEFAULT_DEPTH,
  dateRange?: DateRangeParams,
  options?: {
    enabled?: boolean
    staleTime?: number
    refetchOnWindowFocus?: boolean
  }
) {
  return useQuery<GraphQueryResult, Error>({
    queryKey: graphKeys.companyWithParams(companyId || '', depth, dateRange),
    queryFn: async () => {
      if (!companyId) {
        throw new Error('Company ID is required')
      }
      return getCompanyNetwork(companyId, depth, NODE_LIMIT, dateRange)
    },
    enabled: !!companyId && (options?.enabled !== false),
    staleTime: options?.staleTime ?? 5 * 60 * 1000, // 5분
    gcTime: 10 * 60 * 1000, // 10분 (구 cacheTime)
    refetchOnWindowFocus: options?.refetchOnWindowFocus ?? false,
    retry: 1,
  })
}

// 그래프 데이터 프리페치 훅 (다음 회사 미리 로드용)
export function usePrefetchGraph() {
  const queryClient = useQueryClient()

  return async (companyId: string, depth: number = DEFAULT_DEPTH) => {
    await queryClient.prefetchQuery({
      queryKey: graphKeys.companyWithParams(companyId, depth),
      queryFn: () => getCompanyNetwork(companyId, depth, NODE_LIMIT),
      staleTime: 5 * 60 * 1000,
    })
  }
}

// 그래프 캐시 무효화 훅
export function useInvalidateGraph() {
  const queryClient = useQueryClient()

  return {
    // 특정 회사 그래프 무효화
    invalidateCompany: (companyId: string) => {
      queryClient.invalidateQueries({ queryKey: graphKeys.company(companyId) })
    },
    // 모든 그래프 무효화
    invalidateAll: () => {
      queryClient.invalidateQueries({ queryKey: graphKeys.all })
    },
    // 캐시에서 특정 회사 제거
    removeCompany: (companyId: string) => {
      queryClient.removeQueries({ queryKey: graphKeys.company(companyId) })
    },
  }
}

// 노드 선택 시 관련 회사 프리페치
export function usePrefetchRelatedCompanies() {
  const prefetch = usePrefetchGraph()

  return (node: GraphNode, allNodes: GraphNode[]) => {
    if (node.type === 'company') {
      // 이미 로드된 회사는 프리페치 불필요
      return
    }

    // 관련된 회사 노드들 찾기 (임원/인수인의 다른 회사들)
    const relatedCompanies = allNodes
      .filter(n => n.type === 'company' && n.id !== node.id)
      .slice(0, 3) // 최대 3개만 프리페치

    relatedCompanies.forEach(company => {
      prefetch(company.id, 1)
    })
  }
}

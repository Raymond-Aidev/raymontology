'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { RankingParams, VulnerableMAParams } from '@/lib/types';

export function useRanking(params: RankingParams = {}) {
  return useQuery({
    queryKey: ['ranking', params],
    queryFn: () => api.ranking.getAll(params),
  });
}

export function useTopRanking(limit: number = 10) {
  return useQuery({
    queryKey: ['ranking', 'top', limit],
    queryFn: () => api.ranking.getTop(limit),
  });
}

// 위험기업 랭킹 (낮은 점수순)
export function useBottomRanking(limit: number = 10) {
  return useQuery({
    queryKey: ['ranking', 'bottom', limit],
    queryFn: () => api.ranking.getBottom(limit),
  });
}

// Sub-Index별 랭킹
export function useSubIndexRanking(
  subIndex: 'cei' | 'rii' | 'cgi' | 'mai',
  limit: number = 10,
  ascending: boolean = true
) {
  return useQuery({
    queryKey: ['ranking', 'subindex', subIndex, limit, ascending],
    queryFn: () => api.ranking.getBySubIndex(subIndex, limit, ascending),
  });
}

// 적대적 M&A 취약기업 랭킹
export function useVulnerableMA(params: VulnerableMAParams = {}) {
  return useQuery({
    queryKey: ['vulnerable-ma', params],
    queryFn: () => api.vulnerableMA.getRanking(params),
  });
}

'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { RankingParams } from '@/lib/types';

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

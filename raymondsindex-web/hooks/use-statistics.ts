'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useStatistics() {
  return useQuery({
    queryKey: ['statistics'],
    queryFn: () => api.statistics.get(),
  });
}

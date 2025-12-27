'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useCompany(companyId: string) {
  return useQuery({
    queryKey: ['company', companyId],
    queryFn: () => api.company.getById(companyId),
    enabled: !!companyId,
  });
}

'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useState, useEffect } from 'react';

export function useSearch(query: string, limit: number = 10) {
  return useQuery({
    queryKey: ['search', query, limit],
    queryFn: () => api.search.query(query, limit),
    enabled: query.length >= 1,
  });
}

export function useDebouncedSearch(initialQuery: string = '', debounceMs: number = 300) {
  const [query, setQuery] = useState(initialQuery);
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, debounceMs);

    return () => clearTimeout(timer);
  }, [query, debounceMs]);

  const searchResult = useSearch(debouncedQuery);

  return {
    query,
    setQuery,
    ...searchResult,
  };
}

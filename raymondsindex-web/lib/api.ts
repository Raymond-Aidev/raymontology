// API 클라이언트

import { API_BASE_URL } from './constants';
import type { RankingResponse, RaymondsIndexResponse, StatisticsResponse, SearchResult, RankingParams } from './types';

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export const api = {
  ranking: {
    getAll: async (params: RankingParams = {}): Promise<RankingResponse> => {
      const searchParams = new URLSearchParams();

      // Convert page/size to offset/limit
      const page = params.page || 1;
      const size = params.size || 20;
      const offset = (page - 1) * size;

      searchParams.set('limit', size.toString());
      searchParams.set('offset', offset.toString());

      if (params.grade) searchParams.set('grade', params.grade);
      if (params.sort) searchParams.set('sort', params.sort);
      if (params.min_score) searchParams.set('min_score', params.min_score.toString());
      if (params.max_score) searchParams.set('max_score', params.max_score.toString());

      const query = searchParams.toString();
      const data = await fetchAPI<{
        total: number;
        offset: number;
        limit: number;
        rankings: RaymondsIndexResponse[];
      }>(`/raymonds-index/ranking/list?${query}`);

      return {
        items: data.rankings,
        total: data.total,
        page,
        size,
        total_pages: Math.ceil(data.total / size),
      };
    },

    getTop: async (limit: number = 10): Promise<RankingResponse> => {
      const data = await fetchAPI<{
        total: number;
        offset: number;
        limit: number;
        rankings: RaymondsIndexResponse[];
      }>(`/raymonds-index/ranking/list?limit=${limit}&offset=0&sort=score_desc`);

      return {
        items: data.rankings,
        total: data.total,
        page: 1,
        size: limit,
        total_pages: Math.ceil(data.total / limit),
      };
    },
  },

  company: {
    getById: async (companyId: string): Promise<RaymondsIndexResponse> => {
      return fetchAPI<RaymondsIndexResponse>(`/raymonds-index/${companyId}`);
    },
  },

  search: {
    query: async (q: string, limit: number = 10): Promise<SearchResult[]> => {
      // Use search/filter endpoint with company name search
      const data = await fetchAPI<{
        total: number;
        results: RaymondsIndexResponse[];
      }>(`/raymonds-index/search/filter?limit=${limit}`);

      // Filter by name on client side for now
      const filtered = data.results.filter(item =>
        item.company_name?.toLowerCase().includes(q.toLowerCase()) ||
        item.stock_code?.includes(q)
      );

      return filtered.map(item => ({
        company_id: item.company_id,
        company_name: item.company_name,
        stock_code: item.stock_code || '',
        grade: item.grade,
        total_score: item.total_score,
      }));
    },
  },

  statistics: {
    get: async (): Promise<StatisticsResponse> => {
      const data = await fetchAPI<{
        total_companies: number;
        average_score: number;
        min_score: number;
        max_score: number;
        average_investment_gap: number;
        grade_distribution: Record<string, number>;
        year: number | null;
      }>('/raymonds-index/statistics/summary');

      // Convert grade_distribution object to array format
      const totalCount = Object.values(data.grade_distribution).reduce((a, b) => a + b, 0);
      const gradeDistribution = Object.entries(data.grade_distribution).map(([grade, count]) => ({
        grade,
        count,
        percentage: totalCount > 0 ? (count / totalCount) * 100 : 0,
      }));

      return {
        total_companies: data.total_companies,
        grade_distribution: gradeDistribution,
        average_score: data.average_score,
        median_score: data.average_score, // API doesn't provide median
        updated_at: new Date().toISOString(),
      };
    },
  },
};

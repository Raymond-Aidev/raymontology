// API 클라이언트

import { API_BASE_URL } from './constants';
import type {
  RankingResponse,
  RaymondsIndexResponse,
  StatisticsResponse,
  SearchResult,
  RankingParams,
  StockPriceChartResponse,
  StockPriceStatusResponse,
  MATargetResponse,
  MATargetRankingResponse,
  MATargetParams,
  MATargetStatsResponse
} from './types';

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

      // 기본 필터
      if (params.grade) searchParams.set('grade', params.grade);
      if (params.market) searchParams.set('market', params.market);
      if (params.sort) searchParams.set('sort', params.sort);
      if (params.year) searchParams.set('year', params.year.toString());

      // 점수 범위 필터
      if (params.min_score !== undefined) searchParams.set('min_score', params.min_score.toString());
      if (params.max_score !== undefined) searchParams.set('max_score', params.max_score.toString());

      // Sub-Index 필터 (확장 스크리너)
      if (params.min_cei !== undefined) searchParams.set('min_cei', params.min_cei.toString());
      if (params.max_cei !== undefined) searchParams.set('max_cei', params.max_cei.toString());
      if (params.min_rii !== undefined) searchParams.set('min_rii', params.min_rii.toString());
      if (params.max_rii !== undefined) searchParams.set('max_rii', params.max_rii.toString());
      if (params.min_cgi !== undefined) searchParams.set('min_cgi', params.min_cgi.toString());
      if (params.max_cgi !== undefined) searchParams.set('max_cgi', params.max_cgi.toString());
      if (params.min_mai !== undefined) searchParams.set('min_mai', params.min_mai.toString());
      if (params.max_mai !== undefined) searchParams.set('max_mai', params.max_mai.toString());

      // 투자괴리율 필터
      if (params.min_gap !== undefined) searchParams.set('min_gap', params.min_gap.toString());
      if (params.max_gap !== undefined) searchParams.set('max_gap', params.max_gap.toString());

      // Red Flag 필터
      if (params.has_red_flags !== undefined) searchParams.set('has_red_flags', params.has_red_flags.toString());

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
      // Use dedicated search endpoint with server-side filtering
      const data = await fetchAPI<{
        query: string;
        total: number;
        results: RaymondsIndexResponse[];
      }>(`/raymonds-index/search/companies?q=${encodeURIComponent(q)}&limit=${limit}`);

      return data.results.map(item => ({
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

  // 주가 데이터 API
  stockPrices: {
    // 차트용 데이터 조회
    getChartData: async (
      companyId: string,
      period: '1y' | '2y' | '3y' | 'all' = '3y'
    ): Promise<StockPriceChartResponse> => {
      return fetchAPI<StockPriceChartResponse>(
        `/stock-prices/company/${companyId}/chart?period=${period}`
      );
    },

    // 수집 현황 조회
    getStatus: async (): Promise<StockPriceStatusResponse> => {
      return fetchAPI<StockPriceStatusResponse>('/stock-prices/status');
    },
  },

  // M&A 타겟 API
  maTarget: {
    // 랭킹 조회
    getRanking: async (params: MATargetParams = {}): Promise<MATargetRankingResponse> => {
      const searchParams = new URLSearchParams();

      const page = params.page || 1;
      const size = params.size || 20;
      const offset = (page - 1) * size;

      searchParams.set('limit', size.toString());
      searchParams.set('offset', offset.toString());

      if (params.grade) searchParams.set('grade', params.grade);
      if (params.market) searchParams.set('market', params.market);
      if (params.sort) searchParams.set('sort', params.sort);
      if (params.min_score !== undefined) searchParams.set('min_score', params.min_score.toString());
      if (params.max_score !== undefined) searchParams.set('max_score', params.max_score.toString());
      if (params.min_market_cap !== undefined) searchParams.set('min_market_cap', params.min_market_cap.toString());
      if (params.max_market_cap !== undefined) searchParams.set('max_market_cap', params.max_market_cap.toString());
      if (params.min_cash_ratio !== undefined) searchParams.set('min_cash_ratio', params.min_cash_ratio.toString());
      if (params.min_revenue_growth !== undefined) searchParams.set('min_revenue_growth', params.min_revenue_growth.toString());
      if (params.min_tangible_growth !== undefined) searchParams.set('min_tangible_growth', params.min_tangible_growth.toString());
      if (params.min_op_profit_growth !== undefined) searchParams.set('min_op_profit_growth', params.min_op_profit_growth.toString());
      if (params.snapshot_date) searchParams.set('snapshot_date', params.snapshot_date);

      const query = searchParams.toString();
      const data = await fetchAPI<{
        total: number;
        offset: number;
        limit: number;
        snapshot_date: string | null;
        rankings: MATargetResponse[];
      }>(`/ma-target/ranking?${query}`);

      return {
        items: data.rankings,
        total: data.total,
        page,
        size,
        total_pages: Math.ceil(data.total / size),
        snapshot_date: data.snapshot_date,
      };
    },

    // 통계 조회 (필터 지원)
    getStats: async (params: MATargetParams = {}): Promise<MATargetStatsResponse> => {
      const searchParams = new URLSearchParams();

      if (params.grade) searchParams.set('grade', params.grade);
      if (params.market) searchParams.set('market', params.market);
      if (params.min_market_cap !== undefined) searchParams.set('min_market_cap', params.min_market_cap.toString());
      if (params.max_market_cap !== undefined) searchParams.set('max_market_cap', params.max_market_cap.toString());
      if (params.min_cash_assets !== undefined) searchParams.set('min_cash_assets', params.min_cash_assets.toString());
      if (params.max_cash_assets !== undefined) searchParams.set('max_cash_assets', params.max_cash_assets.toString());
      if (params.min_cash_ratio !== undefined) searchParams.set('min_cash_ratio', params.min_cash_ratio.toString());
      if (params.max_cash_ratio !== undefined) searchParams.set('max_cash_ratio', params.max_cash_ratio.toString());
      if (params.min_revenue_growth !== undefined) searchParams.set('min_revenue_growth', params.min_revenue_growth.toString());
      if (params.max_revenue_growth !== undefined) searchParams.set('max_revenue_growth', params.max_revenue_growth.toString());
      if (params.min_tangible_growth !== undefined) searchParams.set('min_tangible_growth', params.min_tangible_growth.toString());
      if (params.max_tangible_growth !== undefined) searchParams.set('max_tangible_growth', params.max_tangible_growth.toString());
      if (params.snapshot_date) searchParams.set('snapshot_date', params.snapshot_date);

      const query = searchParams.toString();
      return fetchAPI<MATargetStatsResponse>(`/ma-target/stats${query ? `?${query}` : ''}`);
    },

    // 기업 상세 조회
    getCompany: async (companyId: string): Promise<MATargetResponse> => {
      return fetchAPI<MATargetResponse>(`/ma-target/company/${companyId}`);
    },
  },
};

// RaymondsIndex 타입 정의

export interface RaymondsIndexResponse {
  id: string;
  company_id: string;
  company_name: string;
  stock_code: string;
  sector?: string;
  fiscal_year: number;
  total_score: number;
  grade: string;

  // Sub-Index
  cei_score: number | null;
  rii_score: number | null;
  cgi_score: number | null;
  mai_score: number | null;

  // 핵심 지표
  investment_gap: number | null;
  cash_cagr: number | null;
  capex_growth: number | null;
  idle_cash_ratio: number | null;
  roic: number | null;
  reinvestment_rate: number | null;
  shareholder_return: number | null;

  // v4.0 기존 지표
  cash_tangible_ratio: number | null;
  fundraising_utilization: number | null;
  short_term_ratio: number | null;
  capex_trend: 'increasing' | 'stable' | 'decreasing' | null;
  capex_cv: number | null;
  violation_count: number;

  // v2.0 신규 지표
  investment_gap_v2: number | null;
  cash_utilization: number | null;
  industry_sector: string | null;
  weight_adjustment: Record<string, number> | null;

  // 위험 신호
  red_flags: string[];
  yellow_flags: string[];

  // AI 해석
  verdict: string | null;
  key_risk: string | null;
  recommendation: string | null;
  watch_trigger: string | null;

  data_quality_score: number | null;
  calculation_date: string;
}

export interface RankingResponse {
  items: RaymondsIndexResponse[];
  total: number;
  page: number;
  size: number;
  total_pages: number;
}

export interface StatisticsResponse {
  total_companies: number;
  grade_distribution: {
    grade: string;
    count: number;
    percentage: number;
  }[];
  average_score: number;
  median_score: number;
  updated_at: string;
}

export interface SearchResult {
  company_id: string;
  company_name: string;
  stock_code: string;
  grade: string;
  total_score: number;
}

export interface RankingParams {
  page?: number;
  size?: number;
  grade?: string;
  sector?: string;
  min_score?: number;
  max_score?: number;
  sort?: 'score_desc' | 'score_asc' | 'name_asc' | 'name_desc';
}

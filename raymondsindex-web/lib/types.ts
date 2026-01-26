// RaymondsIndex 타입 정의

export interface RaymondsIndexResponse {
  id: string;
  company_id: string;
  company_name: string;
  stock_code: string;
  sector?: string;
  market?: string;                    // KOSPI, KOSDAQ, KONEX
  company_type?: string;              // NORMAL, SPAC, REIT, ETF
  trading_status?: string;            // NORMAL, SUSPENDED, TRADING_HALT
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

  // v2.0/v2.1 지표
  investment_gap_v2: number | null;      // 투자괴리율 v2 (레거시: 재투자율 기반)
  investment_gap_v21: number | null;     // 투자괴리율 v2.1 ⭐핵심 (현금 CAGR - CAPEX 성장률)
  investment_gap_v21_flag: 'ok' | 'no_capex' | 'no_cash' | 'insufficient_data';  // 데이터 품질 플래그
  cash_utilization: number | null;
  industry_sector: string | null;
  weight_adjustment: Record<string, number> | null;

  // v2.1 신규 지표
  tangible_efficiency: number | null;     // 유형자산 효율성 (매출/유형자산)
  cash_yield: number | null;              // 현금 수익률 (영업이익/총현금 %)
  debt_to_ebitda: number | null;          // 부채/EBITDA
  growth_investment_ratio: number | null; // 성장 투자 비율 (성장CAPEX/총CAPEX %)

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
  grade?: string;                     // 등급 (쉼표 구분: A++,A+,A)
  sector?: string;
  market?: string;                    // KOSPI, KOSDAQ 필터 (쉼표 구분)
  company_type?: string;              // NORMAL, SPAC, REIT, ETF 필터
  year?: number;                      // 연도 필터

  // 점수 범위 필터
  min_score?: number;
  max_score?: number;

  // Sub-Index 필터 (확장 스크리너용)
  min_cei?: number;
  max_cei?: number;
  min_rii?: number;
  max_rii?: number;
  min_cgi?: number;
  max_cgi?: number;
  min_mai?: number;
  max_mai?: number;

  // 투자괴리율 필터
  min_gap?: number;
  max_gap?: number;

  // 위험신호 필터
  has_red_flags?: boolean;

  // 정렬
  sort?: 'score_desc' | 'score_asc' | 'name_asc' | 'name_desc' | 'gap_asc' | 'gap_desc' | 'cei_desc' | 'rii_desc' | 'cgi_desc' | 'mai_desc';
}

// 주가 데이터 타입
export interface StockPriceData {
  month: string;
  close: number;
  open: number | null;
  high: number | null;
  low: number | null;
  volume: number | null;
  change: number | null;
}

export interface StockPriceChartResponse {
  company: {
    id: string;
    name: string;
    ticker: string;
    market: string;
  };
  period: string;
  labels: string[];
  data: StockPriceData[];
  performance: {
    start_month: string;
    end_month: string;
    start_price: number;
    end_price: number;
    total_return_pct: number;
    data_points: number;
  };
  message?: string;
}

export interface StockPriceStatusResponse {
  total_listed_companies: number;
  companies_with_prices: number;
  coverage_rate: number;
  total_price_records: number;
  latest_data_month: string | null;
}

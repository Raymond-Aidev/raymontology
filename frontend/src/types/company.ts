// 회사 검색 결과 타입
export interface CompanySearchResult {
  id: string
  corp_code: string
  name: string
  cb_count: number
  risk_level: string | null
  investment_grade: string | null
  market?: string  // 시장 구분 (KOSPI, KOSDAQ, KONEX, ETF)
  company_type?: string  // 기업 유형 (NORMAL, SPAC, REIT, ETF)
  trading_status?: string  // 거래 상태 (NORMAL, SUSPENDED, TRADING_HALT)
}

// 리스크 레벨 타입
export type RiskLevel = 'VERY_LOW' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

// 투자등급 타입 (4등급 체계 - 2026-01-28 개편)
export type InvestmentGrade = 'LOW_RISK' | 'RISK' | 'MEDIUM_RISK' | 'HIGH_RISK'

// 하위 호환성을 위한 레거시 타입
export type LegacyInvestmentGrade = 'AAA' | 'AA' | 'A' | 'BBB' | 'BB' | 'B' | 'CCC' | 'D'

// 리스크 레벨 색상 매핑 (다크 테마 최적화)
export const riskLevelColors: Record<string, { bg: string; text: string; label: string }> = {
  VERY_LOW: { bg: 'bg-green-500/10', text: 'text-green-400', label: '매우 낮음' },
  LOW: { bg: 'bg-blue-500/10', text: 'text-blue-400', label: '낮음' },
  MEDIUM: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', label: '보통' },
  HIGH: { bg: 'bg-orange-500/10', text: 'text-orange-400', label: '높음' },
  CRITICAL: { bg: 'bg-red-500/10', text: 'text-red-400', label: '위험' },
}

// 투자등급 색상 매핑 (4등급 체계 - 2026-01-28 개편)
export const gradeColors: Record<string, string> = {
  // 신규 4등급
  LOW_RISK: 'text-green-400',     // 저위험
  RISK: 'text-yellow-400',        // 위험
  MEDIUM_RISK: 'text-orange-400', // 중위험
  HIGH_RISK: 'text-red-500',      // 고위험
  // 레거시 호환 (DB 마이그레이션 전)
  AAA: 'text-green-400',
  AA: 'text-green-400',
  A: 'text-blue-400',
  BBB: 'text-blue-400',
  BB: 'text-yellow-400',
  B: 'text-orange-400',
  CCC: 'text-orange-500',
  D: 'text-red-500',
}

// 등급 라벨 매핑
export const gradeLabels: Record<string, string> = {
  LOW_RISK: '저위험',
  RISK: '위험',
  MEDIUM_RISK: '중위험',
  HIGH_RISK: '고위험',
  // 레거시 호환
  AAA: '최우량', AA: '우량', A: '양호', BBB: '적정',
  BB: '투기', B: '고위험', CCC: '매우위험', D: '부도',
}

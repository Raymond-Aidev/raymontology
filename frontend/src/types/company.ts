// 회사 검색 결과 타입
export interface CompanySearchResult {
  id: string
  corp_code: string
  name: string
  cb_count: number
  risk_level: string | null
  investment_grade: string | null
}

// 리스크 레벨 타입
export type RiskLevel = 'VERY_LOW' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

// 투자등급 타입
export type InvestmentGrade = 'AAA' | 'AA' | 'A' | 'BBB' | 'BB' | 'B' | 'CCC' | 'D'

// 리스크 레벨 색상 매핑 (다크 테마 최적화)
export const riskLevelColors: Record<string, { bg: string; text: string; label: string }> = {
  VERY_LOW: { bg: 'bg-green-500/10', text: 'text-green-400', label: '매우 낮음' },
  LOW: { bg: 'bg-blue-500/10', text: 'text-blue-400', label: '낮음' },
  MEDIUM: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', label: '보통' },
  HIGH: { bg: 'bg-orange-500/10', text: 'text-orange-400', label: '높음' },
  CRITICAL: { bg: 'bg-red-500/10', text: 'text-red-400', label: '위험' },
}

// 투자등급 색상 매핑 (다크 테마 최적화 - 밝은 색상)
export const gradeColors: Record<string, string> = {
  AAA: 'text-green-400',
  AA: 'text-green-400',
  A: 'text-blue-400',
  BBB: 'text-blue-400',
  BB: 'text-yellow-400',
  B: 'text-orange-400',
  CCC: 'text-orange-500',
  D: 'text-red-500',
}

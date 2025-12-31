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

// 리스크 레벨 설정
export const riskLevelConfig: Record<RiskLevel, { color: string; label: string }> = {
  VERY_LOW: { color: '#10B981', label: '매우 낮음' },
  LOW: { color: '#3B82F6', label: '낮음' },
  MEDIUM: { color: '#F59E0B', label: '보통' },
  HIGH: { color: '#F97316', label: '높음' },
  CRITICAL: { color: '#EF4444', label: '위험' },
}

// 투자등급 설정
export const gradeConfig: Record<InvestmentGrade, { color: string; label: string }> = {
  AAA: { color: '#059669', label: '최우량' },
  AA: { color: '#10B981', label: '우량' },
  A: { color: '#34D399', label: '양호' },
  BBB: { color: '#FBBF24', label: '적정' },
  BB: { color: '#F59E0B', label: '투기' },
  B: { color: '#F97316', label: '고위험' },
  CCC: { color: '#EF4444', label: '매우위험' },
  D: { color: '#991B1B', label: '부도' },
}

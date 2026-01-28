// 리스크 점수 데이터
export interface RiskScore {
  total: number // 0-100
  cbRisk: number // CB 관련 리스크
  officerRisk: number // 임원 관련 리스크
  financialRisk: number // 재무 관련 리스크
  networkRisk: number // 네트워크 관련 리스크
}

// 투자등급 (4등급 체계 - 2026-01-28 개편)
export type InvestmentGrade = 'LOW_RISK' | 'RISK' | 'MEDIUM_RISK' | 'HIGH_RISK'

// 하위 호환성을 위한 레거시 등급 타입 (DB 마이그레이션 전 지원)
export type LegacyInvestmentGrade = 'AAA' | 'AA' | 'A' | 'BBB' | 'BB' | 'B' | 'CCC' | 'CC' | 'C' | 'D'

// 회사 리포트 데이터
export interface CompanyReport {
  id: string
  name: string
  corp_code: string
  risk_score: RiskScore
  investment_grade: InvestmentGrade
  summary: string
}

// CB 발행 데이터
export interface CBIssuance {
  id: string
  issue_date: string
  amount: number
  conversion_price: number
  maturity_date: string
  coupon_rate: number
  status: 'active' | 'converted' | 'redeemed'
  issue_round?: string  // "제N회" 형태의 발행회차
}

// CB 인수인 데이터
export interface CBSubscriber {
  id: string
  name: string
  amount: number
  ratio: number
  type: 'institution' | 'individual' | 'related'
  issue_rounds?: string[]  // 인수한 CB 회차 목록 (예: ["제45회", "제46회"])
}

// 임원 데이터
export interface Officer {
  id: string
  name: string
  position: string
  tenure_start?: string
  tenure_end?: string
  is_current: boolean
  other_positions?: string[]
}

// 재무제표 데이터
export interface FinancialStatement {
  year: number
  quarter?: string | null  // Q1, Q2, Q3, Q4, null (연간)
  revenue: number
  operating_profit: number
  net_income: number
  total_assets: number
  total_liabilities: number
  equity: number
  // 계산된 재무비율
  debt_ratio?: number  // 부채비율 (%)
  current_ratio?: number  // 유동비율 (%)
}

// 주주 유형
export type ShareholderType = 'major' | 'executive' | 'institution' | 'general'

// 주주 데이터
export interface Shareholder {
  id: string
  name: string
  shares: number
  percentage: number
  type: ShareholderType
}

// 주주 유형별 설정
export const shareholderTypeConfig: Record<ShareholderType, { bg: string; text: string; label: string } | null> = {
  major: { bg: 'bg-blue-100', text: 'text-blue-700', label: '대주주' },
  executive: { bg: 'bg-green-100', text: 'text-green-700', label: '임원' },
  institution: { bg: 'bg-gray-100', text: 'text-gray-700', label: '기관투자자' },
  general: null, // 배지 없음
}

// 리스크 신호 심각도
export type RiskSignalSeverity = 'HIGH' | 'MEDIUM' | 'LOW'

// 리스크 신호 데이터
export interface RiskSignal {
  id: string
  pattern_name: string
  severity: RiskSignalSeverity
  description: string
  detected_at?: string
}

// 심각도별 설정 (다크 테마)
export const severityConfig: Record<RiskSignalSeverity, { bg: string; text: string; border: string; label: string }> = {
  HIGH: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30', label: '높음' },
  MEDIUM: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30', label: '보통' },
  LOW: { bg: 'bg-theme-surface', text: 'text-text-muted', border: 'border-theme-border', label: '낮음' },
}

// 계열회사 관계 유형
export type AffiliateRelation = 'subsidiary' | 'grandchild' | 'associate'

// 계열회사 데이터
export interface Affiliate {
  id: string
  name: string
  company_id?: string // 클릭 시 이동용
  relation: AffiliateRelation
  percentage: number
  industry: string
  founded_date?: string
}

// 계열회사 관계 유형별 설정
export const affiliateRelationConfig: Record<AffiliateRelation, { bg: string; text: string; label: string }> = {
  subsidiary: { bg: 'bg-blue-100', text: 'text-blue-700', label: '자회사' },
  grandchild: { bg: 'bg-sky-100', text: 'text-sky-700', label: '손자회사' },
  associate: { bg: 'bg-gray-100', text: 'text-gray-700', label: '관계회사' },
}

// 리스크 레벨별 색상
export const riskLevelConfig = {
  low: { color: '#10B981', label: '낮음', range: [0, 30] },
  medium: { color: '#F59E0B', label: '보통', range: [31, 60] },
  high: { color: '#EF4444', label: '높음', range: [61, 100] },
} as const

// 투자등급별 색상 (4등급 체계 - 2026-01-28 개편)
export const gradeConfig: Record<InvestmentGrade, { color: string; label: string }> = {
  LOW_RISK: { color: '#10B981', label: '저위험' },     // 초록 (0-19점)
  RISK: { color: '#FBBF24', label: '위험' },           // 노랑 (20-34점)
  MEDIUM_RISK: { color: '#F97316', label: '중위험' },  // 주황 (35-49점)
  HIGH_RISK: { color: '#EF4444', label: '고위험' },    // 빨강 (50점+)
}

// 하위 호환성을 위한 레거시 등급 색상 (DB 마이그레이션 전 지원)
export const legacyGradeConfig: Record<LegacyInvestmentGrade, { color: string; label: string }> = {
  AAA: { color: '#059669', label: '최우량' },
  AA: { color: '#10B981', label: '우량' },
  A: { color: '#34D399', label: '양호' },
  BBB: { color: '#FBBF24', label: '적정' },
  BB: { color: '#F59E0B', label: '투기' },
  B: { color: '#F97316', label: '고위험' },
  CCC: { color: '#EF4444', label: '매우위험' },
  CC: { color: '#DC2626', label: '극히위험' },
  C: { color: '#B91C1C', label: '최고위험' },
  D: { color: '#991B1B', label: '부도' },
}

// 등급 변환 유틸리티 (레거시 → 신규)
export function convertLegacyGrade(legacy: LegacyInvestmentGrade | string): InvestmentGrade {
  const mapping: Record<string, InvestmentGrade> = {
    'AAA': 'LOW_RISK', 'AA': 'LOW_RISK', 'A': 'RISK',
    'BBB': 'RISK', 'BB': 'MEDIUM_RISK', 'B': 'MEDIUM_RISK',
    'CCC': 'HIGH_RISK', 'CC': 'HIGH_RISK', 'C': 'HIGH_RISK', 'D': 'HIGH_RISK',
    // 신규 등급은 그대로
    'LOW_RISK': 'LOW_RISK', 'RISK': 'RISK', 'MEDIUM_RISK': 'MEDIUM_RISK', 'HIGH_RISK': 'HIGH_RISK',
  }
  return mapping[legacy] || 'RISK'
}

// 등급 설정 가져오기 (레거시/신규 모두 지원)
export function getGradeConfig(grade: string): { color: string; label: string } {
  // 신규 등급인지 확인
  if (grade in gradeConfig) {
    return gradeConfig[grade as InvestmentGrade]
  }
  // 레거시 등급이면 변환
  if (grade in legacyGradeConfig) {
    const newGrade = convertLegacyGrade(grade)
    return gradeConfig[newGrade]
  }
  // 기본값
  return { color: '#6B7280', label: '미평가' }
}

// 리스크 점수로 레벨 판정
export function getRiskLevel(score: number): 'low' | 'medium' | 'high' {
  if (score <= 30) return 'low'
  if (score <= 60) return 'medium'
  return 'high'
}

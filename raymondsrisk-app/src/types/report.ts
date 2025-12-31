// 리스크 점수 데이터
export interface RiskScore {
  total: number // 0-100
  cbRisk: number // CB 관련 리스크
  officerRisk: number // 임원 관련 리스크
  financialRisk: number // 재무 관련 리스크
  networkRisk: number // 네트워크 관련 리스크
}

// 투자등급
export type InvestmentGrade = 'AAA' | 'AA' | 'A' | 'BBB' | 'BB' | 'B' | 'CCC' | 'CC' | 'C' | 'D'

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
  issue_round?: string
}

// CB 인수인 데이터
export interface CBSubscriber {
  id: string
  name: string
  amount: number
  ratio: number
  type: 'institution' | 'individual' | 'related'
  issue_rounds?: string[]
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
  quarter?: string | null
  revenue: number
  operating_profit: number
  net_income: number
  total_assets: number
  total_liabilities: number
  equity: number
  debt_ratio?: number
  current_ratio?: number
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

// 심각도별 설정
export const severityConfig: Record<RiskSignalSeverity, { color: string; label: string }> = {
  HIGH: { color: '#EF4444', label: '높음' },
  MEDIUM: { color: '#F59E0B', label: '보통' },
  LOW: { color: '#6B7280', label: '낮음' },
}

// 리스크 점수로 레벨 판정
export function getRiskLevel(score: number): 'low' | 'medium' | 'high' {
  if (score <= 30) return 'low'
  if (score <= 60) return 'medium'
  return 'high'
}

import type {
  RiskScore,
  InvestmentGrade,
  CBIssuance,
  CBSubscriber,
  Officer,
  FinancialStatement,
  Shareholder,
  Affiliate,
  RiskSignal,
  CompanyReportData,
} from '../types/report'

// ============================================================================
// UUID 생성 함수 (React Native WebView 호환)
// crypto.randomUUID()가 지원되지 않는 환경을 위한 폴리필
// ============================================================================
function generateUUID(): string {
  // crypto.randomUUID가 있으면 사용
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  // 폴리필: Math.random 기반 UUID v4
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

// ============================================================================
// 백엔드 API 응답 타입
// ============================================================================

interface ApiCompanyBasicInfo {
  id: string
  corp_code: string
  name: string
  ticker?: string
}

interface ApiRiskScoreInfo {
  total_score: number
  investment_grade: string
  raymondsrisk_score: number
  human_risk_score: number
  cb_risk_score: number
  financial_health_score: number
}

interface ApiRiskSignalInfo {
  severity: string
  title: string
  description: string
}

interface ApiCBInfo {
  issue_date: string | null
  issue_amount_billion: number
  conversion_price: number | null
  maturity_date: string | null
  bond_name: string | null
}

interface ApiCBSubscriberInfo {
  subscriber_name: string
  subscription_amount_billion: number
  bond_name: string | null
}

interface ApiOfficerInfo {
  name: string
  position: string
  term_start: string | null
  term_end: string | null
  is_current: boolean
}

interface ApiFinancialInfo {
  fiscal_year: number
  quarter: string | null
  total_assets_billion: number | null
  total_liabilities_billion: number | null
  total_equity_billion: number | null
  revenue_billion: number | null
  operating_profit_billion: number | null
  net_income_billion: number | null
}

interface ApiShareholderInfo {
  shareholder_name: string
  share_ratio: number | null
  is_largest: boolean
}

interface ApiAffiliateInfo {
  affiliate_name: string
  relationship_type: string
}

interface ApiCompanyFullReport {
  basic_info: ApiCompanyBasicInfo
  risk_score: ApiRiskScoreInfo | null
  risk_signals: ApiRiskSignalInfo[]
  convertible_bonds: ApiCBInfo[]
  cb_subscribers: ApiCBSubscriberInfo[]
  officers: ApiOfficerInfo[]
  financials: ApiFinancialInfo[]
  shareholders: ApiShareholderInfo[]
  affiliates: ApiAffiliateInfo[]
  summary: Record<string, unknown>
}

// ============================================================================
// 변환 함수
// ============================================================================

function mapRiskScore(apiScore: ApiRiskScoreInfo): RiskScore {
  return {
    total: Math.round(apiScore.total_score),
    cbRisk: Math.round(apiScore.cb_risk_score),
    officerRisk: Math.round(apiScore.human_risk_score),
    financialRisk: Math.round(apiScore.financial_health_score),
    networkRisk: Math.round(apiScore.raymondsrisk_score),
  }
}

function mapInvestmentGrade(grade: string): InvestmentGrade {
  const validGrades: InvestmentGrade[] = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC', 'CC', 'C', 'D']
  return validGrades.includes(grade as InvestmentGrade) ? (grade as InvestmentGrade) : 'BB'
}

function extractIssueRound(bondName: string | null): string | undefined {
  if (!bondName) return undefined
  const match = bondName.match(/제(\d+)회/)
  return match ? `제${match[1]}회` : undefined
}

function mapCBIssuance(apiCB: ApiCBInfo): CBIssuance {
  return {
    id: generateUUID(),
    issue_date: apiCB.issue_date || '-',
    amount: Math.round(apiCB.issue_amount_billion * 100000000),
    conversion_price: apiCB.conversion_price || 0,
    maturity_date: apiCB.maturity_date || '-',
    coupon_rate: 0,
    status: 'active',
    issue_round: extractIssueRound(apiCB.bond_name),
  }
}

// CB 발행 회차별 그룹핑
function aggregateCBIssuances(cbIssuances: CBIssuance[]): CBIssuance[] {
  const roundMap = new Map<string, {
    earliestDate: string
    totalAmount: number
    latestConversionPrice: number
    maturityDate: string
  }>()

  for (const cb of cbIssuances) {
    const round = cb.issue_round || '기타'
    const existing = roundMap.get(round)

    if (existing) {
      if (cb.issue_date !== '-' && (existing.earliestDate === '-' || cb.issue_date < existing.earliestDate)) {
        existing.earliestDate = cb.issue_date
      }
      existing.totalAmount = Math.max(existing.totalAmount, cb.amount)
      if (cb.maturity_date !== '-') existing.maturityDate = cb.maturity_date
    } else {
      roundMap.set(round, {
        earliestDate: cb.issue_date,
        totalAmount: cb.amount,
        latestConversionPrice: cb.conversion_price,
        maturityDate: cb.maturity_date,
      })
    }
  }

  const result: CBIssuance[] = []
  for (const [round, data] of roundMap) {
    result.push({
      id: generateUUID(),
      issue_round: round,
      issue_date: data.earliestDate,
      amount: data.totalAmount,
      conversion_price: data.latestConversionPrice,
      maturity_date: data.maturityDate,
      coupon_rate: 0,
      status: 'active',
    })
  }

  return result.sort((a, b) => {
    const numA = parseInt(a.issue_round?.match(/\d+/)?.[0] || '0')
    const numB = parseInt(b.issue_round?.match(/\d+/)?.[0] || '0')
    return numB - numA
  })
}

interface CBSubscriberWithRound extends CBSubscriber {
  issue_round?: string
}

function mapCBSubscriber(apiSub: ApiCBSubscriberInfo, totalAmount: number): CBSubscriberWithRound {
  const amount = Math.round(apiSub.subscription_amount_billion * 100000000)
  return {
    id: generateUUID(),
    name: apiSub.subscriber_name,
    amount,
    ratio: totalAmount > 0 ? Math.round((amount / totalAmount) * 1000) / 10 : 0,
    type: apiSub.subscriber_name.includes('(주)') || apiSub.subscriber_name.includes('주식회사')
      ? 'institution' : 'individual',
    issue_round: extractIssueRound(apiSub.bond_name),
  }
}

function aggregateCBSubscribers(subscribers: CBSubscriberWithRound[], totalAmount: number): CBSubscriber[] {
  const subscriberMap = new Map<string, CBSubscriber & { roundSet: Set<string> }>()

  for (const sub of subscribers) {
    const existing = subscriberMap.get(sub.name)
    if (existing) {
      existing.amount += sub.amount
      existing.ratio = totalAmount > 0 ? Math.round((existing.amount / totalAmount) * 1000) / 10 : 0
      if (sub.issue_round) existing.roundSet.add(sub.issue_round)
    } else {
      const roundSet = new Set<string>()
      if (sub.issue_round) roundSet.add(sub.issue_round)
      subscriberMap.set(sub.name, { ...sub, roundSet, issue_rounds: [] })
    }
  }

  return Array.from(subscriberMap.values())
    .map(({ roundSet, ...sub }) => ({
      ...sub,
      issue_rounds: Array.from(roundSet).sort((a, b) => {
        const numA = parseInt(a.match(/\d+/)?.[0] || '0')
        const numB = parseInt(b.match(/\d+/)?.[0] || '0')
        return numA - numB
      }),
    }))
    .sort((a, b) => b.amount - a.amount)
}

function mapOfficer(apiOfficer: ApiOfficerInfo): Officer {
  return {
    id: generateUUID(),
    name: apiOfficer.name,
    position: apiOfficer.position || '-',
    tenure_start: apiOfficer.term_start || undefined,
    tenure_end: apiOfficer.term_end || undefined,
    is_current: apiOfficer.is_current,
  }
}

function mapFinancial(apiFin: ApiFinancialInfo): FinancialStatement {
  const total_assets = Math.round((apiFin.total_assets_billion || 0) * 100000000)
  const total_liabilities = Math.round((apiFin.total_liabilities_billion || 0) * 100000000)
  const equity = Math.round((apiFin.total_equity_billion || 0) * 100000000)

  return {
    year: apiFin.fiscal_year,
    quarter: apiFin.quarter,
    revenue: Math.round((apiFin.revenue_billion || 0) * 100000000),
    operating_profit: Math.round((apiFin.operating_profit_billion || 0) * 100000000),
    net_income: Math.round((apiFin.net_income_billion || 0) * 100000000),
    total_assets,
    total_liabilities,
    equity,
    debt_ratio: equity > 0 ? (total_liabilities / equity) * 100 : undefined,
  }
}

function mapShareholder(apiSh: ApiShareholderInfo): Shareholder {
  return {
    id: generateUUID(),
    name: apiSh.shareholder_name,
    shares: 0,
    percentage: apiSh.share_ratio || 0,
    type: apiSh.is_largest ? 'major' : 'general',
  }
}

function mapAffiliate(apiAff: ApiAffiliateInfo): Affiliate {
  const relationMap: Record<string, Affiliate['relation']> = {
    'SUBSIDIARY': 'subsidiary',
    'ASSOCIATE': 'associate',
    'AFFILIATE': 'associate',
    'GRANDCHILD': 'grandchild',
  }
  return {
    id: generateUUID(),
    name: apiAff.affiliate_name,
    relation: relationMap[apiAff.relationship_type] || 'associate',
    percentage: 0,
    industry: '-',
  }
}

function mapRiskSignal(apiSignal: ApiRiskSignalInfo): RiskSignal {
  const severityMap: Record<string, 'HIGH' | 'MEDIUM' | 'LOW'> = {
    'HIGH': 'HIGH', 'MEDIUM': 'MEDIUM', 'LOW': 'LOW',
    'CRITICAL': 'HIGH', 'WARNING': 'MEDIUM', 'INFO': 'LOW',
  }
  return {
    id: generateUUID(),
    pattern_name: apiSignal.title,
    severity: severityMap[apiSignal.severity] || 'MEDIUM',
    description: apiSignal.description,
  }
}

function generateWarnings(report: ApiCompanyFullReport): string[] {
  const warnings: string[] = []
  const summary = report.summary as Record<string, unknown>

  if (summary.cb_total_count && (summary.cb_total_count as number) >= 3) {
    warnings.push(`CB 발행 빈도가 높습니다 (총 ${summary.cb_total_count}회)`)
  }
  if (summary.high_risk_signals && (summary.high_risk_signals as number) > 0) {
    warnings.push(`고위험 신호 ${summary.high_risk_signals}건 탐지`)
  }
  if (summary.has_financial_loss) {
    warnings.push('최근 영업손실 발생')
  }

  report.risk_signals.slice(0, 3).forEach(signal => {
    if (signal.severity === 'HIGH') warnings.push(signal.title)
  })

  return warnings.slice(0, 5)
}

// ============================================================================
// API 함수
// ============================================================================

/**
 * 회사명으로 종합 보고서 조회
 * fetch를 직접 사용 (React Native WebView 호환성 개선)
 */
export async function getCompanyReportByName(companyName: string): Promise<CompanyReportData | null> {
  const API_BASE = import.meta.env.VITE_API_URL || 'https://raymontology-production.up.railway.app'
  const url = `${API_BASE}/api/report/name/${encodeURIComponent(companyName)}`

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`API HTTP ${response.status}`)
    }

    const report: ApiCompanyFullReport = await response.json()

    const totalCBAmount = report.convertible_bonds.reduce(
      (sum, cb) => sum + cb.issue_amount_billion * 100000000, 0
    )

    const defaultRiskScore: RiskScore = {
      total: 50, cbRisk: 50, officerRisk: 50, financialRisk: 50, networkRisk: 50,
    }

    const result = {
      companyId: report.basic_info.id,
      corpCode: report.basic_info.corp_code,
      ticker: report.basic_info.ticker || '',
      companyName: report.basic_info.name,
      riskScore: report.risk_score ? mapRiskScore(report.risk_score) : defaultRiskScore,
      investmentGrade: report.risk_score ? mapInvestmentGrade(report.risk_score.investment_grade) : 'BB',
      cbIssuances: aggregateCBIssuances(report.convertible_bonds.map(mapCBIssuance)),
      cbSubscribers: aggregateCBSubscribers(
        report.cb_subscribers.map(sub => mapCBSubscriber(sub, totalCBAmount)),
        totalCBAmount
      ),
      officers: report.officers.map(mapOfficer),
      financials: report.financials.map(mapFinancial),
      shareholders: report.shareholders.map(mapShareholder),
      affiliates: report.affiliates.map(mapAffiliate),
      riskSignals: report.risk_signals.map(mapRiskSignal),
      warnings: generateWarnings(report),
      calculatedAt: new Date().toISOString(),
    }
    return result
  } catch (error) {
    const errMsg = error instanceof Error ? error.message : String(error)
    throw new Error(`Report API 실패: ${errMsg}`)
  }
}

/**
 * 회사 ID로 회사 기본 정보 조회
 * fetch를 직접 사용 (React Native WebView 호환성 개선)
 */
export async function getCompanyDetail(companyId: string): Promise<{ id: string; name: string; _error?: string } | null> {
  const API_BASE = import.meta.env.VITE_API_URL || 'https://raymontology-production.up.railway.app'
  const url = `${API_BASE}/api/companies/${companyId}`

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      return { id: '', name: '', _error: `getCompanyDetail: HTTP ${response.status}` }
    }

    const data = await response.json()
    return data as { id: string; name: string }
  } catch (err) {
    const errMsg = err instanceof Error ? err.message : String(err)
    return { id: '', name: '', _error: `getCompanyDetail: ${errMsg}` }
  }
}

/**
 * 회사 ID로 종합 보고서 조회
 * @returns CompanyReportData 또는 에러 정보가 포함된 객체
 */
export async function getCompanyReport(companyId: string): Promise<CompanyReportData | { _error: string } | null> {
  const companyDetail = await getCompanyDetail(companyId)

  // 에러가 있는 경우
  if (companyDetail && '_error' in companyDetail && companyDetail._error) {
    return { _error: companyDetail._error }
  }

  if (companyDetail && companyDetail.name) {
    try {
      const result = await getCompanyReportByName(companyDetail.name)
      if (!result) {
        return { _error: `getCompanyReportByName(${companyDetail.name}) returned null` }
      }
      return result
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err)
      return { _error: `getCompanyReportByName 예외: ${errMsg}` }
    }
  }

  return { _error: 'companyDetail is null or has no name' }
}

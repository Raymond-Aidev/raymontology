import apiClient from './client'
import type {
  RiskScore,
  InvestmentGrade,
  CBIssuance,
  CBSubscriber,
  Officer,
  FinancialStatement,
  Shareholder,
  RiskSignal,
  Affiliate,
} from '../types/report'

// ============================================================================
// 백엔드 API 응답 타입 (/api/report/name/{company_name})
// ============================================================================

interface ApiCompanyBasicInfo {
  id: string
  corp_code: string
  name: string
  market?: string | null  // KOSPI, KOSDAQ, KONEX, ETF
  company_type?: string | null  // NORMAL, SPAC, REIT, ETF
  trading_status?: string | null  // NORMAL, SUSPENDED, TRADING_HALT
}

interface ApiRiskScoreInfo {
  analysis_year: number
  analysis_quarter: number | null
  total_score: number
  risk_level: string
  investment_grade: string
  raymondsrisk_score: number
  human_risk_score: number
  cb_risk_score: number
  financial_health_score: number
}

interface ApiRiskSignalInfo {
  pattern_type: string
  severity: string
  risk_score: number
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
  issue_date: string | null
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
  report_year: number | null
}

interface ApiAffiliateInfo {
  affiliate_name: string
  relationship_type: string
}

interface ApiCompanyFullReport {
  basic_info: ApiCompanyBasicInfo
  disclosure_count: number
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
// 프론트엔드 타입
// ============================================================================

export interface CompanyReportData {
  companyId: string
  companyName: string
  market?: string  // KOSPI, KOSDAQ, KONEX, ETF
  companyType?: string  // NORMAL, SPAC, REIT, ETF
  tradingStatus?: string  // NORMAL, SUSPENDED, TRADING_HALT
  riskScore: RiskScore
  investmentGrade: InvestmentGrade
  cbIssuances: CBIssuance[]
  cbSubscribers: CBSubscriber[]
  officers: Officer[]
  financials: FinancialStatement[]
  shareholders: Shareholder[]
  affiliates: Affiliate[]
  riskSignals: RiskSignal[]
  warnings: string[]
  calculatedAt: string
}

// ============================================================================
// 타입 변환 함수
// ============================================================================

function mapRiskScoreToFrontend(apiScore: ApiRiskScoreInfo): RiskScore {
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

// bond_name에서 회차 추출 (예: "제33회 무기명식..." → "제33회")
function extractIssueRound(bondName: string | null): string | undefined {
  if (!bondName) return undefined
  const match = bondName.match(/제(\d+)회/)
  if (match) {
    return `제${match[1]}회`
  }
  return undefined
}

function mapCBIssuanceToFrontend(apiCB: ApiCBInfo): CBIssuance {
  return {
    id: crypto.randomUUID(),
    issue_date: apiCB.issue_date || '-',
    amount: Math.round(apiCB.issue_amount_billion * 100000000), // 억원 → 원
    conversion_price: apiCB.conversion_price || 0,
    maturity_date: apiCB.maturity_date || '-',
    coupon_rate: 0, // API에서 제공하지 않음
    status: 'active',
    issue_round: extractIssueRound(apiCB.bond_name),
  }
}

// CB 발행 데이터 회차별 그룹핑 (같은 회차의 여러 레코드를 하나로 합침)
function aggregateCBIssuances(cbIssuances: CBIssuance[]): CBIssuance[] {
  const roundMap = new Map<string, {
    rounds: CBIssuance[]
    earliestDate: string   // 가장 오래된 날짜 = 실제 발행일
    latestDate: string     // 가장 최근 날짜 = 전환가격 조정일
    totalAmount: number
    latestConversionPrice: number
    maturityDate: string
  }>()

  for (const cb of cbIssuances) {
    const round = cb.issue_round || '기타'
    const existing = roundMap.get(round)

    if (existing) {
      existing.rounds.push(cb)
      // 가장 오래된 날짜를 실제 발행일로 사용
      if (cb.issue_date !== '-') {
        if (existing.earliestDate === '-' || cb.issue_date < existing.earliestDate) {
          existing.earliestDate = cb.issue_date
        }
        if (existing.latestDate === '-' || cb.issue_date > existing.latestDate) {
          existing.latestDate = cb.issue_date
          existing.latestConversionPrice = cb.conversion_price
        }
      }
      // 금액은 합산하지 않음 (같은 회차의 중복 레코드이므로 최대값 사용)
      existing.totalAmount = Math.max(existing.totalAmount, cb.amount)
      // 만기일 (있으면 사용)
      if (cb.maturity_date !== '-') {
        existing.maturityDate = cb.maturity_date
      }
    } else {
      roundMap.set(round, {
        rounds: [cb],
        earliestDate: cb.issue_date,
        latestDate: cb.issue_date,
        totalAmount: cb.amount,
        latestConversionPrice: cb.conversion_price,
        maturityDate: cb.maturity_date,
      })
    }
  }

  // 회차별로 하나의 레코드 생성
  const result: CBIssuance[] = []
  for (const [round, data] of roundMap) {
    result.push({
      id: crypto.randomUUID(),
      issue_round: round,
      issue_date: data.earliestDate,  // 실제 발행일 사용
      amount: data.totalAmount,
      conversion_price: data.latestConversionPrice,  // 최신 전환가격 사용
      maturity_date: data.maturityDate,
      coupon_rate: 0,
      status: 'active',
    })
  }

  // 회차 숫자로 정렬 (내림차순)
  return result.sort((a, b) => {
    const numA = parseInt(a.issue_round?.match(/\d+/)?.[0] || '0')
    const numB = parseInt(b.issue_round?.match(/\d+/)?.[0] || '0')
    return numB - numA
  })
}

// 임시 타입 (회차 정보 포함)
interface CBSubscriberWithRound extends CBSubscriber {
  issue_round?: string
}

function mapCBSubscriberToFrontend(apiSub: ApiCBSubscriberInfo, totalAmount: number): CBSubscriberWithRound {
  const amount = Math.round(apiSub.subscription_amount_billion * 100000000)
  return {
    id: crypto.randomUUID(),
    name: apiSub.subscriber_name,
    amount,
    ratio: totalAmount > 0 ? Math.round((amount / totalAmount) * 1000) / 10 : 0,
    type: apiSub.subscriber_name.includes('(주)') || apiSub.subscriber_name.includes('주식회사')
      ? 'institution'
      : 'individual',
    issue_round: extractIssueRound(apiSub.bond_name),
  }
}

// 인수인 중복 제거 및 금액 합산 + 회차 목록 수집
function aggregateCBSubscribers(subscribers: CBSubscriberWithRound[], totalAmount: number): CBSubscriber[] {
  const subscriberMap = new Map<string, CBSubscriber & { roundSet: Set<string> }>()

  for (const sub of subscribers) {
    const existing = subscriberMap.get(sub.name)
    if (existing) {
      // 금액 합산
      existing.amount += sub.amount
      // 비율 재계산
      existing.ratio = totalAmount > 0 ? Math.round((existing.amount / totalAmount) * 1000) / 10 : 0
      // 회차 추가 (중복 제거)
      if (sub.issue_round) {
        existing.roundSet.add(sub.issue_round)
      }
    } else {
      const roundSet = new Set<string>()
      if (sub.issue_round) {
        roundSet.add(sub.issue_round)
      }
      subscriberMap.set(sub.name, { ...sub, roundSet, issue_rounds: [] })
    }
  }

  // 회차 목록을 배열로 변환하고 정렬
  const result: CBSubscriber[] = Array.from(subscriberMap.values()).map(({ roundSet, ...sub }) => ({
    ...sub,
    issue_rounds: Array.from(roundSet).sort((a, b) => {
      // 숫자 추출하여 정렬 (제45회 → 45)
      const numA = parseInt(a.match(/\d+/)?.[0] || '0')
      const numB = parseInt(b.match(/\d+/)?.[0] || '0')
      return numA - numB
    }),
  }))

  // 인수금액 높은 순으로 정렬
  return result.sort((a, b) => b.amount - a.amount)
}

function mapOfficerToFrontend(apiOfficer: ApiOfficerInfo): Officer {
  return {
    id: crypto.randomUUID(),
    name: apiOfficer.name,
    position: apiOfficer.position || '-',
    tenure_start: apiOfficer.term_start || undefined,
    tenure_end: apiOfficer.term_end || undefined,
    is_current: apiOfficer.is_current,  // 백엔드에서 최신 보고서 기준 재직 여부 판단
  }
}

function mapFinancialToFrontend(apiFin: ApiFinancialInfo): FinancialStatement {
  const total_assets = Math.round((apiFin.total_assets_billion || 0) * 100000000)
  const total_liabilities = Math.round((apiFin.total_liabilities_billion || 0) * 100000000)
  const equity = Math.round((apiFin.total_equity_billion || 0) * 100000000)

  // 부채비율 계산: (총부채 / 자기자본) * 100
  const debt_ratio = equity > 0 ? (total_liabilities / equity) * 100 : undefined

  return {
    year: apiFin.fiscal_year,
    quarter: apiFin.quarter,
    revenue: Math.round((apiFin.revenue_billion || 0) * 100000000),
    operating_profit: Math.round((apiFin.operating_profit_billion || 0) * 100000000),
    net_income: Math.round((apiFin.net_income_billion || 0) * 100000000),
    total_assets,
    total_liabilities,
    equity,
    debt_ratio,
  }
}

function mapShareholderToFrontend(apiSh: ApiShareholderInfo): Shareholder {
  return {
    id: crypto.randomUUID(),
    name: apiSh.shareholder_name,
    shares: 0, // API에서 주식 수는 제공하지 않음
    percentage: apiSh.share_ratio || 0,
    type: apiSh.is_largest ? 'major' : 'general',
  }
}

function mapAffiliateToFrontend(apiAff: ApiAffiliateInfo): Affiliate {
  const relationMap: Record<string, Affiliate['relation']> = {
    'SUBSIDIARY': 'subsidiary',
    'ASSOCIATE': 'associate',
    'AFFILIATE': 'associate',
    'GRANDCHILD': 'grandchild',
  }
  return {
    id: crypto.randomUUID(),
    name: apiAff.affiliate_name,
    relation: relationMap[apiAff.relationship_type] || 'associate',
    percentage: 0,
    industry: '-',
  }
}

function mapRiskSignalToFrontend(apiSignal: ApiRiskSignalInfo): RiskSignal {
  const severityMap: Record<string, 'HIGH' | 'MEDIUM' | 'LOW'> = {
    'HIGH': 'HIGH',
    'MEDIUM': 'MEDIUM',
    'LOW': 'LOW',
    'CRITICAL': 'HIGH',
    'WARNING': 'MEDIUM',
    'INFO': 'LOW',
  }
  return {
    id: crypto.randomUUID(),
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

  // 리스크 신호에서 추가 경고 추출
  report.risk_signals.slice(0, 3).forEach(signal => {
    if (signal.severity === 'HIGH') {
      warnings.push(signal.title)
    }
  })

  return warnings.slice(0, 5) // 최대 5개
}

// ============================================================================
// API 함수
// ============================================================================

/**
 * 회사 ID로 회사 기본 정보 조회
 */
export async function getCompanyDetail(companyId: string): Promise<{ id: string; name: string; corp_code: string } | null> {
  try {
    const response = await apiClient.get<{ id: string; name: string; ticker: string | null }>(`/api/companies/${companyId}`)
    return {
      id: response.data.id,
      name: response.data.name,
      corp_code: response.data.ticker || '',
    }
  } catch (error) {
    console.warn('Company API 호출 실패:', error)
    return null
  }
}

/**
 * 회사명으로 종합 보고서 조회 (백엔드 /api/report/name/{company_name})
 */
export async function getCompanyReportByName(companyName: string): Promise<CompanyReportData | null> {
  try {
    const response = await apiClient.get<ApiCompanyFullReport>(`/api/report/name/${encodeURIComponent(companyName)}`)
    const report = response.data

    // CB 총 발행액 계산 (인수인 비율 계산용)
    const totalCBAmount = report.convertible_bonds.reduce(
      (sum, cb) => sum + cb.issue_amount_billion * 100000000, 0
    )

    // 기본 리스크 점수 (API 응답이 없을 경우)
    const defaultRiskScore: RiskScore = {
      total: 50,
      cbRisk: 50,
      officerRisk: 50,
      financialRisk: 50,
      networkRisk: 50,
    }

    return {
      companyId: report.basic_info.id,
      companyName: report.basic_info.name,
      market: report.basic_info.market || undefined,
      companyType: report.basic_info.company_type || undefined,
      tradingStatus: report.basic_info.trading_status || undefined,
      riskScore: report.risk_score ? mapRiskScoreToFrontend(report.risk_score) : defaultRiskScore,
      investmentGrade: report.risk_score ? mapInvestmentGrade(report.risk_score.investment_grade) : 'BB',
      cbIssuances: aggregateCBIssuances(report.convertible_bonds.map(mapCBIssuanceToFrontend)),
      cbSubscribers: aggregateCBSubscribers(
        report.cb_subscribers.map(sub => mapCBSubscriberToFrontend(sub, totalCBAmount)),
        totalCBAmount
      ),
      officers: report.officers.map(mapOfficerToFrontend),
      financials: report.financials.map(mapFinancialToFrontend),
      shareholders: report.shareholders.map(mapShareholderToFrontend),
      affiliates: report.affiliates.map(mapAffiliateToFrontend),
      riskSignals: report.risk_signals.map(mapRiskSignalToFrontend),
      warnings: generateWarnings(report),
      calculatedAt: new Date().toISOString(),
    }
  } catch (error) {
    console.warn('Report API by name 호출 실패:', error)
    return null
  }
}

/**
 * 회사 ID로 종합 보고서 조회
 * 1. 회사 ID로 회사명 조회
 * 2. 회사명으로 종합 보고서 조회
 */
export async function getCompanyReport(companyId: string): Promise<CompanyReportData> {
  try {
    // 1. 회사 ID로 회사 기본 정보 조회
    const companyDetail = await getCompanyDetail(companyId)

    if (companyDetail) {
      // 2. 회사명으로 종합 보고서 조회
      const report = await getCompanyReportByName(companyDetail.name)
      if (report) {
        return report
      }
    }

    // API 실패 시 빈 데이터 반환 (더미 데이터 사용 안 함)
    console.warn('Report API 호출 실패, 빈 데이터 반환')
    return {
      companyId,
      companyName: companyDetail?.name || '회사',
      riskScore: { total: 0, cbRisk: 0, officerRisk: 0, financialRisk: 0, networkRisk: 0 },
      investmentGrade: 'BB',
      cbIssuances: [],
      cbSubscribers: [],
      officers: [],
      financials: [],
      shareholders: [],
      affiliates: [],
      riskSignals: [],
      warnings: [],
      calculatedAt: new Date().toISOString(),
    }
  } catch (error) {
    console.warn('Report API 호출 실패:', error)
    return {
      companyId,
      companyName: '회사',
      riskScore: { total: 0, cbRisk: 0, officerRisk: 0, financialRisk: 0, networkRisk: 0 },
      investmentGrade: 'BB',
      cbIssuances: [],
      cbSubscribers: [],
      officers: [],
      financials: [],
      shareholders: [],
      affiliates: [],
      riskSignals: [],
      warnings: [],
      calculatedAt: new Date().toISOString(),
    }
  }
}

// ============================================================================
// 개별 데이터 API (필요 시 사용)
// ============================================================================

/**
 * 회사 CB 발행 목록 조회
 */
export async function getCompanyConvertibleBonds(companyId: string): Promise<CBIssuance[]> {
  try {
    const response = await apiClient.get<Array<{
      id: string
      issue_date: string | null
      issue_amount: number | null
      conversion_price: number | null
      maturity_date: string | null
      interest_rate: number | null
      status: string | null
    }>>(`/api/convertible-bonds/company/${companyId}`)

    return response.data.map(cb => ({
      id: cb.id,
      issue_date: cb.issue_date || '-',
      amount: cb.issue_amount || 0,
      conversion_price: cb.conversion_price || 0,
      maturity_date: cb.maturity_date || '-',
      coupon_rate: cb.interest_rate || 0,
      status: 'active' as const,
    }))
  } catch (error) {
    console.warn('CB 발행 API 호출 실패:', error)
    return []
  }
}

/**
 * 회사 임원 목록 조회
 */
export async function getCompanyOfficers(companyId: string): Promise<Officer[]> {
  try {
    const response = await apiClient.get<Array<{
      id: string
      name: string
      position: string | null
      created_at: string
    }>>(`/api/officers/company/${companyId}`)

    return response.data.map(officer => ({
      id: officer.id,
      name: officer.name,
      position: officer.position || '-',
      tenure_start: officer.created_at.split('T')[0],
      is_current: true,
    }))
  } catch (error) {
    console.warn('임원 API 호출 실패:', error)
    return []
  }
}

/**
 * 회사 재무제표 조회
 */
export async function getCompanyFinancials(companyId: string): Promise<FinancialStatement[]> {
  try {
    const response = await apiClient.get<Array<{
      fiscal_year: number
      quarter: string | null
      total_assets: number | null
      total_liabilities: number | null
      total_equity: number | null
      revenue: number | null
      operating_profit: number | null
      net_income: number | null
    }>>(`/api/financials/companies/${companyId}/statements`, {
      params: { limit: 10 }
    })

    // 연도별로 그룹화하여 최신 데이터만 반환
    const byYear = new Map<number, typeof response.data[0]>()
    for (const stmt of response.data) {
      if (!byYear.has(stmt.fiscal_year) || stmt.quarter === 'Q4' || !stmt.quarter) {
        byYear.set(stmt.fiscal_year, stmt)
      }
    }

    return Array.from(byYear.values())
      .sort((a, b) => b.fiscal_year - a.fiscal_year)
      .map(stmt => ({
        year: stmt.fiscal_year,
        revenue: stmt.revenue || 0,
        operating_profit: stmt.operating_profit || 0,
        net_income: stmt.net_income || 0,
        total_assets: stmt.total_assets || 0,
        total_liabilities: stmt.total_liabilities || 0,
        equity: stmt.total_equity || 0,
      }))
  } catch (error) {
    console.warn('재무제표 API 호출 실패:', error)
    return []
  }
}

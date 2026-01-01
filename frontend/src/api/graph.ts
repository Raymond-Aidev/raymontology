import apiClient from './client'
import type { GraphData, GraphNode, GraphLink } from '../types/graph'

// 임원 경력 타입
export interface OfficerCareer {
  company_name: string
  company_id?: string | null
  position: string
  start_date?: string | null
  end_date?: string | null
  is_current: boolean
  is_listed?: boolean  // 상장회사 여부
  source: 'db' | 'disclosure'  // "db": 상장사 임원 DB, "disclosure": 공시 파일 확인
}

// 인수인 투자 이력 타입
export interface SubscriberInvestment {
  company_name: string
  company_id?: string
  cb_issue_date: string
  amount: number
}

// 백엔드 API 응답 타입
interface ApiGraphNode {
  id: string
  type: string // Company, Officer, ConvertibleBond, Subscriber
  properties: Record<string, unknown>
}

interface ApiGraphRelationship {
  id: string
  type: string // WORKS_AT, WORKED_AT, ISSUED, SUBSCRIBED, etc.
  source: string
  target: string
  properties: Record<string, unknown>
}

interface ApiGraphResponse {
  nodes: ApiGraphNode[]
  relationships: ApiGraphRelationship[]
  center?: { type: string; id: string }
}

// API 노드 타입 → 프론트 노드 타입 매핑
function mapNodeType(apiType: string): 'company' | 'officer' | 'subscriber' | 'cb' | 'shareholder' | 'affiliate' {
  switch (apiType) {
    case 'Company': return 'company'
    case 'Officer': return 'officer'
    case 'Subscriber': return 'subscriber'
    case 'ConvertibleBond': return 'cb'
    case 'Shareholder': return 'shareholder'
    case 'Affiliate': return 'affiliate'
    default: return 'company'
  }
}

// API 관계 타입 → 프론트 링크 타입 매핑
function mapLinkType(apiType: string): 'officer' | 'subscriber' | 'cb_issue' | 'affiliate' {
  switch (apiType) {
    case 'WORKS_AT':
    case 'WORKED_AT':
      return 'officer'
    case 'SUBSCRIBED':
      return 'subscriber'
    case 'ISSUED':
      return 'cb_issue'
    case 'AFFILIATED':
    case 'SUBSIDIARY':
      return 'affiliate'
    default:
      return 'affiliate'
  }
}

// bond_name에서 회차 추출 (예: "제33회 무기명식..." → "33회")
function extractCbRound(bondName: string): string {
  const match = bondName.match(/제(\d+)회/)
  if (match) {
    return `${match[1]}회`
  }
  return bondName.slice(0, 10) // fallback: 앞 10자
}

// API 응답을 프론트 GraphData로 변환
function transformApiResponse(response: ApiGraphResponse): GraphData {
  // 1. 먼저 모든 노드를 변환
  const allNodes: GraphNode[] = response.nodes.map(node => {
    // ConvertibleBond인 경우 bond_name에서 회차 추출
    let name = (node.properties.name as string) || (node.properties.corp_name as string) || node.id
    if (node.type === 'ConvertibleBond' && node.properties.bond_name) {
      name = extractCbRound(node.properties.bond_name as string)
    }

    return {
      id: node.id,
      name,
      type: mapNodeType(node.type),
      corp_code: node.properties.corp_code as string | undefined,
      risk_level: node.properties.risk_level as string | undefined,
      investment_grade: node.properties.investment_grade as string | undefined,
      position: node.properties.position as string | undefined,
      listedCareerCount: node.properties.listed_career_count as number | undefined,
      deficitCareerCount: node.properties.deficit_career_count as number | undefined,
      amount: node.properties.amount as number | undefined,
      issue_date: node.properties.issue_date as string | undefined,
      // Subscriber 법인정보
      representative_name: node.properties.representative_name as string | undefined,
      gp_name: node.properties.gp_name as string | undefined,
      largest_shareholder_name: node.properties.largest_shareholder_name as string | undefined,
    }
  })

  // 2. 동일 이름+타입 노드 중복 제거 (첫 번째 노드만 유지)
  // 단, 회사(company) 노드는 corp_code로 구분, CB는 issue_date+name으로 구분
  const nodeMap = new Map<string, GraphNode>()
  const idMapping = new Map<string, string>() // 원래 ID → 대표 ID 매핑

  allNodes.forEach(node => {
    let dedupeKey: string
    if (node.type === 'company') {
      // 회사는 corp_code로 구분 (없으면 이름)
      dedupeKey = `company:${node.corp_code || node.name}`
    } else if (node.type === 'cb') {
      // CB는 회차(name)로만 구분 - 같은 회차는 하나만 표시
      dedupeKey = `cb:${node.name}`
    } else {
      // 임원, 투자자 등은 이름+타입으로 구분
      dedupeKey = `${node.type}:${node.name}`
    }

    if (!nodeMap.has(dedupeKey)) {
      nodeMap.set(dedupeKey, node)
      idMapping.set(node.id, node.id)
    } else {
      // 중복 노드의 ID를 대표 노드 ID로 매핑
      const representativeNode = nodeMap.get(dedupeKey)!
      idMapping.set(node.id, representativeNode.id)
    }
  })

  const nodes = Array.from(nodeMap.values())

  // 3. 링크의 source/target을 대표 노드 ID로 변환하고 중복 제거
  const linkSet = new Set<string>()
  const links: GraphLink[] = []

  response.relationships.forEach(rel => {
    const source = idMapping.get(rel.source) || rel.source
    const target = idMapping.get(rel.target) || rel.target
    const linkType = mapLinkType(rel.type)

    // 같은 source-target-type 링크는 한 번만 추가
    const linkKey = `${source}:${target}:${linkType}`
    if (!linkSet.has(linkKey)) {
      linkSet.add(linkKey)
      links.push({
        source,
        target,
        type: linkType,
        label: rel.properties.label as string | undefined,
      })
    }
  })

  return { nodes, links }
}

// 날짜 범위 파라미터 타입
export interface DateRangeParams {
  date_from?: string // YYYY-MM-DD
  date_to?: string   // YYYY-MM-DD
  report_years?: number[]  // 사업보고서 연도 목록 (예: [2025], [2023, 2024, 2025])
}

// 노드 수 제한 상수
export const NODE_LIMIT = 200
export const DEFAULT_DEPTH = 2  // 관계도 기본 탐색 깊이 (2단계)

/**
 * 노드 수 제한 적용 (중요도 기준 필터링)
 * 회사 노드 우선, 그 다음 직접 연결된 노드 우선
 */
function applyNodeLimit(data: GraphData, limit: number): GraphData {
  if (data.nodes.length <= limit) {
    return data
  }

  // 노드 중요도 계산 (연결 수 기준)
  const connectionCount = new Map<string, number>()
  data.nodes.forEach(node => connectionCount.set(node.id, 0))
  data.links.forEach(link => {
    const sourceId = typeof link.source === 'string' ? link.source : link.source.id
    const targetId = typeof link.target === 'string' ? link.target : link.target.id
    connectionCount.set(sourceId, (connectionCount.get(sourceId) || 0) + 1)
    connectionCount.set(targetId, (connectionCount.get(targetId) || 0) + 1)
  })

  // 노드 정렬: 회사 > 연결 수 > 타입 순
  const sortedNodes = [...data.nodes].sort((a, b) => {
    // 회사 노드 우선
    if (a.type === 'company' && b.type !== 'company') return -1
    if (a.type !== 'company' && b.type === 'company') return 1
    // 연결 수 높은 순
    return (connectionCount.get(b.id) || 0) - (connectionCount.get(a.id) || 0)
  })

  // 상위 limit개 노드만 선택
  const limitedNodes = sortedNodes.slice(0, limit)
  const limitedNodeIds = new Set(limitedNodes.map(n => n.id))

  // 선택된 노드들 사이의 링크만 유지
  const limitedLinks = data.links.filter(link => {
    const sourceId = typeof link.source === 'string' ? link.source : link.source.id
    const targetId = typeof link.target === 'string' ? link.target : link.target.id
    return limitedNodeIds.has(sourceId) && limitedNodeIds.has(targetId)
  })

  return {
    nodes: limitedNodes,
    links: limitedLinks,
  }
}

/**
 * 회사 중심 네트워크 조회 API
 * @param companyId 회사 ID
 * @param depth 탐색 깊이 (1-3)
 *   - 1단계: 임원 + CB 회차
 *   - 2단계: 1단계 + CB 인수대상자
 *   - 3단계: 2단계 + 임원 타사 경력 + 인수자 타사 투자
 * @param limit 노드 제한 (기본 200)
 * @param dateRange 날짜 범위 (선택)
 */
export async function getCompanyNetwork(
  companyId: string,
  depth: number = DEFAULT_DEPTH,
  limit: number = NODE_LIMIT,
  dateRange?: DateRangeParams
): Promise<GraphData & { isLimited: boolean; originalCount: number }> {
  const params = {
    depth,
    limit: limit + 50, // 여유분 요청 후 클라이언트에서 필터링
    ...(dateRange?.date_from && { date_from: dateRange.date_from }),
    ...(dateRange?.date_to && { date_to: dateRange.date_to }),
    ...(dateRange?.report_years && { report_years: dateRange.report_years.join(',') }),
  }

  // 1차: Neo4j 기반 Graph API 시도
  try {
    const response = await apiClient.get<ApiGraphResponse>(`/api/graph/company/${companyId}`, { params })
    const fullData = transformApiResponse(response.data)
    const originalCount = fullData.nodes.length
    const limitedData = applyNodeLimit(fullData, limit)

    return {
      ...limitedData,
      isLimited: originalCount > limit,
      originalCount,
    }
  } catch (error) {
    console.warn('Neo4j Graph API 실패, PostgreSQL 폴백 시도:', error)
  }

  // 2차: PostgreSQL 기반 폴백 API 시도
  try {
    const response = await apiClient.get<ApiGraphResponse>(`/api/graph-fallback/company/${companyId}`, { params })
    const fullData = transformApiResponse(response.data)
    const originalCount = fullData.nodes.length
    const limitedData = applyNodeLimit(fullData, limit)

    return {
      ...limitedData,
      isLimited: originalCount > limit,
      originalCount,
    }
  } catch (fallbackError) {
    console.warn('PostgreSQL 폴백 API도 실패:', fallbackError)
    return {
      nodes: [],
      links: [],
      isLimited: false,
      originalCount: 0,
    }
  }
}

/**
 * 임원 경력 네트워크 조회 API
 * @param officerId 임원 ID
 */
export async function getOfficerCareerNetwork(officerId: string): Promise<GraphData> {
  try {
    const response = await apiClient.get<ApiGraphResponse>(`/api/graph/officer/${officerId}/career-network`)
    return transformApiResponse(response.data)
  } catch (error) {
    console.warn('Officer Career Network API 호출 실패:', error)
    return { nodes: [], links: [] }
  }
}

/**
 * CB 인수자 투자 네트워크 조회 API
 * @param subscriberId 인수자 ID
 */
export async function getSubscriberInvestmentNetwork(subscriberId: string): Promise<GraphData> {
  try {
    const response = await apiClient.get<ApiGraphResponse>(`/api/graph/subscriber/${subscriberId}/investment-network`)
    return transformApiResponse(response.data)
  } catch (error) {
    console.warn('Subscriber Investment Network API 호출 실패:', error)
    return { nodes: [], links: [] }
  }
}

// API 응답 타입 - 백엔드 실제 응답 형식
interface ApiOfficerCareerItem {
  company_name: string
  company_id?: string | null
  position: string
  start_date?: string | null
  end_date?: string | null
  is_current?: boolean
  is_listed?: boolean
  source?: 'db' | 'disclosure'
}

interface ApiOfficerCareerResponse {
  officer: {
    id: string
    type: string
    properties: Record<string, unknown>
  }
  career_history: ApiOfficerCareerItem[]
}

/**
 * 임원 경력 조회 API
 * @param officerId 임원 ID
 */
export async function fetchOfficerCareer(officerId: string): Promise<OfficerCareer[]> {
  try {
    const response = await apiClient.get<ApiOfficerCareerResponse>(`/api/graph/officer/${officerId}/career`)

    // API 응답의 career_history 배열을 프론트 타입으로 매핑
    const careerHistory = response.data.career_history || []
    return careerHistory.map(career => ({
      company_name: career.company_name,
      company_id: career.company_id,
      position: career.position,
      start_date: career.start_date || undefined,
      end_date: career.end_date || undefined,
      is_current: career.is_current ?? !career.end_date,
      is_listed: career.is_listed ?? true,
      source: career.source || 'db',
    }))
  } catch (error) {
    console.warn('Officer Career API 호출 실패:', error)
    return []
  }
}

// ============================================================================
// 인수인 투자 이력 API
// ============================================================================

// API 응답 타입 - 백엔드 실제 응답 형식
interface ApiInvestmentHistoryItem {
  company_id: string
  company_name: string
  total_amount?: number | null
  investment_count: number
  first_investment?: string | null
  latest_investment?: string | null
  cbs: Array<{
    id: string
    bond_name?: string
    issue_date?: string
    total_amount?: number | null
  }>
}

interface ApiSubscriberInvestmentResponse {
  subscriber: {
    id: string
    type: string
    properties: Record<string, unknown>
  }
  investment_history: ApiInvestmentHistoryItem[]
}

/**
 * 인수인 투자 이력 조회 API
 * @param subscriberId 인수인 ID
 */
export async function fetchSubscriberInvestments(subscriberId: string): Promise<SubscriberInvestment[]> {
  try {
    const response = await apiClient.get<ApiSubscriberInvestmentResponse>(`/api/graph/subscriber/${subscriberId}/investments`)

    // investment_history 배열을 프론트 타입으로 변환
    const investments: SubscriberInvestment[] = []
    const investmentHistory = response.data.investment_history || []

    investmentHistory.forEach(inv => {
      // 각 회사의 CB들을 개별 투자 이력으로 변환
      inv.cbs.forEach(cb => {
        investments.push({
          company_name: inv.company_name,
          company_id: inv.company_id,
          cb_issue_date: cb.issue_date || inv.latest_investment || '',
          amount: cb.total_amount || 0,
        })
      })
    })

    // 최근 순으로 정렬
    return investments.sort((a, b) => {
      if (!a.cb_issue_date) return 1
      if (!b.cb_issue_date) return -1
      return new Date(b.cb_issue_date).getTime() - new Date(a.cb_issue_date).getTime()
    })
  } catch (error) {
    console.warn('Subscriber Investments API 호출 실패:', error)
    return []
  }
}

// ============================================================================
// CB 인수자 리스트 API
// ============================================================================

// CB 인수자 타입
export interface CBSubscriberItem {
  id: string
  subscriber_name: string
  subscriber_type?: string
  subscription_amount?: number
  subscription_quantity?: number
  is_related_party: boolean
  relationship?: string
}

/**
 * CB 인수자 목록 조회 API
 * @param cbId 전환사채 ID
 */
export async function fetchCBSubscribers(cbId: string): Promise<CBSubscriberItem[]> {
  try {
    const response = await apiClient.get<CBSubscriberItem[]>(`/api/cb-subscribers/bond/${cbId}`)
    // 인수금액 높은 순으로 정렬
    return response.data.sort((a, b) => (b.subscription_amount || 0) - (a.subscription_amount || 0))
  } catch (error) {
    console.warn('CB Subscribers API 호출 실패:', error)
    return []
  }
}

// ============================================================================
// 대주주 상세 API
// ============================================================================

// 대주주 유형
export type ShareholderType = 'individual' | 'corporation' | 'institution'

// 대주주 상세 정보 타입
export interface ShareholderDetail {
  id: string
  name: string
  type: ShareholderType
  shares: number
  percentage: number
  acquisition_date?: string
  acquisition_price?: number
  current_value?: number
  profit_loss?: number
}

// 대주주 변동 이력 타입
export interface ShareholderHistory {
  date: string
  percentage: number
  change: number // 양수: 증가, 음수: 감소
  shares_changed: number
  reason?: string
}

// 대주주 관련 회사 타입
export interface ShareholderCompany {
  company_id: string
  company_name: string
  percentage: number
  shares: number
}

/**
 * 대주주 상세 정보 조회 API
 */
export async function fetchShareholderDetail(shareholderId: string): Promise<ShareholderDetail | null> {
  try {
    const response = await apiClient.get<ShareholderDetail>(`/api/graph/shareholder/${shareholderId}/detail`)
    return response.data
  } catch (error) {
    console.warn('Shareholder Detail API 호출 실패:', error)
    return null
  }
}

/**
 * 대주주 변동 이력 조회 API
 */
export async function fetchShareholderHistory(shareholderId: string): Promise<ShareholderHistory[]> {
  try {
    const response = await apiClient.get<ShareholderHistory[]>(`/api/graph/shareholder/${shareholderId}/history`)
    // 최근 순으로 정렬
    return response.data.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  } catch (error) {
    console.warn('Shareholder History API 호출 실패:', error)
    return []
  }
}

/**
 * 대주주 관련 회사 조회 API
 */
export async function fetchShareholderCompanies(shareholderId: string): Promise<ShareholderCompany[]> {
  try {
    const response = await apiClient.get<ShareholderCompany[]>(`/api/graph/shareholder/${shareholderId}/companies`)
    // 지분율 높은 순으로 정렬
    return response.data.sort((a, b) => b.percentage - a.percentage)
  } catch (error) {
    console.warn('Shareholder Companies API 호출 실패:', error)
    return []
  }
}

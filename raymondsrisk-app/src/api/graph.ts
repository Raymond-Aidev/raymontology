import apiClient from './client'
import type { GraphData, GraphNode, GraphLink } from '../types/graph'

// 백엔드 API 응답 타입
interface ApiGraphNode {
  id: string
  type: string
  properties: Record<string, unknown>
}

interface ApiGraphRelationship {
  id: string
  type: string
  source: string
  target: string
  properties: Record<string, unknown>
}

interface ApiGraphResponse {
  nodes: ApiGraphNode[]
  relationships: ApiGraphRelationship[]
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

// bond_name에서 회차 추출
function extractCbRound(bondName: string): string {
  const match = bondName.match(/제(\d+)회/)
  if (match) {
    return `${match[1]}회`
  }
  return bondName.slice(0, 10)
}

// API 응답을 프론트 GraphData로 변환
function transformApiResponse(response: ApiGraphResponse): GraphData {
  const allNodes: GraphNode[] = response.nodes.map(node => {
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
      bond_name: node.properties.bond_name as string | undefined,
      representative_name: node.properties.representative_name as string | undefined,
      gp_name: node.properties.gp_name as string | undefined,
      largest_shareholder_name: node.properties.largest_shareholder_name as string | undefined,
    }
  })

  // 노드 중복 제거
  const nodeMap = new Map<string, GraphNode>()
  const idMapping = new Map<string, string>()

  allNodes.forEach(node => {
    let dedupeKey: string
    if (node.type === 'company') {
      dedupeKey = `company:${node.corp_code || node.name}`
    } else if (node.type === 'cb') {
      dedupeKey = `cb:${node.name}`
    } else {
      dedupeKey = `${node.type}:${node.name}`
    }

    if (!nodeMap.has(dedupeKey)) {
      nodeMap.set(dedupeKey, node)
      idMapping.set(node.id, node.id)
    } else {
      const representativeNode = nodeMap.get(dedupeKey)!
      idMapping.set(node.id, representativeNode.id)
    }
  })

  const nodes = Array.from(nodeMap.values())

  // 링크 중복 제거
  const linkSet = new Set<string>()
  const links: GraphLink[] = []

  response.relationships.forEach(rel => {
    const source = idMapping.get(rel.source) || rel.source
    const target = idMapping.get(rel.target) || rel.target
    const linkType = mapLinkType(rel.type)
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

// 노드 수 제한 상수
export const NODE_LIMIT = 100  // 모바일은 100개로 제한
export const DEFAULT_DEPTH = 2

// 노드 수 제한 적용
function applyNodeLimit(data: GraphData, limit: number): GraphData {
  if (data.nodes.length <= limit) {
    return data
  }

  const connectionCount = new Map<string, number>()
  data.nodes.forEach(node => connectionCount.set(node.id, 0))
  data.links.forEach(link => {
    const sourceId = typeof link.source === 'string' ? link.source : link.source.id
    const targetId = typeof link.target === 'string' ? link.target : link.target.id
    connectionCount.set(sourceId, (connectionCount.get(sourceId) || 0) + 1)
    connectionCount.set(targetId, (connectionCount.get(targetId) || 0) + 1)
  })

  const sortedNodes = [...data.nodes].sort((a, b) => {
    if (a.type === 'company' && b.type !== 'company') return -1
    if (a.type !== 'company' && b.type === 'company') return 1
    return (connectionCount.get(b.id) || 0) - (connectionCount.get(a.id) || 0)
  })

  const limitedNodes = sortedNodes.slice(0, limit)
  const limitedNodeIds = new Set(limitedNodes.map(n => n.id))

  const limitedLinks = data.links.filter(link => {
    const sourceId = typeof link.source === 'string' ? link.source : link.source.id
    const targetId = typeof link.target === 'string' ? link.target : link.target.id
    return limitedNodeIds.has(sourceId) && limitedNodeIds.has(targetId)
  })

  return { nodes: limitedNodes, links: limitedLinks }
}

/**
 * 회사 중심 네트워크 조회 API
 */
export async function getCompanyNetwork(
  companyId: string,
  depth: number = DEFAULT_DEPTH,
  limit: number = NODE_LIMIT
): Promise<GraphData & { isLimited: boolean; originalCount: number }> {
  const params = { depth, limit: limit + 50 }

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

// 임원 경력 타입
export interface OfficerCareer {
  company_name: string
  company_id?: string | null
  position: string
  start_date?: string | null
  end_date?: string | null
  is_current: boolean
  is_listed?: boolean
  source: 'db' | 'disclosure'
  raw_text?: string
}

// 임원 경력 조회 결과 타입
export interface OfficerCareerResult {
  careers: OfficerCareer[]
  careerRawText?: string | null
}

// API 응답 타입
interface ApiOfficerCareerItem {
  company_name: string
  company_id?: string | null
  position: string
  start_date?: string | null
  end_date?: string | null
  is_current?: boolean
  is_listed?: boolean
  source?: 'db' | 'disclosure'
  raw_text?: string
}

interface ApiOfficerCareerResponse {
  officer: { id: string; type: string; properties: Record<string, unknown> }
  career_history: ApiOfficerCareerItem[]
  career_raw_text?: string | null
}

/**
 * 임원 경력 조회 API
 */
export async function fetchOfficerCareer(officerId: string): Promise<OfficerCareerResult> {
  try {
    const response = await apiClient.get<ApiOfficerCareerResponse>(`/api/graph/officer/${officerId}/career`)
    return {
      careers: (response.data.career_history || []).map(c => ({
        company_name: c.company_name,
        company_id: c.company_id,
        position: c.position,
        start_date: c.start_date || undefined,
        end_date: c.end_date || undefined,
        is_current: c.is_current ?? !c.end_date,
        is_listed: c.is_listed ?? (c.source === 'db'),
        source: c.source || 'db',
        raw_text: c.raw_text,
      })),
      careerRawText: response.data.career_raw_text,
    }
  } catch {
    // 폴백 시도
    try {
      const response = await apiClient.get<ApiOfficerCareerResponse>(`/api/graph-fallback/officer/${officerId}/career`)
      return {
        careers: (response.data.career_history || []).map(c => ({
          company_name: c.company_name,
          company_id: c.company_id,
          position: c.position,
          start_date: c.start_date || undefined,
          end_date: c.end_date || undefined,
          is_current: c.is_current ?? !c.end_date,
          is_listed: c.is_listed ?? (c.source === 'db'),
          source: c.source || 'db',
          raw_text: c.raw_text,
        })),
        careerRawText: response.data.career_raw_text,
      }
    } catch {
      return { careers: [], careerRawText: null }
    }
  }
}

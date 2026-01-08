// 그래프 노드 타입
export type NodeType = 'company' | 'officer' | 'subscriber' | 'cb' | 'shareholder' | 'affiliate'

// 그래프 노드 데이터
export interface GraphNode {
  id: string
  name: string
  type: NodeType
  // 회사 노드 추가 정보
  corp_code?: string
  risk_level?: string | null
  investment_grade?: string | null
  // 임원 노드 추가 정보
  position?: string
  listedCareerCount?: number
  deficitCareerCount?: number
  // CB 노드 추가 정보
  amount?: number
  issue_date?: string
  bond_name?: string
  // Subscriber 노드 법인정보
  representative_name?: string
  gp_name?: string
  largest_shareholder_name?: string
  // 대주주 노드 추가 정보
  shareholder_type?: 'individual' | 'corporation' | 'institution'
  shares?: number
  percentage?: number
  // D3 시뮬레이션 좌표 (런타임)
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
}

// 그래프 엣지 데이터
export interface GraphLink {
  source: string | GraphNode
  target: string | GraphNode
  type: 'officer' | 'subscriber' | 'cb_issue' | 'affiliate'
  label?: string
}

// 전체 그래프 데이터
export interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

// 노드 타입별 색상 설정 (모바일 밝은 테마)
export const nodeTypeColors: Record<NodeType, { fill: string; stroke: string; label: string }> = {
  company: { fill: '#3B82F6', stroke: '#1D4ED8', label: '회사' },
  officer: { fill: '#10B981', stroke: '#059669', label: '임원' },
  subscriber: { fill: '#8B5CF6', stroke: '#7C3AED', label: 'CB 투자자' },
  cb: { fill: '#F59E0B', stroke: '#D97706', label: '전환사채' },
  shareholder: { fill: '#F97316', stroke: '#EA580C', label: '대주주' },
  affiliate: { fill: '#06B6D4', stroke: '#0891B2', label: '계열사' },
}

// 엣지 타입별 색상
export const linkTypeColors: Record<string, string> = {
  officer: '#10B981',
  subscriber: '#8B5CF6',
  cb_issue: '#F59E0B',
  affiliate: '#06B6D4',
  shareholder: '#F97316',
}

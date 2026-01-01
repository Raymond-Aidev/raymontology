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
  listedCareerCount?: number  // 상장사 임원 경력 수 (DB 조회 결과)
  deficitCareerCount?: number // 적자기업 경력 수 (최근 2년 적자 회사)
  // CB 노드 추가 정보
  amount?: number
  issue_date?: string
  // Subscriber 노드 법인정보
  representative_name?: string  // 대표이사(대표조합원)
  gp_name?: string              // 업무집행자(업무집행조합원)
  largest_shareholder_name?: string  // 최대주주(최대출자자)
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

// 노드 타입별 색상 설정 (다크 테마 최적화 - 고대비 네온 스타일)
export const nodeTypeColors: Record<NodeType, { fill: string; stroke: string; label: string }> = {
  company: { fill: '#60A5FA', stroke: '#3B82F6', label: '회사' },       // Bright Blue (메인)
  officer: { fill: '#34D399', stroke: '#10B981', label: '임원' },       // Bright Green
  subscriber: { fill: '#A78BFA', stroke: '#8B5CF6', label: 'CB 투자자' }, // Bright Purple
  cb: { fill: '#FBBF24', stroke: '#F59E0B', label: '전환사채' },        // Bright Amber
  shareholder: { fill: '#FB923C', stroke: '#F97316', label: '대주주' }, // Bright Orange
  affiliate: { fill: '#22D3EE', stroke: '#06B6D4', label: '계열사' },   // Bright Cyan
}

// 엣지 타입별 색상 (다크 테마용 - 밝은 색상)
export const linkTypeColors: Record<string, string> = {
  officer: '#34D399',     // Bright Green
  subscriber: '#A78BFA',  // Bright Purple
  cb_issue: '#FBBF24',    // Bright Amber
  affiliate: '#22D3EE',   // Bright Cyan
  shareholder: '#FB923C', // Bright Orange
}

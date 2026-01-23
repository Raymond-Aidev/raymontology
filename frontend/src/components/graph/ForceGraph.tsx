import { useEffect, useRef, useCallback, useImperativeHandle, forwardRef, useState } from 'react'
import * as d3 from 'd3'
import type { GraphNode, GraphLink, GraphData } from '../../types/graph'
import { nodeTypeColors, linkTypeColors } from '../../types/graph'

// 임원 경력 3개 이상일 때 붉은색
const OFFICER_WARNING_COLOR = '#EF4444'  // red-500
const OFFICER_WARNING_STROKE = '#DC2626' // red-600

// 회사 노드 고정 색상 (노란색 바탕 + 검은색 폰트)
const COMPANY_FILL_COLOR = '#FBBF24'     // amber-400
const COMPANY_STROKE_COLOR = '#F59E0B'   // amber-500
const COMPANY_TEXT_COLOR = '#000000'     // black

// 적자기업 경력 경고 배지 색상
const DEFICIT_BADGE_COLOR = '#F97316'    // orange-500
const DEFICIT_BADGE_STROKE = '#EA580C'   // orange-600

// 이동 가능한 기업 노드 표시 (DB에 있는 기업)
const NAVIGABLE_COMPANY_GLOW = '#60A5FA'  // blue-400 (호버 시 글로우)

interface ForceGraphProps {
  data: GraphData
  width: number
  height: number
  onNodeClick?: (node: GraphNode) => void
  onNodeDoubleClick?: (node: GraphNode) => void
  onNavigateToCompany?: (node: GraphNode) => void  // 기업 관계도 이동 콜백
  selectedNodeId?: string | null
  centerCompanyId?: string | null  // 현재 그래프 중심 기업 ID
}

export interface ForceGraphRef {
  centerOnNode: (node: GraphNode) => void
}

const ForceGraph = forwardRef<ForceGraphRef, ForceGraphProps>(({
  data,
  width,
  height,
  onNodeClick,
  onNodeDoubleClick,
  onNavigateToCompany,
  selectedNodeId,
  centerCompanyId,
}, ref) => {
  const svgRef = useRef<SVGSVGElement>(null)
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(null)
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)

  // 클릭되어 채워진 노드들 (선택된 노드와 별개로 유지)
  const [filledNodeIds, setFilledNodeIds] = useState<Set<string>>(new Set())

  // DB에 등록된 기업인지 확인 (corp_code 존재 여부)
  // 현재 중심 기업은 네비게이션 대상에서 제외
  const isNavigableCompany = useCallback((node: GraphNode): boolean => {
    return node.type === 'company' &&
           !!node.corp_code &&
           node.id !== centerCompanyId
  }, [centerCompanyId])

  // 노드가 채워져야 하는지 결정 (임원 경력 3개 이상 또는 클릭됨)
  const shouldFillNode = useCallback((node: GraphNode): boolean => {
    // 임원이고 상장사 경력 3개 이상이면 항상 채움 (붉은색)
    if (node.type === 'officer' && (node.listedCareerCount ?? 0) >= 3) {
      return true
    }
    // 클릭된 노드는 채움
    return filledNodeIds.has(node.id)
  }, [filledNodeIds])

  // 노드 채우기 색상 결정
  const getNodeFillColor = useCallback((node: GraphNode): string => {
    // 회사 노드는 항상 노란색 바탕
    if (node.type === 'company') {
      return COMPANY_FILL_COLOR
    }
    // 임원이고 상장사 경력 3개 이상이면 붉은색
    if (node.type === 'officer' && (node.listedCareerCount ?? 0) >= 3) {
      return OFFICER_WARNING_COLOR
    }
    // 클릭된 노드는 타입별 색상으로 채움
    if (filledNodeIds.has(node.id)) {
      return nodeTypeColors[node.type].fill
    }
    // 기본: 투명 (테두리만)
    return 'transparent'
  }, [filledNodeIds])

  // 노드 테두리 색상 결정
  const getNodeStrokeColor = useCallback((node: GraphNode): string => {
    // 회사 노드는 노란색 계열 테두리
    if (node.type === 'company') {
      return COMPANY_STROKE_COLOR
    }
    // 임원이고 상장사 경력 3개 이상이면 붉은색 테두리
    if (node.type === 'officer' && (node.listedCareerCount ?? 0) >= 3) {
      return OFFICER_WARNING_STROKE
    }
    return nodeTypeColors[node.type].stroke
  }, [])

  // 노드 텍스트 색상 결정
  const getNodeTextColor = useCallback((node: GraphNode): string => {
    // 회사 노드는 검은색 텍스트
    if (node.type === 'company') {
      return COMPANY_TEXT_COLOR
    }
    // 채워진 노드는 흰색 텍스트
    if (shouldFillNode(node) || filledNodeIds.has(node.id)) {
      return 'white'
    }
    // 테두리만 있는 노드는 테두리 색상과 동일
    return getNodeStrokeColor(node)
  }, [shouldFillNode, filledNodeIds, getNodeStrokeColor])

  // 노드 중심으로 이동하는 함수
  const centerOnNodeFn = useCallback((node: GraphNode) => {
    if (!svgRef.current || !zoomRef.current) return

    const svg = d3.select(svgRef.current)
    const x = node.x ?? width / 2
    const y = node.y ?? height / 2

    // 현재 줌 레벨 가져오기
    const currentTransform = d3.zoomTransform(svgRef.current)
    const scale = Math.max(currentTransform.k, 1.2) // 최소 1.2배 줌

    // 새 transform 계산 (노드를 화면 중앙으로)
    const newTransform = d3.zoomIdentity
      .translate(width / 2 - x * scale, height / 2 - y * scale)
      .scale(scale)

    // 부드러운 애니메이션으로 이동 (1초)
    svg.transition()
      .duration(1000)
      .ease(d3.easeCubicInOut)
      .call(zoomRef.current.transform, newTransform)
  }, [width, height])

  // ref를 통해 centerOnNode 함수 노출
  useImperativeHandle(ref, () => ({
    centerOnNode: centerOnNodeFn
  }), [centerOnNodeFn])

  const getNodeRadius = useCallback((node: GraphNode) => {
    switch (node.type) {
      case 'company':
        return 40
      case 'officer':
        return 28
      case 'subscriber':
        return 30
      case 'cb':
        return 26
      case 'shareholder':
        return 28
      case 'affiliate':
        return 32
      default:
        return 26
    }
  }, [])

  useEffect(() => {
    if (!svgRef.current || !data.nodes.length) return

    const svg = d3.select(svgRef.current)
    // Preserve accessibility elements (title, desc), only remove D3-managed elements
    svg.selectAll('g, defs').remove()

    // 줌 설정
    const g = svg.append('g')
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
      })
    svg.call(zoom)
    zoomRef.current = zoom

    // 노드와 링크 복사 (D3 뮤테이션 방지)
    const nodes: GraphNode[] = data.nodes.map(d => ({ ...d }))
    const links: GraphLink[] = data.links.map(d => ({ ...d }))

    // Force 시뮬레이션
    const simulation = d3.forceSimulation<GraphNode>(nodes)
      .force('link', d3.forceLink<GraphNode, GraphLink>(links)
        .id(d => d.id)
        .distance(120)
        .strength(0.8)
      )
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide<GraphNode>().radius(d => getNodeRadius(d) + 15))

    simulationRef.current = simulation

    // 화살표 마커 정의
    const defs = svg.append('defs')
    const markerTypes = ['officer', 'subscriber', 'cb_issue', 'affiliate', 'shareholder']
    markerTypes.forEach(type => {
      defs.append('marker')
        .attr('id', `arrow-${type}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 35)
        .attr('refY', 0)
        .attr('markerWidth', 5)
        .attr('markerHeight', 5)
        .attr('orient', 'auto')
        .append('path')
        .attr('fill', linkTypeColors[type] || '#52525b')
        .attr('d', 'M0,-5L10,0L0,5')
    })

    // 링크 그리기
    const link = g.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', d => {
        const linkType = typeof d.type === 'string' ? d.type : 'affiliate'
        return linkTypeColors[linkType] || '#52525b'
      })
      .attr('stroke-opacity', 0.5)
      .attr('stroke-width', 2)
      .attr('marker-end', d => `url(#arrow-${d.type})`)

    // 노드 그룹
    const node = g.append('g')
      .attr('class', 'nodes')
      .attr('role', 'list')
      .attr('aria-label', '네트워크 노드 목록')
      .selectAll<SVGGElement, GraphNode>('g')
      .data(nodes)
      .join('g')
      .attr('class', 'node')
      .attr('role', 'listitem')
      .attr('aria-label', d => {
        const typeLabel = {
          company: '회사',
          officer: '임원',
          subscriber: 'CB투자자',
          cb: '전환사채',
          shareholder: '대주주',
          affiliate: '계열사'
        }[d.type] || d.type
        return `${typeLabel}: ${d.name}`
      })
      .attr('tabindex', 0)
      .style('cursor', d => isNavigableCompany(d) ? 'pointer' : 'default')
      .call(d3.drag<SVGGElement, GraphNode>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event, d) => {
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0)
          d.fx = null
          d.fy = null
        })
      )

    // 노드 원 (글로우 효과) - 선택된 노드만
    node.append('circle')
      .attr('r', d => getNodeRadius(d) + 4)
      .attr('fill', 'transparent')
      .attr('stroke', d => {
        if (selectedNodeId && d.id === selectedNodeId) {
          return getNodeStrokeColor(d)
        }
        return 'transparent'
      })
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.5)
      .attr('class', 'glow-ring')

    // 노드 원 - 테두리 스타일 (기본: 투명 배경 + 색상 테두리)
    node.append('circle')
      .attr('r', d => getNodeRadius(d))
      .attr('fill', d => getNodeFillColor(d))
      .attr('stroke', d => {
        if (selectedNodeId && d.id === selectedNodeId) {
          return '#FFFFFF'  // 선택된 노드는 흰색 테두리
        }
        return getNodeStrokeColor(d)
      })
      .attr('stroke-width', d => {
        if (selectedNodeId && d.id === selectedNodeId) return 4
        // 테두리 강조를 위해 두껍게
        return 3
      })
      .attr('stroke-opacity', 1)
      .attr('class', 'main-circle')

    // 노드 안에 이름 표시 (회사명/인물명)
    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('fill', d => getNodeTextColor(d))
      .attr('font-size', d => {
        const name = d.name || ''
        const radius = getNodeRadius(d)

        // 회사 노드: 가장 큰 폰트 (기본)
        // 다른 노드: 2단계 작게 (-4px)
        const sizeReduction = d.type === 'company' ? 0 : 4

        // 이름 길이에 따라 폰트 크기 조절
        if (name.length <= 3) return `${Math.max(Math.min(radius * 0.6, 16) - sizeReduction, 8)}px`
        if (name.length <= 5) return `${Math.max(Math.min(radius * 0.5, 14) - sizeReduction, 8)}px`
        return `${Math.max(Math.min(radius * 0.45, 12) - sizeReduction, 7)}px`
      })
      .attr('font-weight', '600')
      .attr('font-family', 'Inter, system-ui, sans-serif')
      .attr('class', 'node-label')
      .text(d => {
        const name = d.name || ''
        const radius = getNodeRadius(d)
        // 원 크기에 맞게 이름 자르기
        const maxChars = Math.floor(radius / 5)
        if (name.length > maxChars) {
          return name.slice(0, maxChars - 1) + '..'
        }
        return name
      })

    // 노드 타입 라벨 (원 아래에 표시)
    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', d => getNodeRadius(d) + 14)
      .attr('fill', '#71717a')
      .attr('font-size', '10px')
      .attr('font-weight', '500')
      .attr('font-family', 'Inter, system-ui, sans-serif')
      .text(d => {
        if (d.type === 'company') return '회사'
        if (d.type === 'officer') return '임원'
        if (d.type === 'subscriber') return 'CB투자자'
        if (d.type === 'cb') return '전환사채'
        if (d.type === 'shareholder') return '대주주'
        if (d.type === 'affiliate') return '계열사'
        return d.type
      })

    // 적자기업 경력 경고 배지 (임원 노드에만 표시)
    // 노드 우측 상단에 작은 원형 배지로 "주의" 표시
    const badgeGroup = node.filter(d => d.type === 'officer' && (d.deficitCareerCount ?? 0) >= 1)
      .append('g')
      .attr('class', 'deficit-badge')
      .attr('transform', d => {
        const radius = getNodeRadius(d)
        // 노드 우측 상단에 배치 (45도 각도)
        const badgeX = radius * 0.7
        const badgeY = -radius * 0.7
        return `translate(${badgeX}, ${badgeY})`
      })

    // 배지 배경 원
    badgeGroup.append('circle')
      .attr('r', 12)
      .attr('fill', DEFICIT_BADGE_COLOR)
      .attr('stroke', DEFICIT_BADGE_STROKE)
      .attr('stroke-width', 2)

    // 배지 텍스트 "주의"
    badgeGroup.append('text')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('fill', 'white')
      .attr('font-size', '8px')
      .attr('font-weight', '700')
      .attr('font-family', 'Inter, system-ui, sans-serif')
      .text('주의')

    // 클릭 이벤트 - 노드 채우기 (단일 선택) + 상세 패널 열기
    node.on('click', (event, d) => {
      event.stopPropagation()

      // 회사 노드와 임원 경력 3개 이상은 항상 채워져 있으므로 선택 토글 제외
      const isFixedFill = d.type === 'company' || (d.type === 'officer' && (d.listedCareerCount ?? 0) >= 3)
      if (!isFixedFill) {
        const svg = d3.select(svgRef.current)
        const wasSelected = filledNodeIds.has(d.id)

        // 단일 선택: 이전 선택 모두 해제 후 새 노드만 선택
        setFilledNodeIds(() => {
          if (wasSelected) {
            // 이미 선택된 노드 클릭 시 선택 해제
            return new Set()
          } else {
            // 새 노드 선택 (기존 선택 해제)
            return new Set([d.id])
          }
        })

        // D3로 즉시 시각적 업데이트
        // 1. 모든 노드 채움 해제 (회사 노드와 경력 3개 이상 임원 제외)
        svg.selectAll<SVGGElement, GraphNode>('.nodes .node').each(function(nodeData) {
          const isFixed = nodeData.type === 'company' || (nodeData.type === 'officer' && (nodeData.listedCareerCount ?? 0) >= 3)
          if (!isFixed) {
            const nodeGroup = d3.select(this)
            nodeGroup.select('.main-circle').attr('fill', 'transparent')
            nodeGroup.select('.node-label').attr('fill', getNodeStrokeColor(nodeData))
          }
        })

        // 2. 새로 선택된 노드만 채우기 (선택 해제가 아닌 경우)
        if (!wasSelected) {
          const nodeGroup = d3.select(event.currentTarget)
          nodeGroup.select('.main-circle').attr('fill', nodeTypeColors[d.type].fill)
          nodeGroup.select('.node-label').attr('fill', 'white')
        }
      }

      onNodeClick?.(d)
    })

    // 더블클릭 이벤트: DB 기업 → 네비게이션, 그 외 → Re-center
    node.on('dblclick', (event, d) => {
      event.stopPropagation()

      // DB에 등록된 기업이면 해당 기업 관계도로 이동
      if (isNavigableCompany(d)) {
        onNavigateToCompany?.(d)
      } else {
        // 그 외 노드는 재중심
        centerOnNodeFn(d)
        onNodeDoubleClick?.(d)
      }
    })

    // 키보드 접근성: Enter/Space로 노드 선택, DB 기업은 Enter로 이동
    node.on('keydown', (event: KeyboardEvent, d) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        event.stopPropagation()

        // Enter 키로 DB 기업 관계도 이동
        if (event.key === 'Enter' && isNavigableCompany(d)) {
          onNavigateToCompany?.(d)
        } else {
          onNodeClick?.(d)
        }
      }
    })

    // 호버 이벤트: 이동 가능한 기업 노드에 글로우 효과
    node.on('mouseenter', function(_event, d) {
      if (isNavigableCompany(d)) {
        const nodeGroup = d3.select(this)
        // 글로우 링 활성화
        nodeGroup.select('.glow-ring')
          .attr('stroke', NAVIGABLE_COMPANY_GLOW)
          .attr('stroke-opacity', 0.8)
          .attr('stroke-width', 3)
        // 커서를 pointer로 변경 (이미 설정되어 있지만 명시적으로)
        nodeGroup.style('cursor', 'pointer')
      }
    })

    node.on('mouseleave', function(_event, d) {
      if (isNavigableCompany(d)) {
        const nodeGroup = d3.select(this)
        // 글로우 링 비활성화 (선택된 노드가 아니면)
        if (d.id !== selectedNodeId) {
          nodeGroup.select('.glow-ring')
            .attr('stroke', 'transparent')
            .attr('stroke-opacity', 0.5)
        }
      }
    })

    // 시뮬레이션 틱
    simulation.on('tick', () => {
      link
        .attr('x1', d => (d.source as GraphNode).x ?? 0)
        .attr('y1', d => (d.source as GraphNode).y ?? 0)
        .attr('x2', d => (d.target as GraphNode).x ?? 0)
        .attr('y2', d => (d.target as GraphNode).y ?? 0)

      node.attr('transform', d => `translate(${d.x ?? 0},${d.y ?? 0})`)
    })

    // SVG 클릭 시 선택 해제
    svg.on('click', () => {
      onNodeClick?.(null as unknown as GraphNode)
    })

    return () => {
      simulation.stop()
    }
    // Note: filledNodeIds, getNodeFillColor, shouldFillNode are intentionally excluded
    // Click handler updates node visuals directly via D3, no re-render needed
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, width, height, onNodeClick, onNodeDoubleClick, onNavigateToCompany, selectedNodeId, getNodeRadius, centerOnNodeFn, getNodeStrokeColor, isNavigableCompany])

  // 선택 노드 변경 시 하이라이트 업데이트
  useEffect(() => {
    if (!svgRef.current) return
    const svg = d3.select(svgRef.current)

    // 글로우 링 업데이트
    svg.selectAll<SVGCircleElement, GraphNode>('.nodes .glow-ring')
      .attr('stroke', d => {
        if (selectedNodeId && d.id === selectedNodeId) {
          return getNodeStrokeColor(d)
        }
        return 'transparent'
      })

    // 메인 원 업데이트
    svg.selectAll<SVGCircleElement, GraphNode>('.nodes .main-circle')
      .attr('stroke', d => {
        if (selectedNodeId && d.id === selectedNodeId) {
          return '#FFFFFF'
        }
        return getNodeStrokeColor(d)
      })
      .attr('stroke-width', d => selectedNodeId && d.id === selectedNodeId ? 4 : 3)
  }, [selectedNodeId, getNodeStrokeColor])

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      className="bg-theme-bg rounded-lg"
      style={{
        background: 'radial-gradient(circle at center, #171717 0%, #0a0a0a 100%)'
      }}
      role="img"
      aria-label={`기업 네트워크 그래프: ${data.nodes.length}개 노드, ${data.links.length}개 연결`}
      tabIndex={0}
    >
      <title>기업 네트워크 시각화</title>
      <desc>
        기업, 임원, CB투자자, 계열사 간의 연결 관계를 보여주는 인터랙티브 네트워크 그래프입니다.
        노드를 클릭하면 상세 정보를 볼 수 있습니다.
      </desc>
    </svg>
  )
})

ForceGraph.displayName = 'ForceGraph'

export default ForceGraph

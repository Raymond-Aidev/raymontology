import { useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react'
import * as d3 from 'd3'
import type { GraphData, GraphNode, GraphLink, NodeType } from '../../types/graph'
import { nodeTypeColors, linkTypeColors } from '../../types/graph'
import { colors } from '../../constants/colors'

interface ForceGraphProps {
  data: GraphData
  width: number
  height: number
  onNodeClick?: (node: GraphNode | null) => void
  selectedNodeId?: string
}

export interface ForceGraphRef {
  centerOnNode: (node: GraphNode) => void
}

const ForceGraph = forwardRef<ForceGraphRef, ForceGraphProps>(({
  data,
  width,
  height,
  onNodeClick,
  selectedNodeId,
}, ref) => {
  const svgRef = useRef<SVGSVGElement>(null)
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(null)
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)

  // 노드 중심으로 이동
  const centerOnNode = useCallback((node: GraphNode) => {
    if (!svgRef.current || !zoomRef.current || node.x === undefined || node.y === undefined) return

    const svg = d3.select(svgRef.current)
    const x = width / 2 - node.x
    const y = height / 2 - node.y

    svg.transition().duration(500).call(
      zoomRef.current.transform as never,
      d3.zoomIdentity.translate(x, y).scale(1.5)
    )
  }, [width, height])

  useImperativeHandle(ref, () => ({ centerOnNode }), [centerOnNode])

  useEffect(() => {
    if (!svgRef.current || data.nodes.length === 0) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    // 노드 반경 (모바일 최적화 - 작은 크기)
    const getNodeRadius = (type: NodeType) => {
      switch (type) {
        case 'company': return 24
        case 'officer': return 16
        case 'cb': return 14
        case 'subscriber': return 16
        case 'shareholder': return 16
        case 'affiliate': return 18
        default: return 14
      }
    }

    // 줌 설정
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 3])
      .on('zoom', (event) => {
        container.attr('transform', event.transform)
      })

    svg.call(zoom)
    zoomRef.current = zoom

    // 메인 컨테이너
    const container = svg.append('g')

    // 화살표 마커 정의
    const defs = svg.append('defs')
    Object.entries(linkTypeColors).forEach(([type, color]) => {
      defs.append('marker')
        .attr('id', `arrow-${type}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', color)
    })

    // 시뮬레이션
    const simulation = d3.forceSimulation<GraphNode>(data.nodes)
      .force('link', d3.forceLink<GraphNode, GraphLink>(data.links)
        .id(d => d.id)
        .distance(80))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide<GraphNode>().radius(d => getNodeRadius(d.type) + 5))

    simulationRef.current = simulation

    // 링크 렌더링
    const link = container.append('g')
      .selectAll('line')
      .data(data.links)
      .join('line')
      .attr('stroke', d => linkTypeColors[d.type] || colors.gray500)
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.6)
      .attr('marker-end', d => `url(#arrow-${d.type})`)

    // 노드 그룹
    const node = container.append('g')
      .selectAll<SVGGElement, GraphNode>('g')
      .data(data.nodes)
      .join('g')
      .attr('cursor', 'pointer')
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
        }))

    // 노드 원
    node.append('circle')
      .attr('r', d => getNodeRadius(d.type))
      .attr('fill', d => nodeTypeColors[d.type]?.fill || colors.gray500)
      .attr('stroke', d => {
        // 선택된 노드 강조
        if (selectedNodeId === d.id) return '#000000'
        // 임원 주의 표시 (상장사 3개 이상)
        if (d.type === 'officer' && d.listedCareerCount && d.listedCareerCount >= 3) {
          return '#EF4444'
        }
        return nodeTypeColors[d.type]?.stroke || colors.gray600
      })
      .attr('stroke-width', d => selectedNodeId === d.id ? 3 : 2)

    // 원 안에 이름 표시 (2글자까지)
    node.append('text')
      .text(d => {
        // 회사는 3글자, 나머지는 2글자
        const maxLen = d.type === 'company' ? 3 : 2
        return d.name.slice(0, maxLen)
      })
      .attr('text-anchor', 'middle')
      .attr('dy', 4)  // 원 중앙에 배치
      .attr('font-size', d => d.type === 'company' ? '11px' : '9px')
      .attr('font-weight', '600')
      .attr('fill', '#FFFFFF')  // 흰색 글자
      .style('pointer-events', 'none')  // 클릭 이벤트 투과

    // 원 아래에 구분자 표시 (임원, 대주주 등)
    node.append('text')
      .text(d => nodeTypeColors[d.type]?.label || '')
      .attr('text-anchor', 'middle')
      .attr('dy', d => getNodeRadius(d.type) + 12)
      .attr('font-size', '9px')
      .attr('font-weight', '500')
      .attr('fill', colors.gray500)
      .style('pointer-events', 'none')

    // 임원 주의 배지 (적자기업 경력 있는 경우 - 원 우측 상단에 표시)
    node.filter(d => d.type === 'officer' && (d.deficitCareerCount ?? 0) >= 1)
      .append('circle')
      .attr('cx', d => getNodeRadius(d.type) - 4)
      .attr('cy', d => -getNodeRadius(d.type) + 4)
      .attr('r', 6)
      .attr('fill', '#F97316')
      .attr('stroke', '#FFFFFF')
      .attr('stroke-width', 1.5)

    node.filter(d => d.type === 'officer' && (d.deficitCareerCount ?? 0) >= 1)
      .append('text')
      .text('!')
      .attr('x', d => getNodeRadius(d.type) - 4)
      .attr('y', d => -getNodeRadius(d.type) + 8)
      .attr('text-anchor', 'middle')
      .attr('font-size', '9px')
      .attr('font-weight', 'bold')
      .attr('fill', '#FFFFFF')
      .style('pointer-events', 'none')

    // 노드 클릭 이벤트
    node.on('click', (event, d) => {
      event.stopPropagation()
      onNodeClick?.(d)
    })

    // 배경 클릭 시 선택 해제
    svg.on('click', () => {
      onNodeClick?.(null)
    })

    // 시뮬레이션 틱
    simulation.on('tick', () => {
      link
        .attr('x1', d => (d.source as GraphNode).x || 0)
        .attr('y1', d => (d.source as GraphNode).y || 0)
        .attr('x2', d => (d.target as GraphNode).x || 0)
        .attr('y2', d => (d.target as GraphNode).y || 0)

      node.attr('transform', d => `translate(${d.x || 0},${d.y || 0})`)
    })

    // 초기 줌 조정 (모바일에서 전체 보이도록)
    const zoomTimer = setTimeout(() => {
      const bounds = container.node()?.getBBox()
      if (bounds) {
        const scale = Math.min(
          width / (bounds.width + 100),
          height / (bounds.height + 100),
          1
        )
        const translateX = (width - bounds.width * scale) / 2 - bounds.x * scale
        const translateY = (height - bounds.height * scale) / 2 - bounds.y * scale

        svg.transition().duration(500).call(
          zoom.transform as never,
          d3.zoomIdentity.translate(translateX, translateY).scale(scale)
        )
      }
    }, 500)

    // 메모리 릭 방지: 모든 이벤트 리스너 및 타이머 정리
    return () => {
      // 타이머 정리
      clearTimeout(zoomTimer)

      // 시뮬레이션 중지
      simulation.stop()

      // 이벤트 리스너 정리
      svg.on('.zoom', null)  // zoom 이벤트 제거
      svg.on('click', null)  // click 이벤트 제거
      node.on('click', null) // 노드 클릭 이벤트 제거

      // DOM 정리 (selectAll('*').remove()는 다음 렌더에서 수행됨)
      simulationRef.current = null
      zoomRef.current = null
    }
  }, [data, width, height, onNodeClick, selectedNodeId])

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      style={{ backgroundColor: colors.white, touchAction: 'none' }}
    />
  )
})

ForceGraph.displayName = 'ForceGraph'

export default ForceGraph

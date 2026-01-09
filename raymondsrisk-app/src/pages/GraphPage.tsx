import { useState, useRef, useCallback, useEffect, useMemo } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import * as d3 from 'd3'
import { ForceGraph, NodeDetailPanel, GraphControls } from '../components/graph'
import type { ForceGraphRef } from '../components/graph'
import { BottomSheet } from '../components/common'
import type { GraphNode, GraphData, NodeType } from '../types/graph'
import { getCompanyNetwork, NODE_LIMIT, DEFAULT_DEPTH } from '../api/graph'
import { colors } from '../constants/colors'

export default function GraphPage() {
  const { corpCode } = useParams<{ corpCode: string }>()
  const navigate = useNavigate()
  const location = useLocation()

  // 회사명 (이전 페이지에서 전달받음)
  const companyName = location.state?.companyName || '기업'

  // 상태
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [depth, setDepth] = useState(DEFAULT_DEPTH)
  const [visibleNodeTypes, setVisibleNodeTypes] = useState<Set<NodeType>>(
    new Set(['company', 'officer', 'subscriber', 'cb', 'shareholder', 'affiliate'])
  )
  const [isNodeLimited, setIsNodeLimited] = useState(false)
  const [originalNodeCount, setOriginalNodeCount] = useState(0)

  // 화면 크기
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })
  const svgRef = useRef<SVGSVGElement | null>(null)
  const forceGraphRef = useRef<ForceGraphRef>(null)

  // 화면 크기 감지
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setDimensions({
          width: rect.width,
          height: window.innerHeight - 120, // 헤더 공간 제외
        })
      }
    }

    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  // 그래프 데이터 로드
  useEffect(() => {
    if (!corpCode) return

    const loadGraph = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const data = await getCompanyNetwork(corpCode, depth, NODE_LIMIT)
        setGraphData(data)
        setIsNodeLimited(data.isLimited)
        setOriginalNodeCount(data.originalCount)
      } catch {
        setError('관계도를 불러오는데 실패했습니다')
      } finally {
        setIsLoading(false)
      }
    }

    loadGraph()
  }, [corpCode, depth])

  // SVG ref 저장
  useEffect(() => {
    const svg = containerRef.current?.querySelector('svg')
    if (svg) {
      svgRef.current = svg as SVGSVGElement
    }
  }, [dimensions, graphData])

  // 노드 클릭 핸들러
  const handleNodeClick = useCallback((node: GraphNode | null) => {
    setSelectedNode(node)
  }, [])

  // 회사 노드 네비게이션
  const handleNavigateToCompany = useCallback((node: GraphNode) => {
    if (node.type === 'company' && node.corp_code) {
      navigate(`/graph/${node.corp_code}`, {
        state: { companyName: node.name }
      })
      setSelectedNode(null)
    }
  }, [navigate])

  // 줌 컨트롤
  const handleZoomIn = useCallback(() => {
    if (svgRef.current) {
      const svg = d3.select(svgRef.current)
      svg.transition().duration(300).call(
        d3.zoom<SVGSVGElement, unknown>().scaleBy as never,
        1.3
      )
    }
  }, [])

  const handleZoomOut = useCallback(() => {
    if (svgRef.current) {
      const svg = d3.select(svgRef.current)
      svg.transition().duration(300).call(
        d3.zoom<SVGSVGElement, unknown>().scaleBy as never,
        0.7
      )
    }
  }, [])

  const handleReset = useCallback(() => {
    if (svgRef.current) {
      const svg = d3.select(svgRef.current)
      svg.transition().duration(500).call(
        d3.zoom<SVGSVGElement, unknown>().transform as never,
        d3.zoomIdentity
      )
    }
  }, [])

  // 노드 타입 토글
  const handleToggleNodeType = useCallback((type: NodeType) => {
    setVisibleNodeTypes(prev => {
      const next = new Set(prev)
      if (next.has(type)) {
        if (next.size > 1) next.delete(type)
      } else {
        next.add(type)
      }
      return next
    })
  }, [])

  // 탐색 깊이 변경
  const handleDepthChange = useCallback((newDepth: number) => {
    setDepth(Math.max(1, Math.min(3, newDepth)))
  }, [])

  // 필터링된 그래프 데이터
  const filteredGraphData = useMemo(() => {
    const visibleNodes = graphData.nodes.filter(node => visibleNodeTypes.has(node.type))
    const visibleNodeIds = new Set(visibleNodes.map(n => n.id))

    const visibleLinks = graphData.links.filter(link => {
      const sourceId = typeof link.source === 'string' ? link.source : (link.source as GraphNode).id
      const targetId = typeof link.target === 'string' ? link.target : (link.target as GraphNode).id
      return visibleNodeIds.has(sourceId) && visibleNodeIds.has(targetId)
    })

    return { nodes: visibleNodes, links: visibleLinks }
  }, [graphData, visibleNodeTypes])

  // 노드 타입별 카운트
  const nodeCounts = useMemo(() => {
    const counts: Record<NodeType, number> = {
      company: 0, officer: 0, subscriber: 0, cb: 0, shareholder: 0, affiliate: 0,
    }
    graphData.nodes.forEach(node => { counts[node.type]++ })
    return counts
  }, [graphData])

  // 중심 회사 찾기
  const centerCompany = graphData.nodes.find(n =>
    n.type === 'company' && (n.corp_code === corpCode || n.id === corpCode)
  )

  return (
    <div style={{ minHeight: '100vh', backgroundColor: colors.white }}>
      {/* 헤더 */}
      <header style={{
        padding: '12px 16px',
        paddingTop: 'max(env(safe-area-inset-top), 12px)',
        backgroundColor: colors.white,
        borderBottom: `1px solid ${colors.gray100}`,
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={() => navigate(-1)}
              style={{
                padding: '8px',
                border: 'none',
                backgroundColor: 'transparent',
                color: colors.blue500,
                fontSize: '16px',
                cursor: 'pointer',
              }}
            >
              ← 뒤로
            </button>
            <h1 style={{
              fontSize: '16px',
              fontWeight: '600',
              color: colors.gray900,
              margin: 0,
              maxWidth: '150px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {centerCompany?.name || companyName} 관계도
            </h1>
          </div>

          {/* 탐색 깊이 버튼 */}
          <div style={{ display: 'flex', gap: '4px' }}>
            {[1, 2, 3].map(d => (
              <button
                key={d}
                onClick={() => handleDepthChange(d)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: depth === d ? `1px solid ${colors.blue500}` : `1px solid ${colors.gray100}`,
                  backgroundColor: depth === d ? `${colors.blue500}15` : colors.white,
                  color: depth === d ? colors.blue500 : colors.gray600,
                  fontSize: '13px',
                  fontWeight: '500',
                  cursor: 'pointer',
                }}
              >
                {d}단계
              </button>
            ))}
          </div>
        </div>

        {/* 노드 제한 경고 */}
        {isNodeLimited && (
          <div style={{
            marginTop: '8px',
            padding: '6px 10px',
            backgroundColor: '#FEF3C7',
            borderRadius: '6px',
            fontSize: '12px',
            color: '#D97706',
          }}>
            노드가 많아 상위 {NODE_LIMIT}개만 표시 (전체 {originalNodeCount}개)
          </div>
        )}
      </header>

      {/* 그래프 영역 */}
      <div
        ref={containerRef}
        style={{
          position: 'relative',
          width: '100%',
          height: `calc(100vh - 120px)`,
          overflow: 'hidden',
        }}
      >
        {isLoading ? (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{
                width: '40px',
                height: '40px',
                border: `3px solid ${colors.gray100}`,
                borderTopColor: colors.blue500,
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                margin: '0 auto 12px',
              }} />
              <p style={{ color: colors.gray500, fontSize: '14px' }}>관계도 로딩 중...</p>
              <style>{`
                @keyframes spin {
                  to { transform: rotate(360deg); }
                }
              `}</style>
            </div>
          </div>
        ) : error ? (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <div style={{ fontSize: '48px', marginBottom: '12px' }}>⚠️</div>
              <p style={{ color: colors.gray900, fontSize: '16px', fontWeight: '500', marginBottom: '8px' }}>
                오류 발생
              </p>
              <p style={{ color: colors.gray500, fontSize: '14px', marginBottom: '16px' }}>{error}</p>
              <button
                onClick={() => window.location.reload()}
                style={{
                  padding: '10px 20px',
                  borderRadius: '8px',
                  border: 'none',
                  backgroundColor: colors.blue500,
                  color: colors.white,
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                다시 시도
              </button>
            </div>
          </div>
        ) : filteredGraphData.nodes.length === 0 ? (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <div style={{ fontSize: '48px', marginBottom: '12px' }}>📊</div>
              <p style={{ color: colors.gray500, fontSize: '14px' }}>관계 데이터가 없습니다</p>
            </div>
          </div>
        ) : (
          <>
            <ForceGraph
              ref={forceGraphRef}
              data={filteredGraphData}
              width={dimensions.width}
              height={dimensions.height}
              onNodeClick={handleNodeClick}
              selectedNodeId={selectedNode?.id}
            />
            <GraphControls
              onZoomIn={handleZoomIn}
              onZoomOut={handleZoomOut}
              onReset={handleReset}
              visibleNodeTypes={visibleNodeTypes}
              onToggleNodeType={handleToggleNodeType}
              nodeCounts={nodeCounts}
            />
          </>
        )}
      </div>

      {/* 하단 통계 */}
      {!isLoading && !error && filteredGraphData.nodes.length > 0 && (
        <div style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          backgroundColor: colors.white,
          borderTop: `1px solid ${colors.gray100}`,
          padding: '12px 16px',
          paddingBottom: 'max(env(safe-area-inset-bottom), 12px)',
          display: 'flex',
          justifyContent: 'space-around',
          zIndex: 30,
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '18px', fontWeight: '700', color: '#3B82F6' }}>
              {filteredGraphData.nodes.filter(n => n.type === 'company').length}
            </div>
            <div style={{ fontSize: '11px', color: colors.gray500 }}>회사</div>
          </div>
          <div style={{ width: '1px', backgroundColor: colors.gray100 }} />
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '18px', fontWeight: '700', color: '#10B981' }}>
              {filteredGraphData.nodes.filter(n => n.type === 'officer').length}
            </div>
            <div style={{ fontSize: '11px', color: colors.gray500 }}>임원</div>
          </div>
          <div style={{ width: '1px', backgroundColor: colors.gray100 }} />
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '18px', fontWeight: '700', color: '#F59E0B' }}>
              {filteredGraphData.nodes.filter(n => n.type === 'cb').length}
            </div>
            <div style={{ fontSize: '11px', color: colors.gray500 }}>CB</div>
          </div>
          <div style={{ width: '1px', backgroundColor: colors.gray100 }} />
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '18px', fontWeight: '700', color: colors.gray600 }}>
              {filteredGraphData.links.length}
            </div>
            <div style={{ fontSize: '11px', color: colors.gray500 }}>관계</div>
          </div>
        </div>
      )}

      {/* 노드 상세 BottomSheet */}
      <BottomSheet
        isOpen={!!selectedNode}
        onClose={() => setSelectedNode(null)}
        title={selectedNode?.name || '노드 상세'}
        minHeight={35}
        maxHeight={70}
      >
        <NodeDetailPanel
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
          onNavigateToCompany={handleNavigateToCompany}
        />
      </BottomSheet>
    </div>
  )
}

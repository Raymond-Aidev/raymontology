import { useState, useRef, useCallback, useEffect, useMemo } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import * as d3 from 'd3'
import { ForceGraph, NodeDetailPanel, GraphControls } from '../components/graph'
import type { ForceGraphRef } from '../components/graph'
import { BottomSheet } from '../components/common'
import type { GraphNode, GraphData, NodeType } from '../types/graph'
import { getCompanyNetwork, NODE_LIMIT, DEFAULT_DEPTH } from '../api/graph'
import { colors } from '../constants/colors'
import { useAuth } from '../contexts/AuthContext'
import { DataTabs } from '../components/report'
import { getCompanyReport } from '../api/report'
import type { CompanyReportData } from '../types/report'
import * as creditService from '../services/creditService'

// 탭 타입
type TabType = 'graph' | 'report'

export default function AnalysisPage() {
  const { corpCode } = useParams<{ corpCode: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, isLoading: authLoading, credits, deductCredit } = useAuth()

  // 회사명 (이전 페이지에서 전달받음)
  const companyName = location.state?.companyName || '기업'

  // 탭 상태 (디폴트: 관계도)
  const [activeTab, setActiveTab] = useState<TabType>('graph')

  // === 관계도 상태 ===
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] })
  const [isGraphLoading, setIsGraphLoading] = useState(true)
  const [graphError, setGraphError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [depth, setDepth] = useState(DEFAULT_DEPTH)
  const [visibleNodeTypes, setVisibleNodeTypes] = useState<Set<NodeType>>(
    new Set(['company', 'officer', 'subscriber', 'cb', 'shareholder', 'affiliate'])
  )
  const [isNodeLimited, setIsNodeLimited] = useState(false)
  const [originalNodeCount, setOriginalNodeCount] = useState(0)

  // === 분석리포트 상태 ===
  const [reportData, setReportData] = useState<CompanyReportData | null>(null)
  const [isReportLoading, setIsReportLoading] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)

  // === 이용권 차감 상태 ===
  const [creditDeducted, setCreditDeducted] = useState(false)

  // 화면 크기
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })
  const svgRef = useRef<SVGSVGElement | null>(null)
  const forceGraphRef = useRef<ForceGraphRef>(null)

  // 인증 및 이용권 체크
  useEffect(() => {
    if (authLoading) return

    if (!isAuthenticated) {
      navigate('/paywall', {
        state: { returnTo: location.pathname, companyName },
        replace: true
      })
      return
    }

    if (credits === 0) {
      navigate('/paywall', {
        state: { returnTo: location.pathname, companyName },
        replace: true
      })
    }
  }, [authLoading, isAuthenticated, credits, navigate, location.pathname, companyName])

  // 이용권 차감 (페이지 진입 시 한 번만)
  // 무제한 이용권(-1)이라도 API 호출 필요 (report_views에 저장하기 위해)
  useEffect(() => {
    let isMounted = true  // 메모리 릭 방지

    console.log('[AnalysisPage] Credit deduction useEffect triggered:', {
      authLoading, isAuthenticated, corpCode, credits, creditDeducted
    })

    if (authLoading || !isAuthenticated || !corpCode || creditDeducted) {
      console.log('[AnalysisPage] Skipping credit deduction - conditions not met')
      return
    }
    // 이용권이 0이면 조회 불가 (paywall로 이동됨)
    if (credits === 0) {
      console.log('[AnalysisPage] Skipping - credits is 0')
      return
    }

    console.log('[AnalysisPage] Starting credit deduction for:', corpCode)

    const deductCreditForReport = async () => {
      try {
        // 서버에 이용권 차감 요청
        // 무제한(-1)인 경우 백엔드에서 차감 없이 report_views만 저장
        console.log('[AnalysisPage] Calling creditService.useCreditsForReport...')
        const result = await creditService.useCreditsForReport(corpCode, companyName)
        console.log('[AnalysisPage] Credit deduction result:', result)

        if (!isMounted) return  // 언마운트 체크

        if (result.deducted && credits !== -1) {
          // 실제로 차감된 경우에만 로컬 상태 업데이트 (무제한 제외)
          console.log('[AnalysisPage] Calling deductCredit()')
          deductCredit()
        }

        setCreditDeducted(true)
        console.log('[AnalysisPage] Credit deduction completed successfully')
      } catch (err) {
        if (!isMounted) return  // 언마운트 체크
        // 에러 로깅 (디버깅용)
        console.error('[AnalysisPage] Credit deduction failed:', err)
        // 차감 실패해도 페이지는 표시 (서버에서 추후 정산)
        setCreditDeducted(true)
      }
    }

    deductCreditForReport()

    return () => {
      isMounted = false  // cleanup
    }
  }, [authLoading, isAuthenticated, corpCode, credits, creditDeducted, companyName, deductCredit])

  // 화면 크기 감지
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setDimensions({
          width: rect.width,
          height: window.innerHeight - 160, // 헤더 + 탭바 공간 제외
        })
      }
    }

    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [activeTab])

  // 데이터 로드 함수 (재시도에서도 사용)
  const loadAllData = useCallback(async () => {
    if (!corpCode) return

    // 관계도 로드 시작
    setIsGraphLoading(true)
    setGraphError(null)

    // 리포트 로드 시작
    setIsReportLoading(true)
    setReportError(null)

    try {
      // 관계도와 리포트 동시 로드 (병렬)
      const [graphResult, reportResult] = await Promise.all([
        getCompanyNetwork(corpCode, depth, NODE_LIMIT),
        getCompanyReport(corpCode)
      ])

      // 관계도 결과 적용
      setGraphData(graphResult)
      setIsNodeLimited(graphResult.isLimited)
      setOriginalNodeCount(graphResult.originalCount)

      // 리포트 결과 확인 - 에러 객체인지 체크
      if (reportResult && '_error' in reportResult) {
        const errorInfo = (reportResult as { _error: string })._error
        setReportError(`API 오류: ${errorInfo}`)
      } else if (reportResult && 'companyName' in reportResult) {
        setReportData(reportResult)
      } else {
        setReportError('리포트 데이터를 찾을 수 없습니다')
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err)
      setGraphError('데이터를 불러오는데 실패했습니다')
      setReportError(`API 에러: ${errMsg}`)
    } finally {
      setIsGraphLoading(false)
      setIsReportLoading(false)
    }
  }, [corpCode, depth])

  // 관계도 + 리포트 동시 로드 (페이지 진입 시)
  useEffect(() => {
    if (!corpCode || authLoading || !isAuthenticated || credits === 0) {
      return
    }
    loadAllData()
  }, [corpCode, depth, authLoading, isAuthenticated, credits, loadAllData])

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
      navigate(`/analysis/${node.corp_code}`, {
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

  // 리스크 색상/라벨
  const getRiskColor = (score: number) => {
    if (score <= 30) return colors.green500
    if (score <= 60) return colors.yellow500
    return colors.red500
  }

  const getRiskLabel = (score: number) => {
    if (score <= 30) return '안전'
    if (score <= 60) return '주의'
    return '위험'
  }

  // 로딩 중
  if (authLoading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: colors.white,
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: `3px solid ${colors.gray100}`,
            borderTopColor: colors.blue500,
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px',
          }} />
          <p style={{ color: colors.gray500, fontSize: '14px' }}>로딩 중...</p>
          <style>{`
            @keyframes spin {
              to { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      </div>
    )
  }

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
              maxWidth: '180px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              관계형리스크 탐색
            </h1>
          </div>

          {/* 탐색 깊이 버튼 (관계도 탭에서만) */}
          {activeTab === 'graph' && (
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
          )}
        </div>

        {/* 회사명 + ticker */}
        <div style={{
          marginTop: '8px',
          fontSize: '14px',
          color: colors.gray600,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <span>{centerCompany?.name || reportData?.companyName || companyName}</span>
          {(centerCompany?.ticker || reportData?.ticker) && (
            <span style={{
              color: '#F59E0B',
              fontWeight: '600',
            }}>
              {centerCompany?.ticker || reportData?.ticker}
            </span>
          )}
        </div>

        {/* 노드 제한 경고 */}
        {activeTab === 'graph' && isNodeLimited && (
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

      {/* 탭 바 */}
      <div style={{
        display: 'flex',
        borderBottom: `1px solid ${colors.gray100}`,
        backgroundColor: colors.white,
        position: 'sticky',
        top: '80px',
        zIndex: 99,
      }}>
        <button
          onClick={() => setActiveTab('graph')}
          style={{
            flex: 1,
            padding: '14px',
            border: 'none',
            backgroundColor: 'transparent',
            color: activeTab === 'graph' ? colors.blue500 : colors.gray500,
            fontSize: '15px',
            fontWeight: activeTab === 'graph' ? '600' : '500',
            cursor: 'pointer',
            borderBottom: activeTab === 'graph' ? `2px solid ${colors.blue500}` : '2px solid transparent',
          }}
        >
          관계도
        </button>
        <button
          onClick={() => setActiveTab('report')}
          style={{
            flex: 1,
            padding: '14px',
            border: 'none',
            backgroundColor: 'transparent',
            color: activeTab === 'report' ? colors.blue500 : colors.gray500,
            fontSize: '15px',
            fontWeight: activeTab === 'report' ? '600' : '500',
            cursor: 'pointer',
            borderBottom: activeTab === 'report' ? `2px solid ${colors.blue500}` : '2px solid transparent',
          }}
        >
          분석리포트
        </button>
      </div>

      {/* 관계도 탭 */}
      {activeTab === 'graph' && (
        <>
          <div
            ref={containerRef}
            style={{
              position: 'relative',
              width: '100%',
              height: `calc(100vh - 200px)`,
              overflow: 'hidden',
            }}
          >
            {isGraphLoading ? (
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
                </div>
              </div>
            ) : graphError ? (
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
                  <p style={{ color: colors.gray500, fontSize: '14px', marginBottom: '16px' }}>{graphError}</p>
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
          {!isGraphLoading && !graphError && filteredGraphData.nodes.length > 0 && (
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
        </>
      )}

      {/* 분석리포트 탭 */}
      {activeTab === 'report' && (
        <main style={{ padding: '16px 20px 32px' }}>
          {isReportLoading ? (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '60px 0',
            }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{
                  width: '40px',
                  height: '40px',
                  border: `3px solid ${colors.gray100}`,
                  borderTopColor: colors.blue500,
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                  margin: '0 auto 16px',
                }} />
                <p style={{ color: colors.gray500, fontSize: '14px' }}>리포트 로딩 중...</p>
              </div>
            </div>
          ) : reportError ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '60px 20px',
            }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>⚠️</div>
              <p style={{ fontSize: '14px', color: colors.gray500, marginBottom: '16px', textAlign: 'center' }}>
                {reportError}
              </p>
              <button
                onClick={() => loadAllData()}
                style={{
                  padding: '12px 24px',
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
          ) : reportData ? (
            <>
              {/* 기업 정보 카드 */}
              <section
                style={{
                  backgroundColor: colors.gray50,
                  borderRadius: '16px',
                  padding: '20px',
                  marginBottom: '12px',
                }}
              >
                <h2 style={{
                  fontSize: '22px',
                  fontWeight: '700',
                  margin: '0 0 4px 0',
                  color: colors.gray900,
                  letterSpacing: '-0.02em'
                }}>
                  {reportData.companyName}
                </h2>
                <p style={{
                  fontSize: '14px',
                  color: colors.gray500,
                  margin: 0
                }}>
                  {reportData.ticker ? `${reportData.ticker} · ` : ''}{reportData.corpCode}
                </p>
              </section>

              {/* 리스크 점수 카드 */}
              <section
                style={{
                  backgroundColor: colors.white,
                  borderRadius: '16px',
                  padding: '24px 20px',
                  marginBottom: '12px',
                  border: `1px solid ${colors.gray100}`,
                }}
              >
                <div style={{
                  fontSize: '14px',
                  color: colors.gray500,
                  marginBottom: '12px',
                  fontWeight: '500'
                }}>
                  종합 리스크 점수
                </div>
                <div style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: '8px',
                  marginBottom: '16px'
                }}>
                  <span style={{
                    fontSize: '48px',
                    fontWeight: '700',
                    color: getRiskColor(reportData.riskScore.total),
                    letterSpacing: '-0.02em'
                  }}>
                    {reportData.riskScore.total}
                  </span>
                  <span style={{
                    fontSize: '16px',
                    color: colors.gray500,
                    fontWeight: '400'
                  }}>
                    / 100
                  </span>
                  <span style={{
                    marginLeft: 'auto',
                    padding: '6px 12px',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontWeight: '600',
                    backgroundColor: getRiskColor(reportData.riskScore.total) + '20',
                    color: getRiskColor(reportData.riskScore.total),
                  }}>
                    {getRiskLabel(reportData.riskScore.total)}
                  </span>
                </div>
                {/* Progress Bar */}
                <div style={{
                  height: '8px',
                  backgroundColor: colors.gray100,
                  borderRadius: '4px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    height: '100%',
                    width: `${reportData.riskScore.total}%`,
                    backgroundColor: getRiskColor(reportData.riskScore.total),
                    borderRadius: '4px',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </section>

              {/* 통계 카드 그리드 */}
              <section style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '12px',
                marginBottom: '12px'
              }}>
                <article style={{
                  backgroundColor: colors.white,
                  padding: '20px 16px',
                  borderRadius: '16px',
                  border: `1px solid ${colors.gray100}`,
                }}>
                  <div style={{
                    fontSize: '13px',
                    color: colors.gray500,
                    marginBottom: '8px',
                    fontWeight: '500'
                  }}>
                    투자등급
                  </div>
                  <div style={{
                    fontSize: '28px',
                    fontWeight: '700',
                    color: colors.yellow500,
                    letterSpacing: '-0.02em'
                  }}>
                    {reportData.investmentGrade}
                  </div>
                </article>
                <article style={{
                  backgroundColor: colors.white,
                  padding: '20px 16px',
                  borderRadius: '16px',
                  border: `1px solid ${colors.gray100}`,
                }}>
                  <div style={{
                    fontSize: '13px',
                    color: colors.gray500,
                    marginBottom: '8px',
                    fontWeight: '500'
                  }}>
                    CB 발행
                  </div>
                  <div style={{
                    fontSize: '28px',
                    fontWeight: '700',
                    color: reportData.cbIssuances.length > 0 ? colors.red500 : colors.green500,
                    letterSpacing: '-0.02em'
                  }}>
                    {reportData.cbIssuances.length}회
                  </div>
                </article>
              </section>

              {/* 추가 정보 카드 */}
              <section style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '12px',
                marginBottom: '16px'
              }}>
                <article style={{
                  backgroundColor: colors.white,
                  padding: '20px 16px',
                  borderRadius: '16px',
                  border: `1px solid ${colors.gray100}`,
                }}>
                  <div style={{
                    fontSize: '13px',
                    color: colors.gray500,
                    marginBottom: '8px',
                    fontWeight: '500'
                  }}>
                    등기임원 수
                  </div>
                  <div style={{
                    fontSize: '28px',
                    fontWeight: '700',
                    color: colors.blue500,
                    letterSpacing: '-0.02em'
                  }}>
                    {reportData.officers.length}명
                  </div>
                </article>
                <article style={{
                  backgroundColor: colors.white,
                  padding: '20px 16px',
                  borderRadius: '16px',
                  border: `1px solid ${colors.gray100}`,
                }}>
                  <div style={{
                    fontSize: '13px',
                    color: colors.gray500,
                    marginBottom: '8px',
                    fontWeight: '500'
                  }}>
                    주주 수
                  </div>
                  <div style={{
                    fontSize: '28px',
                    fontWeight: '700',
                    color: colors.gray900,
                    letterSpacing: '-0.02em'
                  }}>
                    {reportData.shareholders.length}명
                  </div>
                </article>
              </section>

              {/* 상세 데이터 탭 */}
              <section style={{
                backgroundColor: colors.white,
                borderRadius: '16px',
                padding: '16px',
                border: `1px solid ${colors.gray100}`,
              }}>
                <DataTabs
                  cbIssuances={reportData.cbIssuances}
                  cbSubscribers={reportData.cbSubscribers}
                  officers={reportData.officers}
                  financials={reportData.financials}
                  shareholders={reportData.shareholders}
                  affiliates={reportData.affiliates}
                />
              </section>
            </>
          ) : null}
        </main>
      )}
    </div>
  )
}

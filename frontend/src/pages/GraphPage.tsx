import { useState, useRef, useCallback, useEffect, useMemo } from 'react'
import { useParams, Link, useSearchParams, useNavigate } from 'react-router-dom'
import * as d3 from 'd3'
import { ForceGraph, NodeDetailPanel, GraphControls, NavigationButtons, Breadcrumb, MiniStockChart } from '../components/graph'
import type { ForceGraphRef } from '../components/graph'
import type { GraphNode, GraphData, NodeType } from '../types/graph'
import { NODE_LIMIT, DEFAULT_DEPTH, type DateRangeParams, extractQueryLimitError, type QueryLimitError } from '../api/graph'
import { DateRangePicker, type DateRange, BottomSheet, MarketBadge, TradingStatusBadge } from '../components/common'
import { useGraphQuery } from '../hooks/useGraphQuery'
import { useGraphStore, selectCanGoBack, selectCanGoForward } from '../store'
import { getRaymondsIndexById } from '../api/raymondsIndex'
import type { RaymondsIndexData } from '../types/raymondsIndex'
import { getGradeColor } from '../types/raymondsIndex'

// URL 파라미터에서 날짜 파싱
function parseDateFromUrl(dateStr: string | null): Date | null {
  if (!dateStr) return null
  const date = new Date(dateStr)
  return isNaN(date.getTime()) ? null : date
}

// 날짜를 URL 파라미터 형식으로 변환
function formatDateForUrl(date: Date | string | null): string | null {
  if (!date) return null
  // 문자열인 경우 (localStorage에서 복원된 경우)
  if (typeof date === 'string') {
    return date.split('T')[0]
  }
  // Date 객체인 경우
  if (date instanceof Date && !isNaN(date.getTime())) {
    return date.toISOString().split('T')[0]
  }
  return null
}

function GraphPage() {
  const { companyId } = useParams<{ companyId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  // URL에서 초기값 읽기
  const initialDepth = parseInt(searchParams.get('depth') || String(DEFAULT_DEPTH), 10)
  const initialDateFrom = parseDateFromUrl(searchParams.get('from'))
  const initialDateTo = parseDateFromUrl(searchParams.get('to'))

  // Zustand UI 상태
  const {
    selectedNodeId,
    visibleNodeTypes,
    dateRange: storedDateRange,
    navigationHistory,
    navigationIndex,
    selectNode,
    toggleNodeType,
    setDateRange: setStoredDateRange,
    pushNavigation,
    goBack: storeGoBack,
    goForward: storeGoForward,
    navigateToIndex,
  } = useGraphStore()

  const canGoBack = useGraphStore(selectCanGoBack)
  const canGoForward = useGraphStore(selectCanGoForward)

  // 로컬 상태 (URL 파라미터 연동)
  const [depth, setDepth] = useState(initialDepth)
  const [dateRange, setDateRange] = useState<DateRange>({
    startDate: initialDateFrom ?? storedDateRange.startDate,
    endDate: initialDateTo ?? storedDateRange.endDate,
    reportYears: storedDateRange.reportYears,  // store에서 reportYears 가져오기
  })

  // refs
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
  const svgRef = useRef<SVGSVGElement | null>(null)
  const forceGraphRef = useRef<ForceGraphRef>(null)

  // 모바일 상태
  const [isMobile, setIsMobile] = useState(false)
  const [showMobileFilters, setShowMobileFilters] = useState(false)

  // 전체화면 모드 상태
  const [isFullscreen, setIsFullscreen] = useState(false)

  // RaymondsIndex 데이터
  const [raymondsIndex, setRaymondsIndex] = useState<RaymondsIndexData | null>(null)

  // 조회 제한 에러 정보
  const [queryLimitInfo, setQueryLimitInfo] = useState<QueryLimitError | null>(null)

  // 날짜를 YYYY-MM-DD 형식으로 변환
  const formatDateParam = (date: Date | string | null | undefined): string | undefined => {
    if (!date) return undefined
    // Date 객체인 경우
    if (date instanceof Date) {
      return isNaN(date.getTime()) ? undefined : date.toISOString().split('T')[0]
    }
    // 문자열인 경우 (이미 YYYY-MM-DD 형식)
    if (typeof date === 'string') {
      return date.split('T')[0]
    }
    return undefined
  }

  // 날짜 범위 파라미터 생성 (report_years 기반)
  const dateRangeParams: DateRangeParams | undefined = useMemo(() => {
    // reportYears가 있으면 우선 사용 (사업보고서 연도 기반)
    if (dateRange.reportYears && dateRange.reportYears.length > 0) {
      return { report_years: dateRange.reportYears }
    }
    // 기존 날짜 범위 방식 (fallback)
    const date_from = formatDateParam(dateRange.startDate)
    const date_to = formatDateParam(dateRange.endDate)
    if (!date_from && !date_to) return undefined
    return { date_from, date_to }
  }, [dateRange])

  // React Query - 그래프 데이터 fetch
  const {
    data: graphData,
    isLoading,
    error,
    refetch,
  } = useGraphQuery(companyId, depth, dateRangeParams)

  // 실제 그래프 데이터 (로딩 중 빈 데이터)
  const actualGraphData: GraphData = graphData ?? { nodes: [], links: [] }
  const isNodeLimited = graphData?.isLimited ?? false
  const originalNodeCount = graphData?.originalCount ?? 0

  // 선택된 노드 객체
  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null
    return actualGraphData.nodes.find(n => n.id === selectedNodeId) ?? null
  }, [selectedNodeId, actualGraphData.nodes])

  // URL 파라미터 동기화
  useEffect(() => {
    const params = new URLSearchParams()
    if (depth !== DEFAULT_DEPTH) {
      params.set('depth', String(depth))
    }
    const fromStr = formatDateForUrl(dateRange.startDate)
    const toStr = formatDateForUrl(dateRange.endDate)
    if (fromStr) params.set('from', fromStr)
    if (toStr) params.set('to', toStr)

    // URL 업데이트 (히스토리에 추가하지 않고 replace)
    setSearchParams(params, { replace: true })
  }, [depth, dateRange, setSearchParams])

  // 컨테이너 크기 및 모바일 감지
  useEffect(() => {
    const updateDimensions = () => {
      const mobile = window.innerWidth < 768
      setIsMobile(mobile)

      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setDimensions({
          width: rect.width,
          height: mobile ? window.innerHeight - 120 : Math.max(rect.height, 500),
        })
      }
    }

    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  // SVG ref 저장 (줌 컨트롤용)
  useEffect(() => {
    const svg = containerRef.current?.querySelector('svg')
    if (svg) {
      svgRef.current = svg as SVGSVGElement
    }
  }, [dimensions, actualGraphData])

  // 중심 회사 정보 (corp_code 또는 id로 검색)
  const centerCompany = actualGraphData.nodes.find(n =>
    n.type === 'company' && (n.corp_code === companyId || n.id === companyId)
  )

  // 네비게이션 히스토리에 현재 회사 추가
  useEffect(() => {
    if (companyId && centerCompany?.name) {
      pushNavigation(companyId, centerCompany.name)
    }
  }, [companyId, centerCompany?.name, pushNavigation])

  // RaymondsIndex 데이터 로드
  useEffect(() => {
    const loadRaymondsIndex = async () => {
      if (!companyId) return
      try {
        const data = await getRaymondsIndexById(companyId)
        setRaymondsIndex(data)
      } catch {
        // RaymondsIndex 로드 실패는 무시 (Optional 데이터)
        setRaymondsIndex(null)
      }
    }
    loadRaymondsIndex()
  }, [companyId])

  // API 연결 상태
  const isApiConnected = !error && actualGraphData.nodes.length > 0

  // 조회 제한 에러 감지
  useEffect(() => {
    if (error) {
      const limitError = extractQueryLimitError(error)
      if (limitError) {
        setQueryLimitInfo(limitError)
      }
    }
  }, [error])

  // 노드 클릭 핸들러
  const handleNodeClick = useCallback((node: GraphNode | null) => {
    selectNode(node?.id ?? null)
  }, [selectNode])

  // 노드 재중심 핸들러
  const handleRecenter = useCallback((node: GraphNode) => {
    forceGraphRef.current?.centerOnNode(node)
  }, [])

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

  // 재시도 핸들러
  const handleRetry = useCallback(() => {
    refetch()
  }, [refetch])

  // 탐색 깊이 변경 핸들러
  const handleDepthChange = useCallback((newDepth: number) => {
    setDepth(Math.max(1, Math.min(3, newDepth)))
  }, [])

  // 날짜 범위 변경 핸들러
  const handleDateRangeChange = useCallback((range: DateRange) => {
    setDateRange(range)
    setStoredDateRange(range)
  }, [setStoredDateRange])

  // 노드 타입 토글
  const handleToggleNodeType = useCallback((type: NodeType) => {
    toggleNodeType(type)
  }, [toggleNodeType])

  // 네비게이션 핸들러
  const handleGoBack = useCallback(() => {
    const entry = storeGoBack()
    if (entry) {
      navigate(`/company/${entry.companyId}/graph`)
    }
  }, [storeGoBack, navigate])

  const handleGoForward = useCallback(() => {
    const entry = storeGoForward()
    if (entry) {
      navigate(`/company/${entry.companyId}/graph`)
    }
  }, [storeGoForward, navigate])

  // 회사 노드 클릭으로 네비게이션
  const handleNavigateToCompany = useCallback((node: GraphNode) => {
    if (node.type === 'company' && node.id !== companyId) {
      pushNavigation(node.id, node.name)
      navigate(`/company/${node.id}/graph`)
    }
  }, [companyId, pushNavigation, navigate])

  // 브레드크럼에서 특정 위치로 이동
  const handleBreadcrumbNavigate = useCallback((targetCompanyId: string, _targetCompanyName: string) => {
    // 히스토리에서 해당 인덱스 찾기
    const targetIndex = navigationHistory.findIndex(
      entry => entry.companyId === targetCompanyId
    )
    if (targetIndex !== -1) {
      navigateToIndex(targetIndex)
      navigate(`/company/${targetCompanyId}/graph`)
    }
  }, [navigationHistory, navigateToIndex, navigate])

  // 전체화면 토글
  const toggleFullscreen = useCallback(() => {
    setIsFullscreen(prev => !prev)
    selectNode(null) // 전체화면 전환 시 선택 해제
  }, [selectNode])

  // 전체화면에서 빈 영역 클릭 시 원래 화면으로 복귀
  const handleFullscreenBackgroundClick = useCallback((e: React.MouseEvent) => {
    // 이벤트가 SVG 배경에서 발생했는지 확인 (노드나 다른 요소가 아닌 경우)
    const target = e.target as Element
    if (target.tagName === 'svg' || target.classList.contains('fullscreen-overlay')) {
      setIsFullscreen(false)
    }
  }, [])

  // ESC 키로 전체화면 해제
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isFullscreen])

  // 키보드 단축키 (Alt+← / Alt+→)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && e.key === 'ArrowLeft' && canGoBack) {
        e.preventDefault()
        handleGoBack()
      }
      if (e.altKey && e.key === 'ArrowRight' && canGoForward) {
        e.preventDefault()
        handleGoForward()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [canGoBack, canGoForward, handleGoBack, handleGoForward])

  // 필터링된 그래프 데이터
  const filteredGraphData = useMemo(() => {
    const visibleNodes = actualGraphData.nodes.filter(node =>
      visibleNodeTypes.has(node.type)
    )
    const visibleNodeIds = new Set(visibleNodes.map(n => n.id))

    const visibleLinks = actualGraphData.links.filter(link => {
      const sourceId = typeof link.source === 'string' ? link.source : (link.source as GraphNode).id
      const targetId = typeof link.target === 'string' ? link.target : (link.target as GraphNode).id
      return visibleNodeIds.has(sourceId) && visibleNodeIds.has(targetId)
    })

    return { nodes: visibleNodes, links: visibleLinks }
  }, [actualGraphData, visibleNodeTypes])

  // 노드 타입별 카운트
  const nodeCounts = useMemo(() => {
    const counts: Record<NodeType, number> = {
      company: 0,
      officer: 0,
      subscriber: 0,
      cb: 0,
      shareholder: 0,
      affiliate: 0,
    }
    actualGraphData.nodes.forEach(node => {
      counts[node.type]++
    })
    return counts
  }, [actualGraphData])

  return (
    <div className="h-full flex flex-col -mx-4 sm:-mx-6 lg:-mx-8 -my-6">
      {/* API 연결 상태 배너 - 모바일에서 숨김 */}
      {!isApiConnected && !isLoading && (
        <div className="hidden md:flex mx-4 sm:mx-6 lg:mx-8 mt-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg items-center gap-2 text-amber-400">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="text-sm">API 연결 실패 - 더미 데이터를 표시합니다</span>
        </div>
      )}

      {/* 노드 수 제한 경고 배너 - 모바일에서 축소 */}
      {isNodeLimited && !isLoading && (
        <div className="hidden md:flex mx-4 sm:mx-6 lg:mx-8 mt-4 p-3 bg-accent-info/10 border border-accent-info/30 rounded-lg items-center justify-between">
          <div className="flex items-center gap-2 text-accent-info">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm">
              노드 수가 많아 상위 {NODE_LIMIT}개만 표시합니다 (전체 {originalNodeCount}개)
            </span>
          </div>
          <span className="text-xs text-accent-info/70">
            중요도(회사 우선, 연결 수)순으로 필터링됨
          </span>
        </div>
      )}

      {/* 상단 네비게이션 - 모바일 최적화 */}
      <div className="px-4 sm:px-6 lg:px-8 py-3 md:py-4 border-b border-theme-border bg-theme-surface/80 backdrop-blur-xl">
        <div className="flex items-center justify-between">
          {/* 모바일: 간소화된 네비게이션 */}
          <div className="flex items-center gap-2 md:gap-4">
            <Link to="/" className="text-accent-primary hover:text-accent-primary/80 p-1.5 md:p-0 md:flex md:items-center md:gap-1 text-sm transition-colors">
              <svg className="w-5 h-5 md:w-4 md:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              <span className="hidden md:inline">검색으로</span>
            </Link>
            <span className="hidden md:inline text-dark-border">|</span>
            {/* 네비게이션 버튼 - 모바일에서 숨김 */}
            <div className="hidden md:flex items-center gap-4">
              <NavigationButtons
                canGoBack={canGoBack}
                canGoForward={canGoForward}
                onGoBack={handleGoBack}
                onGoForward={handleGoForward}
              />
              <span className="text-dark-border">|</span>
            </div>
            <h1 className="text-base md:text-lg font-semibold text-text-primary flex items-center gap-1.5">
              <span className="truncate max-w-[120px] md:max-w-[200px]">{centerCompany?.name || '회사'}</span>
              {centerCompany?.ticker && <span className="text-yellow-400 font-mono text-sm flex-shrink-0">{centerCompany.ticker}</span>}
              {centerCompany?.market && (
                <MarketBadge
                  market={centerCompany.market}
                  tradingStatus={centerCompany.tradingStatus}
                  size="sm"
                  className="flex-shrink-0"
                />
              )}
              {centerCompany?.tradingStatus && centerCompany.tradingStatus !== 'NORMAL' && (
                <TradingStatusBadge status={centerCompany.tradingStatus} className="flex-shrink-0" />
              )}
              <span className="hidden md:inline text-text-muted font-normal flex-shrink-0">관계도</span>
            </h1>
          </div>
          {/* 모바일: 보고서 버튼 아이콘만 */}
          <Link
            to={`/company/${companyId}/report`}
            className="p-2.5 md:px-4 md:py-2 bg-purple-500/20 text-purple-400 text-sm font-medium rounded-lg border border-purple-500/30 hover:bg-purple-500/30 hover:border-purple-500/50 transition-all shadow-[0_0_10px_rgba(168,85,247,0.2)] flex items-center gap-2"
          >
            <svg className="w-5 h-5 md:w-4 md:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span className="hidden md:inline">분석 보고서</span>
          </Link>
        </div>
      </div>

      {/* 브레드크럼 (탐색 기록) - 모바일에서 숨김 */}
      {navigationHistory.length > 1 && (
        <div className="hidden md:block mx-4 sm:mx-6 lg:mx-8 mt-4 bg-theme-card rounded-lg px-4 py-2 border border-theme-border">
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted flex-shrink-0 uppercase tracking-wide">탐색 경로</span>
            <Breadcrumb
              history={navigationHistory}
              currentIndex={navigationIndex}
              onNavigate={handleBreadcrumbNavigate}
              maxVisible={5}
            />
          </div>
        </div>
      )}

      {/* 필터 영역 - 데스크톱 */}
      <div className="hidden md:block mx-4 sm:mx-6 lg:mx-8 mt-4 bg-theme-card rounded-xl border border-theme-border p-4">
        <div className="flex flex-wrap items-center gap-6">
          {/* 관계형리스크등급 */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-text-muted uppercase tracking-wide">관계형리스크</span>
            <span className={`text-2xl font-bold font-mono ${
              centerCompany?.investment_grade === 'A' ? 'text-blue-400' :
              centerCompany?.investment_grade === 'AA' ? 'text-blue-400' :
              centerCompany?.investment_grade === 'AAA' ? 'text-blue-400' :
              centerCompany?.investment_grade === 'B' ? 'text-green-400' :
              centerCompany?.investment_grade === 'BB' ? 'text-green-400' :
              centerCompany?.investment_grade === 'BBB' ? 'text-green-400' :
              centerCompany?.investment_grade === 'C' ? 'text-yellow-400' :
              centerCompany?.investment_grade === 'CC' ? 'text-yellow-400' :
              centerCompany?.investment_grade === 'CCC' ? 'text-yellow-400' :
              centerCompany?.investment_grade === 'D' ? 'text-orange-400' :
              centerCompany?.investment_grade === 'E' ? 'text-red-400' :
              'text-text-muted'
            }`}>
              {centerCompany?.investment_grade || '-'}
            </span>
          </div>

          <div className="w-px h-8 bg-theme-border" />

          {/* RaymondsIndex */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-text-muted uppercase tracking-wide">RIndex</span>
            {raymondsIndex ? (
              <div className="flex items-center gap-1.5">
                <span
                  className="text-2xl font-bold font-mono"
                  style={{ color: getGradeColor(raymondsIndex.grade) }}
                >
                  {raymondsIndex.totalScore.toFixed(0)}
                </span>
                <span
                  className="text-sm font-medium px-1.5 py-0.5 rounded"
                  style={{
                    color: getGradeColor(raymondsIndex.grade),
                    backgroundColor: `${getGradeColor(raymondsIndex.grade)}20`
                  }}
                >
                  {raymondsIndex.grade}
                </span>
              </div>
            ) : (
              <span className="text-text-muted text-sm">-</span>
            )}
          </div>

          <div className="w-px h-8 bg-theme-border" />

          {/* 탐색 깊이 */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-medium text-text-muted uppercase tracking-wide">탐색 깊이</span>
              {/* 도움말 아이콘 */}
              <div className="relative group">
                <svg className="w-4 h-4 text-text-muted cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {/* 툴팁 */}
                <div className="absolute left-0 top-6 w-72 p-3 bg-theme-surface border border-theme-border rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
                  <p className="text-xs font-semibold text-text-primary mb-2">탐색 깊이 설명</p>
                  <div className="space-y-2 text-xs text-text-secondary">
                    <div className="flex gap-2">
                      <span className="text-cyan-400 font-medium w-12">1단계</span>
                      <span>임원 + CB 회차</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-cyan-400 font-medium w-12">2단계</span>
                      <span>1단계 + CB 인수대상자</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-cyan-400 font-medium w-12">3단계</span>
                      <span>2단계 + 임원의 타 상장사 경력 + 인수자의 타 상장사 CB 투자</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex gap-1">
              {[1, 2, 3].map(d => {
                const depthDescriptions: Record<number, string> = {
                  1: '임원 + CB 회차',
                  2: '+ CB 인수자',
                  3: '+ 타사 경력/투자',
                }
                return (
                  <button
                    key={d}
                    onClick={() => handleDepthChange(d)}
                    className={`px-3 py-1.5 text-sm rounded-lg border transition-all font-medium ${
                      depth === d
                        ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/50 shadow-[0_0_10px_rgba(34,211,238,0.3)]'
                        : 'bg-theme-surface text-text-secondary border-theme-border hover:border-cyan-500/30 hover:text-cyan-400 hover:bg-cyan-500/5'
                    }`}
                    title={depthDescriptions[d]}
                  >
                    {d}단계
                  </button>
                )
              })}
            </div>
          </div>

          <div className="w-px h-8 bg-theme-border" />

          {/* 날짜 범위 */}
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-text-muted uppercase tracking-wide">기간 필터</span>
            <DateRangePicker
              onChange={handleDateRangeChange}
            />
          </div>

          {/* 주가 흐름 미니 차트 */}
          {companyId && (
            <>
              <div className="w-px h-8 bg-theme-border" />
              <MiniStockChart companyId={companyId} companyName={centerCompany?.name} />
            </>
          )}
        </div>
      </div>

      {/* 모바일 필터 토글 버튼 */}
      <div className="md:hidden mx-4 mt-2">
        <button
          onClick={() => setShowMobileFilters(!showMobileFilters)}
          className="w-full py-2.5 px-4 bg-theme-card border border-theme-border rounded-lg flex items-center justify-between"
        >
          <span className="text-sm text-text-secondary">
            필터: {depth}단계
          </span>
          <svg className={`w-4 h-4 text-text-muted transition-transform ${showMobileFilters ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {/* 모바일 필터 드롭다운 */}
        {showMobileFilters && (
          <div className="mt-2 p-3 bg-theme-card border border-theme-border rounded-lg space-y-3">
            <div>
              <span className="text-sm font-medium text-text-muted uppercase tracking-wide">탐색 깊이</span>
              <div className="flex gap-2 mt-2">
                {[1, 2, 3].map(d => (
                  <button
                    key={d}
                    onClick={() => handleDepthChange(d)}
                    className={`flex-1 py-2.5 text-sm rounded-lg border transition-all font-medium ${
                      depth === d
                        ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/50'
                        : 'bg-theme-surface text-text-secondary border-theme-border'
                    }`}
                  >
                    {d}단계
                  </button>
                ))}
              </div>
            </div>
            <div>
              <span className="text-sm font-medium text-text-muted uppercase tracking-wide">기간 필터</span>
              <div className="mt-2">
                <DateRangePicker onChange={handleDateRangeChange} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 모바일 RaymondsIndex & 주가 차트 영역 */}
      <div className="md:hidden mx-4 mt-2 bg-theme-card border border-theme-border rounded-lg p-3">
        <div className="flex items-center justify-between gap-3">
          {/* 관계형리스크등급 */}
          <div className="flex flex-col items-center">
            <span className="text-[10px] text-text-muted uppercase">관계형리스크</span>
            <span className={`text-xl font-bold font-mono ${
              centerCompany?.investment_grade === 'A' ? 'text-blue-400' :
              centerCompany?.investment_grade === 'AA' ? 'text-blue-400' :
              centerCompany?.investment_grade === 'AAA' ? 'text-blue-400' :
              centerCompany?.investment_grade === 'B' ? 'text-green-400' :
              centerCompany?.investment_grade === 'BB' ? 'text-green-400' :
              centerCompany?.investment_grade === 'BBB' ? 'text-green-400' :
              centerCompany?.investment_grade === 'C' ? 'text-yellow-400' :
              centerCompany?.investment_grade === 'CC' ? 'text-yellow-400' :
              centerCompany?.investment_grade === 'CCC' ? 'text-yellow-400' :
              centerCompany?.investment_grade === 'D' ? 'text-orange-400' :
              centerCompany?.investment_grade === 'E' ? 'text-red-400' :
              'text-text-muted'
            }`}>
              {centerCompany?.investment_grade || '-'}
            </span>
          </div>

          <div className="w-px h-10 bg-theme-border" />

          {/* RaymondsIndex */}
          <div className="flex flex-col items-center">
            <span className="text-[10px] text-text-muted uppercase">RIndex</span>
            {raymondsIndex ? (
              <div className="flex items-center gap-1">
                <span
                  className="text-xl font-bold font-mono"
                  style={{ color: getGradeColor(raymondsIndex.grade) }}
                >
                  {raymondsIndex.totalScore.toFixed(0)}
                </span>
                <span
                  className="text-xs font-medium px-1 py-0.5 rounded"
                  style={{
                    color: getGradeColor(raymondsIndex.grade),
                    backgroundColor: `${getGradeColor(raymondsIndex.grade)}20`
                  }}
                >
                  {raymondsIndex.grade}
                </span>
              </div>
            ) : (
              <span className="text-text-muted text-sm">-</span>
            )}
          </div>

          <div className="w-px h-10 bg-theme-border" />

          {/* 주가 차트 */}
          {companyId && (
            <div className="flex-1 min-w-0">
              <MiniStockChart companyId={companyId} companyName={centerCompany?.name} />
            </div>
          )}
        </div>
      </div>

      {/* 메인 컨텐츠 */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-4 gap-4 min-h-0 px-4 sm:px-6 lg:px-8 py-4">
        {/* 그래프 영역 */}
        <div
          ref={containerRef}
          className="col-span-1 md:col-span-3 bg-theme-card rounded-xl border border-theme-border relative overflow-hidden"
        >
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-theme-bg/50">
              <div className="flex flex-col items-center gap-3">
                <div className="w-10 h-10 border-2 border-accent-primary border-t-transparent rounded-full animate-spin" />
                <p className="text-text-secondary text-sm">그래프 로딩 중...</p>
              </div>
            </div>
          ) : error && queryLimitInfo ? (
            // 조회 제한 에러 - 별도 UI 표시 (모달은 아래에서 처리)
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex flex-col items-center gap-4 text-center max-w-sm px-4">
                <div className="w-16 h-16 rounded-full bg-accent-warning/20 flex items-center justify-center">
                  <svg className="w-8 h-8 text-accent-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-text-primary mb-2">이용권이 필요합니다</h3>
                  <p className="text-text-secondary text-sm">{queryLimitInfo.message}</p>
                </div>
                <button
                  onClick={() => navigate('/pricing')}
                  className="px-6 py-2.5 bg-accent-primary hover:bg-accent-primary/90 text-white text-sm font-medium rounded-lg transition-all"
                >
                  이용권 확인하기
                </button>
              </div>
            </div>
          ) : error ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex flex-col items-center gap-3 text-center">
                <div className="w-12 h-12 rounded-full bg-accent-danger/20 flex items-center justify-center">
                  <svg className="w-6 h-6 text-accent-danger" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="text-text-secondary text-sm">{error.message || '그래프 데이터를 불러오는데 실패했습니다'}</p>
                <button
                  onClick={handleRetry}
                  className="px-4 py-2 bg-blue-500/20 text-blue-400 text-sm font-medium rounded-lg border border-blue-500/30 hover:bg-blue-500/30 hover:border-blue-500/50 transition-all"
                >
                  다시 시도
                </button>
              </div>
            </div>
          ) : filteredGraphData.nodes.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex flex-col items-center gap-3 text-center">
                <div className="w-12 h-12 rounded-full bg-theme-hover flex items-center justify-center">
                  <svg className="w-6 h-6 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <p className="text-text-muted text-sm">관계 데이터가 없습니다</p>
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
                onNavigateToCompany={handleNavigateToCompany}
                selectedNodeId={selectedNode?.id}
                centerCompanyId={companyId}
              />
              <GraphControls
                onZoomIn={handleZoomIn}
                onZoomOut={handleZoomOut}
                onReset={handleReset}
                visibleNodeTypes={visibleNodeTypes}
                onToggleNodeType={handleToggleNodeType}
                nodeCounts={nodeCounts}
              />
              {/* 전체보기 버튼 - 우측 상단 */}
              <button
                onClick={toggleFullscreen}
                className="absolute top-3 right-3 z-20 p-2.5 bg-theme-card/90 backdrop-blur-sm border border-theme-border rounded-lg
                          hover:bg-accent-primary/20 hover:border-accent-primary/50 transition-all
                          text-text-secondary hover:text-accent-primary shadow-lg"
                title="전체화면으로 보기"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                </svg>
              </button>
            </>
          )}
        </div>

        {/* 사이드 패널 - 데스크톱 */}
        <div className="hidden md:block bg-theme-card rounded-xl border border-theme-border p-4">
          <NodeDetailPanel
            node={selectedNode}
            onClose={() => selectNode(null)}
            onRecenter={handleRecenter}
            onNavigateToCompany={handleNavigateToCompany}
            centerCompanyId={companyId}
          />
        </div>
      </div>

      {/* 모바일 노드 상세 BottomSheet */}
      {isMobile && (
        <BottomSheet
          isOpen={!!selectedNode}
          onClose={() => selectNode(null)}
          title={selectedNode?.name || '노드 상세'}
          minHeight={35}
          maxHeight={70}
        >
          <div className="p-4">
            <NodeDetailPanel
              node={selectedNode}
              onClose={() => selectNode(null)}
              onRecenter={handleRecenter}
              onNavigateToCompany={handleNavigateToCompany}
              centerCompanyId={companyId}
            />
          </div>
        </BottomSheet>
      )}

      {/* 하단 통계 - 데스크톱 */}
      <div className="hidden md:block mx-4 sm:mx-6 lg:mx-8 mb-4 bg-theme-card rounded-xl border border-theme-border p-4">
        <div className="flex items-center justify-around text-center">
          <div>
            <p className="text-2xl font-bold font-mono text-data-company">
              {filteredGraphData.nodes.filter(n => n.type === 'company').length}
              {nodeCounts.company !== filteredGraphData.nodes.filter(n => n.type === 'company').length && (
                <span className="text-xs text-text-muted font-normal ml-1">/{nodeCounts.company}</span>
              )}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wide mt-1">관련 회사</p>
          </div>
          <div className="w-px h-10 bg-theme-border" />
          <div>
            <p className="text-2xl font-bold font-mono text-data-officer">
              {filteredGraphData.nodes.filter(n => n.type === 'officer').length}
              {nodeCounts.officer !== filteredGraphData.nodes.filter(n => n.type === 'officer').length && (
                <span className="text-xs text-text-muted font-normal ml-1">/{nodeCounts.officer}</span>
              )}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wide mt-1">임원</p>
          </div>
          <div className="w-px h-10 bg-theme-border" />
          <div>
            <p className="text-2xl font-bold font-mono text-data-subscriber">
              {filteredGraphData.nodes.filter(n => n.type === 'subscriber').length}
              {nodeCounts.subscriber !== filteredGraphData.nodes.filter(n => n.type === 'subscriber').length && (
                <span className="text-xs text-text-muted font-normal ml-1">/{nodeCounts.subscriber}</span>
              )}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wide mt-1">CB 투자자</p>
          </div>
          <div className="w-px h-10 bg-theme-border" />
          <div>
            <p className="text-2xl font-bold font-mono text-data-cb">
              {filteredGraphData.nodes.filter(n => n.type === 'cb').length}
              {nodeCounts.cb !== filteredGraphData.nodes.filter(n => n.type === 'cb').length && (
                <span className="text-xs text-text-muted font-normal ml-1">/{nodeCounts.cb}</span>
              )}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wide mt-1">전환사채</p>
          </div>
          <div className="w-px h-10 bg-theme-border" />
          <div>
            <p className="text-2xl font-bold font-mono text-text-secondary">
              {filteredGraphData.links.length}
              {actualGraphData.links.length !== filteredGraphData.links.length && (
                <span className="text-xs text-text-muted font-normal ml-1">/{actualGraphData.links.length}</span>
              )}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wide mt-1">관계 수</p>
          </div>
        </div>
      </div>

      {/* 하단 통계 - 모바일 (간소화) */}
      <div className="md:hidden mx-4 mb-4 bg-theme-card rounded-xl border border-theme-border p-3">
        <div className="flex items-center justify-around text-center">
          <div>
            <p className="text-lg font-bold font-mono text-data-company">
              {filteredGraphData.nodes.filter(n => n.type === 'company').length}
            </p>
            <p className="text-[10px] text-text-muted">회사</p>
          </div>
          <div className="w-px h-8 bg-theme-border" />
          <div>
            <p className="text-lg font-bold font-mono text-data-officer">
              {filteredGraphData.nodes.filter(n => n.type === 'officer').length}
            </p>
            <p className="text-[10px] text-text-muted">임원</p>
          </div>
          <div className="w-px h-8 bg-theme-border" />
          <div>
            <p className="text-lg font-bold font-mono text-data-cb">
              {filteredGraphData.nodes.filter(n => n.type === 'cb').length}
            </p>
            <p className="text-[10px] text-text-muted">CB</p>
          </div>
          <div className="w-px h-8 bg-theme-border" />
          <div>
            <p className="text-lg font-bold font-mono text-text-secondary">
              {filteredGraphData.links.length}
            </p>
            <p className="text-[10px] text-text-muted">관계</p>
          </div>
        </div>
      </div>

      {/* 모바일 플로팅 컨트롤 버튼 */}
      {isMobile && !isLoading && filteredGraphData.nodes.length > 0 && (
        <div className="fixed bottom-24 right-4 flex flex-col gap-2 z-30">
          <button
            onClick={handleZoomIn}
            className="w-12 h-12 bg-theme-card border border-theme-border rounded-full shadow-lg flex items-center justify-center text-text-secondary active:bg-theme-hover"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
            </svg>
          </button>
          <button
            onClick={handleZoomOut}
            className="w-12 h-12 bg-theme-card border border-theme-border rounded-full shadow-lg flex items-center justify-center text-text-secondary active:bg-theme-hover"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
            </svg>
          </button>
          <button
            onClick={handleReset}
            className="w-12 h-12 bg-theme-card border border-theme-border rounded-full shadow-lg flex items-center justify-center text-text-secondary active:bg-theme-hover"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      )}

      {/* 전체화면 오버레이 */}
      {isFullscreen && filteredGraphData.nodes.length > 0 && (
        <div
          className="fullscreen-overlay fixed inset-0 z-50 bg-theme-bg"
          onClick={handleFullscreenBackgroundClick}
        >
          {/* 상단 헤더 */}
          <div className="absolute top-0 left-0 right-0 z-10 px-4 py-3 bg-gradient-to-b from-theme-bg via-theme-bg/80 to-transparent">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-text-primary">
                {centerCompany?.name || '회사'} 관계도
              </h2>
              <button
                onClick={() => setIsFullscreen(false)}
                className="p-2.5 bg-theme-card/90 backdrop-blur-sm border border-theme-border rounded-lg
                          hover:bg-accent-primary/20 hover:border-accent-primary/50 transition-all
                          text-text-secondary hover:text-accent-primary"
                title="전체화면 닫기 (ESC)"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* 전체화면 그래프 */}
          <div className="w-full h-full" onClick={handleFullscreenBackgroundClick}>
            <ForceGraph
              ref={forceGraphRef}
              data={filteredGraphData}
              width={window.innerWidth}
              height={window.innerHeight}
              onNodeClick={handleNodeClick}
              onNavigateToCompany={handleNavigateToCompany}
              selectedNodeId={selectedNode?.id}
              centerCompanyId={companyId}
            />
          </div>

          {/* 줌 컨트롤 - 우측 하단 */}
          <div className="absolute bottom-6 right-6 flex flex-col gap-2 z-10">
            <button
              onClick={handleZoomIn}
              className="w-12 h-12 bg-theme-card/90 backdrop-blur-sm border border-theme-border rounded-full shadow-lg flex items-center justify-center text-text-secondary hover:text-accent-primary hover:border-accent-primary/50 transition-all"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
              </svg>
            </button>
            <button
              onClick={handleZoomOut}
              className="w-12 h-12 bg-theme-card/90 backdrop-blur-sm border border-theme-border rounded-full shadow-lg flex items-center justify-center text-text-secondary hover:text-accent-primary hover:border-accent-primary/50 transition-all"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
              </svg>
            </button>
            <button
              onClick={handleReset}
              className="w-12 h-12 bg-theme-card/90 backdrop-blur-sm border border-theme-border rounded-full shadow-lg flex items-center justify-center text-text-secondary hover:text-accent-primary hover:border-accent-primary/50 transition-all"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>

          {/* 안내 텍스트 - 하단 중앙 */}
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10">
            <p className="text-xs text-text-muted bg-theme-card/80 backdrop-blur-sm px-3 py-1.5 rounded-full border border-theme-border">
              빈 영역을 클릭하거나 ESC 키를 눌러 닫기
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default GraphPage

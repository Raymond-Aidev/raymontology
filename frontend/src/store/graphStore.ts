import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { NodeType } from '../types/graph'

// 현재 연도 (기본 필터 적용용)
const CURRENT_YEAR = new Date().getFullYear()

// 날짜 범위 타입
export interface DateRange {
  startDate: Date | null
  endDate: Date | null
  reportYears?: number[]  // 사업보고서 연도 목록 (예: [2025], [2023, 2024, 2025])
}

// 네비게이션 항목
export interface NavigationEntry {
  companyId: string
  companyName: string
  timestamp: number
}

// UI 상태만 관리하는 그래프 스토어
interface GraphUIState {
  // 선택/호버 상태
  selectedNodeId: string | null
  hoveredNodeId: string | null

  // 사이드 패널 상태
  sidePanelOpen: boolean

  // 필터
  visibleNodeTypes: Set<NodeType>
  dateRange: DateRange

  // 네비게이션 히스토리
  navigationHistory: NavigationEntry[]
  navigationIndex: number

  // 액션
  selectNode: (nodeId: string | null) => void
  hoverNode: (nodeId: string | null) => void
  setSidePanelOpen: (open: boolean) => void
  toggleNodeType: (type: NodeType) => void
  setDateRange: (range: DateRange) => void

  // 네비게이션 액션
  pushNavigation: (companyId: string, companyName: string) => void
  goBack: () => NavigationEntry | null
  goForward: () => NavigationEntry | null
  navigateToIndex: (index: number) => NavigationEntry | null
  clearNavigation: () => void

  // 사용자별 데이터 관리
  currentUserId: string | null
  setCurrentUserId: (userId: string | null) => void

  // 초기화
  reset: () => void
}

const MAX_HISTORY = 50

// 기본 날짜 범위: "최근 1년" (현재 연도 사업보고서만)
const defaultDateRange: DateRange = {
  startDate: new Date(CURRENT_YEAR, 0, 1),
  endDate: new Date(),
  reportYears: [CURRENT_YEAR],  // 2025년 사업보고서만
}

const initialState = {
  selectedNodeId: null,
  hoveredNodeId: null,
  sidePanelOpen: true,
  visibleNodeTypes: new Set(['company', 'officer', 'subscriber', 'cb', 'shareholder', 'affiliate'] as NodeType[]),
  dateRange: defaultDateRange,
  navigationHistory: [] as NavigationEntry[],
  navigationIndex: -1,
  currentUserId: null as string | null,
}

export const useGraphStore = create<GraphUIState>()(
  persist(
    (set, get) => ({
      ...initialState,

      selectNode: (nodeId) => set({ selectedNodeId: nodeId }),

      hoverNode: (nodeId) => set({ hoveredNodeId: nodeId }),

      setSidePanelOpen: (open) => set({ sidePanelOpen: open }),

      toggleNodeType: (type) => set((state) => {
        const newTypes = new Set(state.visibleNodeTypes)
        if (newTypes.has(type)) {
          // 최소 1개는 유지
          if (newTypes.size > 1) {
            newTypes.delete(type)
          }
        } else {
          newTypes.add(type)
        }
        return { visibleNodeTypes: newTypes }
      }),

      setDateRange: (range) => set({ dateRange: range }),

      pushNavigation: (companyId, companyName) => set((state) => {
        // 이미 같은 회사면 추가하지 않음
        const current = state.navigationHistory[state.navigationIndex]
        if (current?.companyId === companyId) {
          return state
        }

        const newEntry: NavigationEntry = {
          companyId,
          companyName,
          timestamp: Date.now(),
        }

        // 현재 위치 이후의 히스토리는 제거 (새 경로)
        const newHistory = [
          ...state.navigationHistory.slice(0, state.navigationIndex + 1),
          newEntry,
        ].slice(-MAX_HISTORY)

        return {
          navigationHistory: newHistory,
          navigationIndex: newHistory.length - 1,
        }
      }),

      goBack: () => {
        const state = get()
        if (state.navigationIndex <= 0) return null

        const newIndex = state.navigationIndex - 1
        const entry = state.navigationHistory[newIndex]

        set({ navigationIndex: newIndex })
        return entry
      },

      goForward: () => {
        const state = get()
        if (state.navigationIndex >= state.navigationHistory.length - 1) return null

        const newIndex = state.navigationIndex + 1
        const entry = state.navigationHistory[newIndex]

        set({ navigationIndex: newIndex })
        return entry
      },

      navigateToIndex: (index) => {
        const state = get()
        if (index < 0 || index >= state.navigationHistory.length) return null

        const entry = state.navigationHistory[index]
        set({ navigationIndex: index })
        return entry
      },

      clearNavigation: () => set({
        navigationHistory: [],
        navigationIndex: -1,
      }),

      // 사용자 변경 시 호출 - 다른 사용자면 탐색 경로 초기화
      setCurrentUserId: (userId) => set((state) => {
        // 사용자가 바뀌면 탐색 경로 초기화
        if (state.currentUserId !== userId) {
          return {
            currentUserId: userId,
            navigationHistory: [],
            navigationIndex: -1,
          }
        }
        return { currentUserId: userId }
      }),

      reset: () => set(initialState),
    }),
    {
      name: 'graph-ui-store',
      partialize: (state) => ({
        // localStorage에 저장할 상태만 선택
        sidePanelOpen: state.sidePanelOpen,
        dateRange: state.dateRange,
        visibleNodeTypes: Array.from(state.visibleNodeTypes), // Set은 직접 저장 불가
        navigationHistory: state.navigationHistory,
        navigationIndex: state.navigationIndex,
        currentUserId: state.currentUserId, // 사용자 ID도 저장
      }),
      // Set 복원 및 Date 복원을 위한 커스텀 merge
      merge: (persistedState: unknown, currentState: GraphUIState) => {
        const persisted = persistedState as Partial<GraphUIState & {
          visibleNodeTypes: NodeType[],
          dateRange: { startDate: string | null, endDate: string | null, reportYears?: number[] },
          currentUserId: string | null
        }>

        // dateRange의 Date 문자열 → Date 객체 복원
        let restoredDateRange = currentState.dateRange
        if (persisted.dateRange) {
          restoredDateRange = {
            startDate: persisted.dateRange.startDate
              ? new Date(persisted.dateRange.startDate)
              : null,
            endDate: persisted.dateRange.endDate
              ? new Date(persisted.dateRange.endDate)
              : null,
            reportYears: persisted.dateRange.reportYears,
          }
        }

        return {
          ...currentState,
          ...persisted,
          visibleNodeTypes: persisted.visibleNodeTypes
            ? new Set(persisted.visibleNodeTypes)
            : currentState.visibleNodeTypes,
          dateRange: restoredDateRange,
        }
      },
    }
  )
)

// 유틸리티 셀렉터
export const selectCanGoBack = (state: GraphUIState) => state.navigationIndex > 0
export const selectCanGoForward = (state: GraphUIState) =>
  state.navigationIndex < state.navigationHistory.length - 1
export const selectCurrentNavEntry = (state: GraphUIState) =>
  state.navigationHistory[state.navigationIndex] || null

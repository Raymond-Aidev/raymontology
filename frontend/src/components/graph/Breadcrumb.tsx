import { memo } from 'react'
import type { NavigationEntry } from '../../store/graphStore'

interface BreadcrumbProps {
  history: NavigationEntry[]
  currentIndex: number
  onNavigate: (companyId: string, companyName: string) => void
  maxVisible?: number
}

export const Breadcrumb = memo(function Breadcrumb({
  history,
  currentIndex,
  onNavigate,
  maxVisible = 5,
}: BreadcrumbProps) {
  if (history.length === 0) {
    return null
  }

  // 현재 위치 기준으로 표시할 항목 결정
  let startIndex = Math.max(0, currentIndex - Math.floor(maxVisible / 2))
  let endIndex = Math.min(history.length, startIndex + maxVisible)

  // 끝에서 시작 위치 재조정
  if (endIndex - startIndex < maxVisible) {
    startIndex = Math.max(0, endIndex - maxVisible)
  }

  const visibleHistory = history.slice(startIndex, endIndex)
  const hasEllipsisBefore = startIndex > 0
  const hasEllipsisAfter = endIndex < history.length

  return (
    <nav className="flex items-center gap-1 text-sm" aria-label="탐색 경로">
      {/* 처음 생략 표시 */}
      {hasEllipsisBefore && (
        <>
          <button
            onClick={() => onNavigate(history[0].companyId, history[0].companyName)}
            className="text-gray-400 hover:text-blue-600 transition-colors px-1"
            title={history[0].companyName}
          >
            ...
          </button>
          <ChevronIcon />
        </>
      )}

      {/* 히스토리 항목들 */}
      {visibleHistory.map((entry, idx) => {
        const actualIndex = startIndex + idx
        const isCurrent = actualIndex === currentIndex
        const isLast = idx === visibleHistory.length - 1

        return (
          <span key={`${entry.companyId}-${entry.timestamp}`} className="flex items-center">
            <button
              onClick={() => {
                if (!isCurrent) {
                  onNavigate(entry.companyId, entry.companyName)
                }
              }}
              disabled={isCurrent}
              className={`
                px-2 py-1 rounded transition-all max-w-[120px] truncate
                ${isCurrent
                  ? 'bg-blue-100 text-blue-700 font-medium cursor-default'
                  : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50 cursor-pointer'
                }
              `}
              title={entry.companyName}
            >
              {entry.companyName}
            </button>
            {!isLast && !hasEllipsisAfter && <ChevronIcon />}
            {!isLast && hasEllipsisAfter && idx < visibleHistory.length - 1 && <ChevronIcon />}
          </span>
        )
      })}

      {/* 끝 생략 표시 */}
      {hasEllipsisAfter && (
        <>
          <ChevronIcon />
          <button
            onClick={() => {
              const lastEntry = history[history.length - 1]
              onNavigate(lastEntry.companyId, lastEntry.companyName)
            }}
            className="text-gray-400 hover:text-blue-600 transition-colors px-1"
            title={history[history.length - 1].companyName}
          >
            ...
          </button>
        </>
      )}
    </nav>
  )
})

const ChevronIcon = memo(function ChevronIcon() {
  return (
    <svg
      className="w-4 h-4 text-gray-300 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 5l7 7-7 7"
      />
    </svg>
  )
})

export default Breadcrumb

import { memo } from 'react'

interface NavigationButtonsProps {
  canGoBack: boolean
  canGoForward: boolean
  onGoBack: () => void
  onGoForward: () => void
  onClearHistory?: () => void
}

export const NavigationButtons = memo(function NavigationButtons({
  canGoBack,
  canGoForward,
  onGoBack,
  onGoForward,
  onClearHistory,
}: NavigationButtonsProps) {
  return (
    <div className="flex items-center gap-1">
      {/* 뒤로 가기 */}
      <button
        onClick={onGoBack}
        disabled={!canGoBack}
        className={`
          p-2 rounded-lg transition-all
          ${canGoBack
            ? 'hover:bg-gray-100 text-gray-700 cursor-pointer'
            : 'text-gray-300 cursor-not-allowed'
          }
        `}
        title="이전 회사 (Alt+←)"
        aria-label="뒤로 가기"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
      </button>

      {/* 앞으로 가기 */}
      <button
        onClick={onGoForward}
        disabled={!canGoForward}
        className={`
          p-2 rounded-lg transition-all
          ${canGoForward
            ? 'hover:bg-gray-100 text-gray-700 cursor-pointer'
            : 'text-gray-300 cursor-not-allowed'
          }
        `}
        title="다음 회사 (Alt+→)"
        aria-label="앞으로 가기"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5l7 7-7 7"
          />
        </svg>
      </button>

      {/* 히스토리 초기화 (optional) */}
      {onClearHistory && (
        <button
          onClick={onClearHistory}
          className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 transition-all ml-1"
          title="탐색 기록 초기화"
          aria-label="기록 초기화"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
        </button>
      )}
    </div>
  )
})

export default NavigationButtons

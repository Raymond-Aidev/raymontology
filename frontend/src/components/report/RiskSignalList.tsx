import type { RiskSignal } from '../../types/report'
import { severityConfig } from '../../types/report'

interface RiskSignalListProps {
  signals: RiskSignal[]
}

// 심각도 순서 정의 (높은 순)
const severityOrder: Record<string, number> = {
  HIGH: 0,
  MEDIUM: 1,
  LOW: 2,
}

export default function RiskSignalList({ signals }: RiskSignalListProps) {
  if (signals.length === 0) {
    return (
      <div className="text-center py-8 text-text-muted">
        <svg className="w-12 h-12 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p>탐지된 리스크 신호가 없습니다</p>
      </div>
    )
  }

  // 심각도 높은 순으로 정렬
  const sortedSignals = [...signals].sort((a, b) => {
    return (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99)
  })

  return (
    <div className="space-y-3">
      {sortedSignals.map((signal) => {
        const config = severityConfig[signal.severity]
        return (
          <div
            key={signal.id}
            className={`p-4 rounded-lg border ${config.bg} ${config.border}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-text-primary">
                    {signal.pattern_name}
                  </span>
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${config.bg} ${config.text} border ${config.border}`}>
                    {config.label}
                  </span>
                </div>
                <p className={`text-sm ${config.text}`}>
                  {signal.description}
                </p>
              </div>
              {/* 심각도 아이콘 */}
              <div className="flex-shrink-0">
                {signal.severity === 'HIGH' && (
                  <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                )}
                {signal.severity === 'MEDIUM' && (
                  <svg className="w-6 h-6 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
                {signal.severity === 'LOW' && (
                  <svg className="w-6 h-6 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

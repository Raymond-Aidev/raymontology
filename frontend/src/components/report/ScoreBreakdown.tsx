import type { RiskScore } from '../../types/report'

interface ScoreBreakdownProps {
  scores: RiskScore
}

const categories = [
  { key: 'cbRisk' as const, label: 'CB 리스크', color: '#8B5CF6', icon: '📊' },
  { key: 'officerRisk' as const, label: '임원 리스크', color: '#10B981', icon: '👤' },
  { key: 'financialRisk' as const, label: '재무 리스크', color: '#F59E0B', icon: '💰' },
  { key: 'networkRisk' as const, label: '네트워크 리스크', color: '#3B82F6', icon: '🔗' },
]

export default function ScoreBreakdown({ scores }: ScoreBreakdownProps) {

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-text-primary mb-4">관계형 리스크 구성 요소</h3>
      {categories.map(({ key, label, color, icon }) => {
        const value = scores[key]
        const percentage = (value / 100) * 100

        return (
          <div key={key} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <span>{icon}</span>
                <span className="text-text-secondary">{label}</span>
              </span>
              <span className="font-semibold" style={{ color }}>
                {value}점
              </span>
            </div>
            <div className="h-3 bg-theme-surface rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500 ease-out"
                style={{
                  width: `${percentage}%`,
                  backgroundColor: color,
                }}
              />
            </div>
          </div>
        )
      })}

      {/* 범례 */}
      <div className="mt-6 pt-4 border-t border-theme-border">
        <div className="flex items-center justify-between text-xs text-text-muted">
          <span>0 (안전)</span>
          <span>50 (주의)</span>
          <span>100 (위험)</span>
        </div>
        <div className="h-2 mt-1 rounded-full bg-gradient-to-r from-green-400 via-yellow-400 to-red-500" />
      </div>
    </div>
  )
}

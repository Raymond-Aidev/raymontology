/**
 * WP (Worsening Probability) 인디케이터 - 관계형리스크 악화 확률
 *
 * ML 모델이 예측한 향후 12개월 내 관계형리스크 악화 확률(%)을 표시.
 * GradeCard / RaymondsIndexMiniCard 와 동일한 카드 스타일 사용.
 */

interface WPIndicatorProps {
  probability: number   // 0.0 ~ 1.0
  riskLevel: string     // LOW, MEDIUM, HIGH, CRITICAL
}

const wpConfig: Record<string, { color: string; label: string }> = {
  LOW:      { color: '#10B981', label: '낮음' },
  MEDIUM:   { color: '#FBBF24', label: '보통' },
  HIGH:     { color: '#F97316', label: '높음' },
  CRITICAL: { color: '#EF4444', label: '심각' },
}

export default function WPIndicator({ probability, riskLevel }: WPIndicatorProps) {
  const config = wpConfig[riskLevel] || wpConfig.MEDIUM
  const pct = (probability * 100).toFixed(1)

  return (
    <div className="flex flex-col items-center p-6 bg-theme-surface rounded-xl border border-theme-border">
      <span
        className="text-sm text-text-secondary mb-2 cursor-help border-b border-dotted border-text-muted"
        title="Worsening Probability — ML 모델 기반 향후 12개월 내 관계형리스크 악화 확률"
      >
        WP
      </span>
      <span
        className="text-4xl font-bold"
        style={{ color: config.color }}
      >
        {pct}
        <span className="text-xl">%</span>
      </span>
      <span
        className="mt-2 px-3 py-1 rounded-full text-sm font-medium"
        style={{ backgroundColor: `${config.color}20`, color: config.color }}
      >
        {config.label}
      </span>
    </div>
  )
}

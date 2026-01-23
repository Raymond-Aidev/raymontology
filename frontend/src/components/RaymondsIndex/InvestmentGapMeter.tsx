/**
 * 투자괴리율 게이지 컴포넌트
 *
 * 현금 증가율과 CAPEX 증가율의 차이(투자괴리율)를 시각화
 * 다크 테마 적용 버전
 */
import React from 'react'

interface InvestmentGapMeterProps {
  gap: number         // 투자괴리율 (%)
  cashGrowth: number  // 현금 CAGR (%)
  capexGrowth: number // CAPEX 증가율 (%)
}

export const InvestmentGapMeter: React.FC<InvestmentGapMeterProps> = ({
  gap,
  cashGrowth,
  capexGrowth,
}) => {
  // 게이지 범위: -50 ~ +50
  const normalizedGap = Math.max(-50, Math.min(50, gap))
  const percentage = ((normalizedGap + 50) / 100) * 100

  // 상태 결정
  const getStatus = () => {
    if (gap >= -5 && gap <= 5) return { status: 'optimal', label: '균형', color: 'green' }
    if (gap > 5 && gap <= 15) return { status: 'caution', label: '현금축적', color: 'yellow' }
    if (gap > 15) return { status: 'warning', label: '과다현금', color: 'red' }
    if (gap < -5 && gap >= -15) return { status: 'caution', label: '적극투자', color: 'blue' }
    return { status: 'warning', label: '과잉투자', color: 'purple' }
  }

  const status = getStatus()

  const getStatusBadgeColor = () => {
    switch (status.color) {
      case 'green': return 'bg-green-500/20 text-green-400 border border-green-500/30'
      case 'yellow': return 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
      case 'red': return 'bg-red-500/20 text-red-400 border border-red-500/30'
      case 'blue': return 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
      case 'purple': return 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
      default: return 'bg-theme-surface text-text-secondary border border-theme-border'
    }
  }

  const getIndicatorColor = () => {
    switch (status.color) {
      case 'green': return 'bg-green-500'
      case 'yellow': return 'bg-yellow-500'
      case 'red': return 'bg-red-500'
      case 'blue': return 'bg-blue-500'
      case 'purple': return 'bg-purple-500'
      default: return 'bg-gray-500'
    }
  }

  const getValueColor = () => {
    switch (status.color) {
      case 'green': return 'text-green-400'
      case 'yellow': return 'text-yellow-400'
      case 'red': return 'text-red-400'
      case 'blue': return 'text-blue-400'
      case 'purple': return 'text-purple-400'
      default: return 'text-text-secondary'
    }
  }

  return (
    <div className="bg-theme-card rounded-xl shadow-card border border-theme-border p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-primary">투자괴리율</h3>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusBadgeColor()}`}>
          {status.label}
        </span>
      </div>

      {/* 게이지 */}
      <div className="relative mb-6">
        {/* 배경 그라데이션 바 */}
        <div className="h-4 rounded-full bg-gradient-to-r from-purple-900/50 via-green-900/50 to-red-900/50 relative overflow-hidden">
          {/* 중앙 균형 구간 표시 */}
          <div
            className="absolute h-full bg-green-500/30"
            style={{ left: '45%', width: '10%' }}
          />
        </div>

        {/* 현재 위치 인디케이터 */}
        <div
          className={`absolute top-0 w-4 h-4 rounded-full ${getIndicatorColor()} border-2 border-theme-card shadow-md transform -translate-x-1/2`}
          style={{ left: `${percentage}%` }}
        />

        {/* 눈금 레이블 */}
        <div className="flex justify-between mt-2 text-xs text-text-muted">
          <span>-50%</span>
          <span>-25%</span>
          <span className="text-green-400 font-medium">0%</span>
          <span>+25%</span>
          <span>+50%</span>
        </div>
      </div>

      {/* 수치 */}
      <div className="text-center mb-6">
        <div className={`text-3xl font-bold ${getValueColor()}`}>
          {gap > 0 ? '+' : ''}{gap.toFixed(1)}%
        </div>
        <p className="text-sm text-text-muted mt-1">
          = 현금증가율 - CAPEX증가율
        </p>
      </div>

      {/* 세부 지표 */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
          <div className="text-sm text-blue-400 mb-1">현금 CAGR</div>
          <div className="text-xl font-bold text-blue-300">
            {cashGrowth > 0 ? '+' : ''}{cashGrowth.toFixed(1)}%
          </div>
          <div className="text-xs text-blue-400/70">3년간 연평균</div>
        </div>
        <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-3">
          <div className="text-sm text-orange-400 mb-1">CAPEX 증가율</div>
          <div className="text-xl font-bold text-orange-300">
            {capexGrowth > 0 ? '+' : ''}{capexGrowth.toFixed(1)}%
          </div>
          <div className="text-xs text-orange-400/70">3년간 연평균</div>
        </div>
      </div>

      {/* 해석 */}
      <div className="mt-4 text-sm text-text-secondary bg-theme-surface rounded-lg p-3">
        {gap >= -5 && gap <= 5 && (
          <span>✅ 현금 증가와 투자가 균형을 이루고 있습니다.</span>
        )}
        {gap > 5 && gap <= 15 && (
          <span>📊 현금이 투자 대비 많이 증가하고 있습니다. 투자 기회를 모색 중일 수 있습니다.</span>
        )}
        {gap > 15 && (
          <span>⚠️ 현금이 과도하게 축적되고 있습니다. 자본 배분 효율성 점검이 필요합니다.</span>
        )}
        {gap < -5 && gap >= -15 && (
          <span>📈 적극적인 투자를 진행 중입니다. 성장 투자일 가능성이 높습니다.</span>
        )}
        {gap < -15 && (
          <span>🔴 투자가 현금 증가를 크게 초과합니다. 재무 건전성 점검이 필요합니다.</span>
        )}
      </div>
    </div>
  )
}

export default InvestmentGapMeter

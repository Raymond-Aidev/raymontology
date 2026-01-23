/**
 * RaymondsIndex 점수 카드 컴포넌트
 *
 * 종합 점수, 등급, 투자괴리율을 표시하는 핵심 위젯
 * 다크 테마 적용 버전
 */
import React from 'react'
import type { RaymondsIndexGrade } from '../../types/raymondsIndex'
import { getGradeBgColor, getInvestmentGapInterpretation } from '../../types/raymondsIndex'

interface RaymondsIndexCardProps {
  score: number
  grade: RaymondsIndexGrade
  investmentGap: number
  redFlags: string[]
  yellowFlags: string[]
  fiscalYear?: number
  compact?: boolean
}

export const RaymondsIndexCard: React.FC<RaymondsIndexCardProps> = ({
  score,
  grade,
  investmentGap,
  redFlags,
  yellowFlags,
  fiscalYear,
  compact = false,
}) => {
  const gapInterpretation = getInvestmentGapInterpretation(investmentGap)

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400'
    if (score >= 60) return 'text-lime-400'
    if (score >= 40) return 'text-yellow-400'
    if (score >= 20) return 'text-orange-400'
    return 'text-red-400'
  }

  const getGapStatusColor = (status: 'good' | 'warning' | 'danger') => {
    switch (status) {
      case 'good':
        return 'text-green-400'
      case 'warning':
        return 'text-yellow-400'
      case 'danger':
        return 'text-red-400'
    }
  }

  if (compact) {
    return (
      <div className="bg-theme-card rounded-lg border border-theme-border p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-center">
              <div className={`text-2xl font-bold ${getScoreColor(score)}`}>
                {score.toFixed(0)}
              </div>
              <div className="text-xs text-text-muted">점</div>
            </div>
            <span className={`px-2 py-1 rounded-full text-sm font-medium ${getGradeBgColor(grade)}`}>
              {grade}
            </span>
          </div>
          <div className="text-right">
            <div className={`text-sm font-medium ${getGapStatusColor(gapInterpretation.status)}`}>
              {investmentGap > 0 ? '+' : ''}{investmentGap.toFixed(1)}%
            </div>
            <div className="text-xs text-text-muted">투자괴리율</div>
          </div>
        </div>
        {(redFlags.length > 0 || yellowFlags.length > 0) && (
          <div className="mt-2 flex gap-2">
            {redFlags.length > 0 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-400">
                🚨 {redFlags.length}
              </span>
            )}
            {yellowFlags.length > 0 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-yellow-500/20 text-yellow-400">
                ⚠️ {yellowFlags.length}
              </span>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="bg-theme-card rounded-xl shadow-card border border-theme-border p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-primary">RaymondsIndex</h3>
        {fiscalYear && (
          <span className="text-sm text-text-muted">{fiscalYear}년 기준</span>
        )}
      </div>

      {/* 메인 점수 */}
      <div className="flex items-center gap-6 mb-6">
        <div className="text-center">
          <div className={`text-5xl font-bold ${getScoreColor(score)}`}>
            {score.toFixed(0)}
          </div>
          <div className="text-sm text-text-muted mt-1">종합점수</div>
        </div>
        <div>
          <span className={`inline-block px-4 py-2 rounded-lg text-xl font-bold ${getGradeBgColor(grade)}`}>
            {grade}
          </span>
        </div>
      </div>

      {/* 투자괴리율 */}
      <div className="bg-theme-surface rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-text-secondary">투자괴리율</span>
          <span className={`text-lg font-bold ${getGapStatusColor(gapInterpretation.status)}`}>
            {investmentGap > 0 ? '+' : ''}{investmentGap.toFixed(1)}%
          </span>
        </div>
        <p className={`text-sm mt-1 ${getGapStatusColor(gapInterpretation.status)}`}>
          {gapInterpretation.message}
        </p>
      </div>

      {/* 위험 신호 */}
      {(redFlags.length > 0 || yellowFlags.length > 0) && (
        <div className="space-y-2">
          {redFlags.map((flag, idx) => (
            <div key={`red-${idx}`} className="flex items-start gap-2 p-2 bg-red-500/10 border border-red-500/30 rounded-lg">
              <span className="text-red-400">🚨</span>
              <span className="text-sm text-red-400">{flag}</span>
            </div>
          ))}
          {yellowFlags.map((flag, idx) => (
            <div key={`yellow-${idx}`} className="flex items-start gap-2 p-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
              <span className="text-yellow-400">⚠️</span>
              <span className="text-sm text-yellow-400">{flag}</span>
            </div>
          ))}
        </div>
      )}

      {/* 점수 없는 경우 */}
      {redFlags.length === 0 && yellowFlags.length === 0 && (
        <div className="flex items-center gap-2 p-2 bg-green-500/10 border border-green-500/30 rounded-lg">
          <span className="text-green-400">✅</span>
          <span className="text-sm text-green-400">특이사항 없음</span>
        </div>
      )}
    </div>
  )
}

export default RaymondsIndexCard

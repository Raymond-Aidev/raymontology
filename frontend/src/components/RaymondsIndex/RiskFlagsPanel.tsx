/**
 * 위험 신호 패널 컴포넌트
 *
 * Red Flags와 Yellow Flags를 상세히 표시
 * 다크 테마 적용 버전
 */
import React from 'react'

interface RiskFlagsPanelProps {
  redFlags: string[]
  yellowFlags: string[]
  verdict?: string | null
  keyRisk?: string | null
  recommendation?: string | null
}

export const RiskFlagsPanel: React.FC<RiskFlagsPanelProps> = ({
  redFlags,
  yellowFlags,
  verdict,
  keyRisk,
  recommendation,
}) => {
  const hasFlags = redFlags.length > 0 || yellowFlags.length > 0

  return (
    <div className="bg-dark-card rounded-xl shadow-card border border-dark-border p-6">
      <h3 className="text-lg font-semibold text-text-primary mb-4">리스크 분석</h3>

      {/* 한 줄 요약 */}
      {verdict && (
        <div className="mb-4 p-3 bg-dark-surface rounded-lg">
          <p className="text-sm text-text-secondary font-medium">{verdict}</p>
        </div>
      )}

      {/* 위험 신호 */}
      {hasFlags ? (
        <div className="space-y-3 mb-4">
          {redFlags.map((flag, idx) => (
            <div
              key={`red-${idx}`}
              className="flex items-start gap-3 p-3 bg-red-500/10 border border-red-500/30 rounded-lg"
            >
              <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-red-500/20 rounded-full">
                <span className="text-red-400 text-lg">🚨</span>
              </div>
              <div>
                <span className="inline-block px-2 py-0.5 text-xs font-medium bg-red-500/20 text-red-400 rounded mb-1">
                  Red Flag
                </span>
                <p className="text-sm text-red-400">{flag}</p>
              </div>
            </div>
          ))}
          {yellowFlags.map((flag, idx) => (
            <div
              key={`yellow-${idx}`}
              className="flex items-start gap-3 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg"
            >
              <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-yellow-500/20 rounded-full">
                <span className="text-yellow-400 text-lg">⚠️</span>
              </div>
              <div>
                <span className="inline-block px-2 py-0.5 text-xs font-medium bg-yellow-500/20 text-yellow-400 rounded mb-1">
                  Yellow Flag
                </span>
                <p className="text-sm text-yellow-400">{flag}</p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex items-center gap-3 p-3 bg-green-500/10 border border-green-500/30 rounded-lg mb-4">
          <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-green-500/20 rounded-full">
            <span className="text-green-400 text-lg">✅</span>
          </div>
          <div>
            <span className="inline-block px-2 py-0.5 text-xs font-medium bg-green-500/20 text-green-400 rounded mb-1">
              양호
            </span>
            <p className="text-sm text-green-400">주요 위험 신호가 감지되지 않았습니다.</p>
          </div>
        </div>
      )}

      {/* 핵심 리스크 */}
      {keyRisk && (
        <div className="mb-3">
          <h4 className="text-sm font-medium text-text-secondary mb-1">핵심 리스크</h4>
          <p className="text-sm text-text-secondary bg-dark-surface p-2 rounded">{keyRisk}</p>
        </div>
      )}

      {/* 권고사항 */}
      {recommendation && (
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-1">투자자 권고</h4>
          <p className="text-sm text-blue-400 bg-blue-500/10 border border-blue-500/30 p-2 rounded">{recommendation}</p>
        </div>
      )}
    </div>
  )
}

export default RiskFlagsPanel

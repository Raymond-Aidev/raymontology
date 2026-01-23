/**
 * Sub-Index 레이더 차트 컴포넌트
 *
 * 4개의 Sub-Index (CEI, RII, CGI, MAI)를 레이더 차트로 시각화
 * 다크 테마 적용 버전
 */
import React, { useMemo } from 'react'

interface SubIndexRadarProps {
  cei: number  // Capital Efficiency Index (20%)
  rii: number  // Reinvestment Intensity Index (35%)
  cgi: number  // Cash Governance Index (25%)
  mai: number  // Momentum Alignment Index (20%)
  size?: number
}

const SUB_INDEX_LABELS = [
  { key: 'cei', label: '자본효율성', shortLabel: 'CEI', weight: '20%' },
  { key: 'rii', label: '재투자강도', shortLabel: 'RII', weight: '35%' },
  { key: 'cgi', label: '현금거버넌스', shortLabel: 'CGI', weight: '25%' },
  { key: 'mai', label: '모멘텀정렬', shortLabel: 'MAI', weight: '20%' },
]

export const SubIndexRadar: React.FC<SubIndexRadarProps> = ({
  cei,
  rii,
  cgi,
  mai,
  size = 280,
}) => {
  const scores = [cei, rii, cgi, mai]
  const center = size / 2
  const maxRadius = size / 2 - 40

  // 다각형 좌표 계산
  const calculatePoint = (index: number, value: number) => {
    const angle = (Math.PI * 2 * index) / 4 - Math.PI / 2
    const radius = (value / 100) * maxRadius
    return {
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
    }
  }

  // 데이터 다각형 경로
  const dataPath = useMemo(() => {
    const points = scores.map((score, i) => calculatePoint(i, score))
    return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z'
  }, [scores, center, maxRadius])

  // 배경 그리드 (20%, 40%, 60%, 80%, 100%)
  const gridLevels = [20, 40, 60, 80, 100]

  return (
    <div className="bg-theme-card rounded-xl shadow-card border border-theme-border p-6">
      <h3 className="text-lg font-semibold text-text-primary mb-4">Sub-Index 분석</h3>

      <div className="flex flex-col items-center">
        <svg width={size} height={size} className="overflow-visible">
          {/* 배경 그리드 */}
          {gridLevels.map((level) => {
            const path = [0, 1, 2, 3]
              .map((i) => {
                const p = calculatePoint(i, level)
                return `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`
              })
              .join(' ') + ' Z'
            return (
              <path
                key={level}
                d={path}
                fill="none"
                stroke="#262626"
                strokeWidth="1"
              />
            )
          })}

          {/* 축 라인 */}
          {[0, 1, 2, 3].map((i) => {
            const p = calculatePoint(i, 100)
            return (
              <line
                key={i}
                x1={center}
                y1={center}
                x2={p.x}
                y2={p.y}
                stroke="#262626"
                strokeWidth="1"
              />
            )
          })}

          {/* 데이터 영역 */}
          <path
            d={dataPath}
            fill="rgba(59, 130, 246, 0.2)"
            stroke="#3b82f6"
            strokeWidth="2"
          />

          {/* 데이터 포인트 */}
          {scores.map((score, i) => {
            const p = calculatePoint(i, score)
            return (
              <circle
                key={i}
                cx={p.x}
                cy={p.y}
                r={4}
                fill="#3b82f6"
              />
            )
          })}

          {/* 레이블 */}
          {SUB_INDEX_LABELS.map((item, i) => {
            const p = calculatePoint(i, 115)
            return (
              <g key={item.key}>
                <text
                  x={p.x}
                  y={p.y - 8}
                  textAnchor="middle"
                  fill="#a1a1aa"
                  className="text-xs font-medium"
                >
                  {item.shortLabel}
                </text>
                <text
                  x={p.x}
                  y={p.y + 6}
                  textAnchor="middle"
                  fill="#52525b"
                  className="text-xs"
                >
                  {item.weight}
                </text>
              </g>
            )
          })}
        </svg>

        {/* 상세 점수 */}
        <div className="mt-4 grid grid-cols-2 gap-3 w-full">
          {SUB_INDEX_LABELS.map((item, i) => (
            <div key={item.key} className="flex items-center justify-between bg-theme-surface rounded-lg px-3 py-2">
              <div>
                <span className="text-sm font-medium text-text-secondary">{item.shortLabel}</span>
                <span className="text-xs text-text-muted ml-1">{item.label}</span>
              </div>
              <span className={`text-sm font-bold ${getScoreColor(scores[i])}`}>
                {scores[i].toFixed(0)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-green-400'
  if (score >= 60) return 'text-lime-400'
  if (score >= 40) return 'text-yellow-400'
  if (score >= 20) return 'text-orange-400'
  return 'text-red-400'
}

export default SubIndexRadar

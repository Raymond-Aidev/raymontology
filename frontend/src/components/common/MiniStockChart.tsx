/**
 * MiniStockChart - 주의 필요 기업 카드용 미니 주가 차트
 *
 * StockPriceCard의 축소 버전. 라벨/눈금 없이 라인+그라데이션만 표시.
 * 최근 1년 (12개월) 월별 종가 데이터를 시각화.
 */
import { useState, useEffect, useMemo } from 'react'
import { apiClient } from '../../api/client'

interface StockPriceData {
  month: string
  close: number
}

interface MiniStockChartProps {
  companyId: string
  width?: number
  height?: number
  showReturnRate?: boolean
}

export function MiniStockChart({
  companyId,
  width = 140,
  height = 40,
  showReturnRate = true,
}: MiniStockChartProps) {
  const [data, setData] = useState<StockPriceData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    const fetchStockPrices = async () => {
      setLoading(true)
      setError(false)

      try {
        const response = await apiClient.get(`/api/stock-prices/company/${companyId}/chart`, {
          params: { period: '1y' }
        })

        if (response.data?.data && response.data.data.length > 0) {
          setData(response.data.data)
        } else {
          setError(true)
        }
      } catch {
        setError(true)
      } finally {
        setLoading(false)
      }
    }

    if (companyId) {
      fetchStockPrices()
    }
  }, [companyId])

  // 차트 데이터 계산
  const chartData = useMemo(() => {
    if (data.length < 2) return null

    const prices = data.map(d => d.close)
    const minPrice = Math.min(...prices)
    const maxPrice = Math.max(...prices)
    const range = maxPrice - minPrice || 1

    const recentData = data.slice(-12)
    const latestPrice = recentData[recentData.length - 1]?.close || 0
    const firstPrice = recentData[0]?.close || 0
    const totalChange = firstPrice > 0 ? ((latestPrice - firstPrice) / firstPrice) * 100 : 0

    const paddingX = 2
    const paddingY = 4

    const points = recentData.map((d, i) => {
      const x = paddingX + (i / (recentData.length - 1)) * (width - paddingX * 2)
      const y = height - paddingY - ((d.close - minPrice) / range) * (height - paddingY * 2)
      return { x, y }
    })

    const pathD = points
      .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
      .join(' ')

    const areaD = pathD +
      ` L ${(width - paddingX).toFixed(1)} ${height - paddingY} L ${paddingX} ${height - paddingY} Z`

    return {
      pathD,
      areaD,
      totalChange,
      isPositive: totalChange >= 0,
    }
  }, [data, width, height])

  // 로딩 상태
  if (loading) {
    return (
      <div className="flex items-center gap-2">
        <div
          className="bg-theme-hover rounded animate-pulse"
          style={{ width, height }}
        />
        {showReturnRate && (
          <div className="w-10 h-4 bg-theme-hover rounded animate-pulse" />
        )}
      </div>
    )
  }

  // 에러 또는 데이터 없음
  if (error || !chartData) {
    return (
      <div className="flex items-center gap-2">
        <div
          className="flex items-center justify-center bg-theme-surface/50 rounded"
          style={{ width, height }}
        >
          <span className="text-xs text-text-muted">—</span>
        </div>
        {showReturnRate && (
          <span className="text-xs text-text-muted">—</span>
        )}
      </div>
    )
  }

  const strokeColor = chartData.isPositive ? '#ef4444' : '#3b82f6'
  const textColorClass = chartData.isPositive ? 'text-red-400' : 'text-blue-400'

  return (
    <div className="flex items-center gap-2">
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className="overflow-visible"
      >
        {/* 그라데이션 정의 */}
        <defs>
          <linearGradient id={`mini-gradient-${companyId}`} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={strokeColor} stopOpacity="0.3" />
            <stop offset="100%" stopColor={strokeColor} stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* 그라데이션 영역 */}
        <path
          d={chartData.areaD}
          fill={`url(#mini-gradient-${companyId})`}
        />

        {/* 라인 */}
        <path
          d={chartData.pathD}
          fill="none"
          stroke={strokeColor}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>

      {/* 수익률 */}
      {showReturnRate && (
        <span className={`text-xs font-medium ${textColorClass} whitespace-nowrap`}>
          {chartData.isPositive ? '+' : ''}{chartData.totalChange.toFixed(1)}%
        </span>
      )}
    </div>
  )
}

export default MiniStockChart

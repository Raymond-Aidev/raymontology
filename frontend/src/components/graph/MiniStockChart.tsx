import { useState, useEffect, useMemo } from 'react'
import { apiClient } from '../../api/client'

interface StockPriceData {
  month: string
  close: number
  change: number | null
}

interface MiniStockChartProps {
  companyId: string
  companyName?: string
}

/**
 * 미니 주가 흐름 차트 - 최근 12개월 월말 종가를 스파크라인으로 표시
 */
export default function MiniStockChart({ companyId, companyName }: MiniStockChartProps) {
  const [data, setData] = useState<StockPriceData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStockPrices = async () => {
      setLoading(true)
      setError(null)

      try {
        const response = await apiClient.get(`/api/stock-prices/company/${companyId}/chart`, {
          params: { period: '1y' }
        })

        if (response.data?.data && response.data.data.length > 0) {
          setData(response.data.data)
        } else {
          setError('데이터 없음')
        }
      } catch (err) {
        console.error('주가 데이터 조회 실패:', err)
        setError('조회 실패')
      } finally {
        setLoading(false)
      }
    }

    if (companyId) {
      fetchStockPrices()
    }
  }, [companyId])

  // 차트 계산
  const chartData = useMemo(() => {
    if (data.length === 0) return null

    const prices = data.map(d => d.close)
    const minPrice = Math.min(...prices)
    const maxPrice = Math.max(...prices)
    const range = maxPrice - minPrice || 1

    // 최근 12개월만 사용
    const recentData = data.slice(-12)
    const latestPrice = recentData[recentData.length - 1]?.close || 0
    const firstPrice = recentData[0]?.close || 0
    const totalChange = firstPrice > 0 ? ((latestPrice - firstPrice) / firstPrice) * 100 : 0

    // SVG 경로 생성 (40x24 크기)
    const width = 80
    const height = 24
    const padding = 2

    const points = recentData.map((d, i) => {
      const x = padding + (i / (recentData.length - 1)) * (width - padding * 2)
      const y = height - padding - ((d.close - minPrice) / range) * (height - padding * 2)
      return { x, y, price: d.close, month: d.month }
    })

    const pathD = points
      .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
      .join(' ')

    // 그라데이션 영역 경로
    const areaD = pathD +
      ` L ${(width - padding).toFixed(1)} ${height} L ${padding} ${height} Z`

    return {
      points,
      pathD,
      areaD,
      width,
      height,
      latestPrice,
      totalChange,
      isPositive: totalChange >= 0,
    }
  }, [data])

  // 로딩 상태
  if (loading) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-muted">주가흐름</span>
        <div className="w-20 h-6 bg-dark-hover rounded animate-pulse" />
      </div>
    )
  }

  // 에러 또는 데이터 없음
  if (error || !chartData) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-muted">주가흐름</span>
        <span className="text-xs text-text-muted/50">-</span>
      </div>
    )
  }

  const strokeColor = chartData.isPositive ? '#ef4444' : '#3b82f6'  // 상승: 빨강, 하락: 파랑 (한국식)
  const fillColor = chartData.isPositive ? 'rgba(239, 68, 68, 0.1)' : 'rgba(59, 130, 246, 0.1)'

  return (
    <div className="flex items-center gap-2" title={companyName ? `${companyName} 최근 1년 주가 흐름` : '최근 1년 주가 흐름'}>
      <span className="text-xs font-medium text-text-muted uppercase tracking-wide">주가흐름</span>

      {/* 스파크라인 차트 */}
      <div className="relative">
        <svg
          width={chartData.width}
          height={chartData.height}
          className="overflow-visible"
        >
          {/* 그라데이션 영역 */}
          <path
            d={chartData.areaD}
            fill={fillColor}
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
          {/* 마지막 점 */}
          <circle
            cx={chartData.points[chartData.points.length - 1].x}
            cy={chartData.points[chartData.points.length - 1].y}
            r={2.5}
            fill={strokeColor}
          />
        </svg>
      </div>

      {/* 변동률 */}
      <span className={`text-xs font-semibold font-mono ${chartData.isPositive ? 'text-accent-danger' : 'text-accent-primary'}`}>
        {chartData.isPositive ? '+' : ''}{chartData.totalChange.toFixed(1)}%
      </span>
    </div>
  )
}

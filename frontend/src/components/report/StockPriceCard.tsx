import { useState, useEffect, useMemo } from 'react'
import { apiClient } from '../../api/client'

interface StockPriceData {
  month: string
  close: number
  change: number | null
}

interface StockPriceCardProps {
  companyId: string
  companyName?: string
}

/**
 * 분석보고서용 주가 차트 카드 - 최근 12개월 월말 종가 표시
 */
export default function StockPriceCard({ companyId }: StockPriceCardProps) {
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

    // SVG 경로 생성 - 카드 사이즈에 맞춤
    const width = 280
    const height = 100
    const paddingX = 8
    const paddingY = 12

    const points = recentData.map((d, i) => {
      const x = paddingX + (i / (recentData.length - 1)) * (width - paddingX * 2)
      const y = height - paddingY - ((d.close - minPrice) / range) * (height - paddingY * 2)
      return { x, y, price: d.close, month: d.month }
    })

    const pathD = points
      .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
      .join(' ')

    // 그라데이션 영역 경로
    const areaD = pathD +
      ` L ${(width - paddingX).toFixed(1)} ${height - paddingY} L ${paddingX} ${height - paddingY} Z`

    return {
      points,
      pathD,
      areaD,
      width,
      height,
      latestPrice,
      firstPrice,
      totalChange,
      isPositive: totalChange >= 0,
      startMonth: recentData[0]?.month || '',
      endMonth: recentData[recentData.length - 1]?.month || '',
    }
  }, [data])

  // 로딩 상태
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-4 md:p-6">
        <div className="text-sm text-text-muted mb-2">최근 1년 주가 차트</div>
        <div className="w-full h-24 bg-theme-hover rounded animate-pulse" />
      </div>
    )
  }

  // 에러 또는 데이터 없음
  if (error || !chartData) {
    return (
      <div className="flex flex-col items-center justify-center p-4 md:p-6 text-center">
        <div className="text-sm text-text-muted mb-2">최근 1년 주가 차트</div>
        <div className="text-xs text-text-muted/50">주가 데이터가 없습니다</div>
      </div>
    )
  }

  const strokeColor = chartData.isPositive ? '#ef4444' : '#3b82f6'
  const textColor = chartData.isPositive ? 'text-red-400' : 'text-blue-400'

  // 가격 포맷
  const formatPrice = (price: number) => {
    if (price >= 10000) {
      return `${(price / 10000).toFixed(1)}만`
    }
    return price.toLocaleString()
  }

  return (
    <div className="flex flex-col p-4 md:p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-3">
        <div className="text-sm font-medium text-text-secondary">최근 1년 주가 차트</div>
        <div className={`text-lg font-bold ${textColor}`}>
          {chartData.isPositive ? '+' : ''}{chartData.totalChange.toFixed(1)}%
        </div>
      </div>

      {/* 가격 정보 */}
      <div className="flex items-center justify-between text-xs text-text-muted mb-2">
        <span>{chartData.startMonth}</span>
        <span>{chartData.endMonth}</span>
      </div>

      {/* 차트 */}
      <div className="relative">
        <svg
          width="100%"
          height={chartData.height}
          viewBox={`0 0 ${chartData.width} ${chartData.height}`}
          preserveAspectRatio="none"
          className="overflow-visible"
        >
          {/* 그라데이션 정의 */}
          <defs>
            <linearGradient id={`gradient-${companyId}`} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={strokeColor} stopOpacity="0.3" />
              <stop offset="100%" stopColor={strokeColor} stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* 그라데이션 영역 */}
          <path
            d={chartData.areaD}
            fill={`url(#gradient-${companyId})`}
          />

          {/* 기준선 (시작 가격) */}
          <line
            x1={8}
            y1={chartData.points[0].y}
            x2={chartData.width - 8}
            y2={chartData.points[0].y}
            stroke="rgba(255,255,255,0.1)"
            strokeDasharray="4 4"
          />

          {/* 라인 */}
          <path
            d={chartData.pathD}
            fill="none"
            stroke={strokeColor}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* 12개 점 모두 표시 */}
          {chartData.points.map((point, idx) => (
            <circle
              key={idx}
              cx={point.x}
              cy={point.y}
              r={3}
              fill={idx === chartData.points.length - 1 ? strokeColor : 'transparent'}
              stroke={strokeColor}
              strokeWidth={1.5}
              opacity={idx === chartData.points.length - 1 ? 1 : 0.5}
            />
          ))}
        </svg>
      </div>

      {/* 가격 범위 */}
      <div className="flex items-center justify-between text-xs text-text-muted mt-2">
        <span>{formatPrice(chartData.firstPrice)}원</span>
        <span className={`font-medium ${textColor}`}>
          {formatPrice(chartData.latestPrice)}원
        </span>
      </div>
    </div>
  )
}

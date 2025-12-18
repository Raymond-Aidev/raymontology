import type React from 'react'

interface SkeletonProps {
  className?: string
  width?: string | number
  height?: string | number
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'full'
  animate?: boolean
}

const roundedClasses = {
  none: 'rounded-none',
  sm: 'rounded-sm',
  md: 'rounded-md',
  lg: 'rounded-lg',
  full: 'rounded-full',
}

export function Skeleton({
  className = '',
  width,
  height,
  rounded = 'md',
  animate = true,
}: SkeletonProps) {
  const style: React.CSSProperties = {}
  if (width) style.width = typeof width === 'number' ? `${width}px` : width
  if (height) style.height = typeof height === 'number' ? `${height}px` : height

  return (
    <div
      className={`
        bg-gray-200 ${roundedClasses[rounded]}
        ${animate ? 'animate-pulse' : ''}
        ${className}
      `}
      style={style}
    />
  )
}

// 텍스트 라인 스켈레톤
export function SkeletonText({
  lines = 1,
  className = '',
}: {
  lines?: number
  className?: string
}) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          height={16}
          width={i === lines - 1 && lines > 1 ? '60%' : '100%'}
        />
      ))}
    </div>
  )
}

// 아바타 스켈레톤
export function SkeletonAvatar({
  size = 'md',
}: {
  size?: 'sm' | 'md' | 'lg'
}) {
  const sizeMap = { sm: 32, md: 48, lg: 64 }
  return <Skeleton width={sizeMap[size]} height={sizeMap[size]} rounded="full" />
}

// 카드 스켈레톤
export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-white rounded-xl shadow-lg p-6 ${className}`}>
      <div className="flex items-center gap-4 mb-4">
        <SkeletonAvatar />
        <div className="flex-1">
          <Skeleton height={20} width="60%" className="mb-2" />
          <Skeleton height={14} width="40%" />
        </div>
      </div>
      <SkeletonText lines={3} />
    </div>
  )
}

// 테이블 스켈레톤
export function SkeletonTable({
  rows = 5,
  cols = 4,
}: {
  rows?: number
  cols?: number
}) {
  return (
    <div className="w-full">
      {/* 헤더 */}
      <div className="flex gap-4 pb-3 border-b border-gray-200 mb-3">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} height={16} className="flex-1" />
        ))}
      </div>
      {/* 행들 */}
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, rowIdx) => (
          <div key={rowIdx} className="flex gap-4">
            {Array.from({ length: cols }).map((_, colIdx) => (
              <Skeleton key={colIdx} height={20} className="flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

// 그래프 스켈레톤
export function SkeletonGraph({ className = '' }: { className?: string }) {
  return (
    <div className={`relative bg-gray-50 rounded-xl p-8 ${className}`}>
      {/* 중앙 노드 */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
        <Skeleton width={80} height={80} rounded="full" />
      </div>
      {/* 주변 노드들 */}
      <div className="absolute top-1/4 left-1/4">
        <Skeleton width={50} height={50} rounded="full" />
      </div>
      <div className="absolute top-1/4 right-1/4">
        <Skeleton width={50} height={50} rounded="full" />
      </div>
      <div className="absolute bottom-1/4 left-1/3">
        <Skeleton width={50} height={50} rounded="full" />
      </div>
      <div className="absolute bottom-1/4 right-1/3">
        <Skeleton width={50} height={50} rounded="full" />
      </div>
    </div>
  )
}

// 보고서 대시보드 스켈레톤
export function SkeletonDashboard() {
  return (
    <div className="space-y-6">
      {/* 상단 카드들 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-lg p-6">
          <Skeleton width={100} height={16} className="mb-4" />
          <Skeleton width={120} height={120} rounded="full" className="mx-auto" />
        </div>
        <div className="bg-white rounded-xl shadow-lg p-6">
          <Skeleton width={100} height={16} className="mb-4" />
          <Skeleton height={100} className="mb-2" />
          <SkeletonText lines={2} />
        </div>
        <div className="bg-white rounded-xl shadow-lg p-6">
          <Skeleton width={100} height={16} className="mb-4" />
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-center gap-2">
                <Skeleton width={60} height={12} />
                <Skeleton height={8} className="flex-1" rounded="full" />
                <Skeleton width={40} height={12} />
              </div>
            ))}
          </div>
        </div>
      </div>
      {/* 테이블 영역 */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <Skeleton width={150} height={20} className="mb-4" />
        <SkeletonTable rows={5} cols={5} />
      </div>
    </div>
  )
}

export default Skeleton

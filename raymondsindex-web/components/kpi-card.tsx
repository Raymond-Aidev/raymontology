'use client';

import { Card, CardContent } from '@/components/ui/card';
import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

interface KPICardProps {
  title: string;
  value: string | number;
  suffix?: string;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: {
    direction: 'up' | 'down' | 'stable';
    value?: string;
  };
  percentage?: number;
  isLoading?: boolean;
  className?: string;
}

export function KPICard({
  title,
  value,
  suffix,
  subtitle,
  icon: Icon,
  trend,
  percentage,
  isLoading = false,
  className,
}: KPICardProps) {
  const TrendIcon = trend?.direction === 'up'
    ? TrendingUp
    : trend?.direction === 'down'
      ? TrendingDown
      : Minus;

  const trendColor = trend?.direction === 'up'
    ? 'text-green-400'
    : trend?.direction === 'down'
      ? 'text-red-400'
      : 'text-gray-500';

  if (isLoading) {
    return (
      <Card className={cn('relative overflow-hidden', className)}>
        <CardContent className="p-2.5">
          <div className="animate-pulse">
            <div className="h-3 w-16 bg-gray-200 rounded mb-1.5" />
            <div className="h-6 w-20 bg-gray-200 rounded mb-0.5" />
            <div className="h-2.5 w-14 bg-gray-200 rounded" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('relative overflow-hidden hover:bg-gray-50 transition-colors', className)}>
      <CardContent className="p-2.5">
        {/* 헤더: 타이틀 + 아이콘 */}
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-gray-500">
            {title}
          </span>
          {Icon && (
            <Icon className="w-3.5 h-3.5 text-gray-500" />
          )}
        </div>

        {/* 메인 값 */}
        <div className="flex items-baseline gap-0.5">
          <span className="text-lg font-semibold text-gray-900">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </span>
          {suffix && (
            <span className="text-xs text-gray-500">
              {suffix}
            </span>
          )}
        </div>

        {/* 트렌드 또는 서브타이틀 */}
        <div className="mt-0.5 flex items-center gap-1.5">
          {trend && (
            <div className={cn('flex items-center gap-0.5 text-[10px]', trendColor)}>
              <TrendIcon className="w-2.5 h-2.5" />
              {trend.value && <span>{trend.value}</span>}
            </div>
          )}
          {percentage !== undefined && (
            <span className="text-[10px] text-gray-500">
              전체의 {percentage.toFixed(1)}%
            </span>
          )}
          {subtitle && (
            <span className="text-[10px] text-gray-500">
              {subtitle}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// KPI 카드 그리드 컴포넌트
interface KPIGridProps {
  children: React.ReactNode;
  columns?: 2 | 3 | 4;
  className?: string;
}

export function KPIGrid({ children, columns = 4, className }: KPIGridProps) {
  const gridCols = {
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div className={cn('grid gap-2', gridCols[columns], className)}>
      {children}
    </div>
  );
}

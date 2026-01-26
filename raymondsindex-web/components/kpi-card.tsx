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
    ? 'text-green-500'
    : trend?.direction === 'down'
      ? 'text-red-500'
      : 'text-gray-400';

  if (isLoading) {
    return (
      <Card className={cn('relative overflow-hidden', className)}>
        <CardContent className="p-4">
          <div className="animate-pulse">
            <div className="h-4 w-20 bg-gray-200 rounded mb-2" />
            <div className="h-8 w-24 bg-gray-200 rounded mb-1" />
            <div className="h-3 w-16 bg-gray-200 rounded" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('relative overflow-hidden hover:shadow-md transition-shadow', className)}>
      <CardContent className="p-4">
        {/* 헤더: 타이틀 + 아이콘 */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-muted-foreground">
            {title}
          </span>
          {Icon && (
            <Icon className="w-4 h-4 text-muted-foreground" />
          )}
        </div>

        {/* 메인 값 */}
        <div className="flex items-baseline gap-1">
          <span className="text-2xl font-bold text-foreground">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </span>
          {suffix && (
            <span className="text-sm text-muted-foreground">
              {suffix}
            </span>
          )}
        </div>

        {/* 트렌드 또는 서브타이틀 */}
        <div className="mt-1 flex items-center gap-2">
          {trend && (
            <div className={cn('flex items-center gap-1 text-xs', trendColor)}>
              <TrendIcon className="w-3 h-3" />
              {trend.value && <span>{trend.value}</span>}
            </div>
          )}
          {percentage !== undefined && (
            <span className="text-xs text-muted-foreground">
              전체의 {percentage.toFixed(1)}%
            </span>
          )}
          {subtitle && (
            <span className="text-xs text-muted-foreground">
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
    <div className={cn('grid gap-4', gridCols[columns], className)}>
      {children}
    </div>
  );
}

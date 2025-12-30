'use client';

import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

// 데이터 플래그 설명 메시지
const DATA_FLAG_MESSAGES: Record<string, string> = {
  'no_capex': 'CAPEX 데이터가 부족하여 정확한 투자괴리율 산출이 어렵습니다. 해당 기업의 설비투자 내역을 직접 확인하시기 바랍니다.',
  'no_cash': '현금 데이터가 부족하여 정확한 투자괴리율 산출이 어렵습니다. 해당 기업의 현금흐름을 직접 확인하시기 바랍니다.',
  'insufficient_data': '2개년 미만의 데이터로 인해 정확한 투자괴리율 산출이 어렵습니다.',
};

interface MetricCardProps {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  status?: 'good' | 'warning' | 'danger' | 'neutral';
  description?: string;
  tooltip?: string;  // 위험요소 관점 설명
  trend?: 'up' | 'down' | 'stable';
  className?: string;
  dataFlag?: string;  // 데이터 품질 플래그 (no_capex, no_cash, insufficient_data)
}

const statusConfig = {
  good: {
    bg: 'bg-green-50 border-green-200',
    icon: CheckCircle2,
    iconColor: 'text-green-500',
    label: '양호',
  },
  warning: {
    bg: 'bg-yellow-50 border-yellow-200',
    icon: AlertTriangle,
    iconColor: 'text-yellow-500',
    label: '주의',
  },
  danger: {
    bg: 'bg-red-50 border-red-200',
    icon: XCircle,
    iconColor: 'text-red-500',
    label: '위험',
  },
  neutral: {
    bg: 'bg-gray-50 border-gray-200',
    icon: HelpCircle,
    iconColor: 'text-gray-400',
    label: '-',
  },
};

const trendIcons = {
  up: TrendingUp,
  down: TrendingDown,
  stable: Minus,
};

export function MetricCard({
  label,
  value,
  unit,
  status = 'neutral',
  description,
  tooltip,
  trend,
  className,
  dataFlag,
}: MetricCardProps) {
  const config = statusConfig[status];
  const StatusIcon = config.icon;
  const TrendIcon = trend ? trendIcons[trend] : null;

  const displayValue = value === null || value === undefined ? '-' : value;
  const hasDataIssue = dataFlag && dataFlag !== 'ok' && DATA_FLAG_MESSAGES[dataFlag];

  return (
    <Card className={cn('border', config.bg, className)}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-1 mb-1">
              <p className="text-sm text-gray-600">{label}</p>
              {tooltip && (
                <TooltipProvider delayDuration={0}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        className="text-gray-400 hover:text-gray-600 focus:outline-none"
                        aria-label={`${label} 설명`}
                      >
                        <HelpCircle className="w-3.5 h-3.5" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="max-w-xs">
                      <p className="text-sm">{tooltip}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold text-gray-900">
                {displayValue}
              </span>
              {unit && <span className="text-sm text-gray-500">{unit}</span>}
              {/* 데이터 품질 이슈 표시 */}
              {hasDataIssue && (
                <TooltipProvider delayDuration={0}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        className="text-amber-500 hover:text-amber-600 focus:outline-none ml-1"
                        aria-label="데이터 품질 안내"
                      >
                        <HelpCircle className="w-4 h-4" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="max-w-xs bg-amber-50 border-amber-200">
                      <p className="text-sm text-amber-800">{DATA_FLAG_MESSAGES[dataFlag!]}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
              {TrendIcon && (
                <TrendIcon className={cn(
                  'w-4 h-4 ml-1',
                  trend === 'up' && 'text-green-500',
                  trend === 'down' && 'text-red-500',
                  trend === 'stable' && 'text-gray-400'
                )} />
              )}
            </div>
            {description && (
              <p className="text-xs text-gray-500 mt-1">{description}</p>
            )}
          </div>
          <div className="flex flex-col items-center">
            <StatusIcon className={cn('w-5 h-5', config.iconColor)} />
            <span className={cn('text-xs mt-0.5', config.iconColor)}>{config.label}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

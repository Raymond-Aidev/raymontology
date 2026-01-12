'use client';

import { cn } from '@/lib/utils';

type MarketType = 'KOSPI' | 'KOSDAQ' | 'KONEX' | 'ETF' | string;
type TradingStatus = 'NORMAL' | 'SUSPENDED' | 'TRADING_HALT' | string;

interface MarketBadgeProps {
  market: MarketType;
  tradingStatus?: TradingStatus;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const MARKET_COLORS: Record<string, { bg: string; text: string }> = {
  KOSPI: { bg: '#3B82F6', text: 'white' },      // blue-500
  KOSDAQ: { bg: '#22C55E', text: 'white' },     // green-500
  KONEX: { bg: '#6B7280', text: 'white' },      // gray-500
  ETF: { bg: '#8B5CF6', text: 'white' },        // violet-500
};

const sizeClasses = {
  sm: 'px-1.5 py-0.5 text-[10px]',
  md: 'px-2 py-0.5 text-xs',
  lg: 'px-2.5 py-1 text-sm',
};

export function MarketBadge({
  market,
  tradingStatus = 'NORMAL',
  size = 'sm',
  className
}: MarketBadgeProps) {
  const colors = MARKET_COLORS[market] || { bg: '#9CA3AF', text: 'white' };
  const isSuspended = tradingStatus === 'SUSPENDED' || tradingStatus === 'TRADING_HALT';

  return (
    <span
      className={cn(
        'inline-flex items-center rounded font-medium whitespace-nowrap',
        sizeClasses[size],
        isSuspended && 'ring-2 ring-red-500',
        className
      )}
      style={{
        backgroundColor: colors.bg,
        color: colors.text,
      }}
    >
      {market}
      {isSuspended && (
        <span className="ml-1 text-red-200">!</span>
      )}
    </span>
  );
}

// 거래정지 전용 배지
export function TradingStatusBadge({
  status,
  className
}: {
  status: TradingStatus;
  className?: string;
}) {
  if (status === 'NORMAL') return null;

  const labels: Record<string, string> = {
    SUSPENDED: '거래정지',
    TRADING_HALT: '매매거래정지',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium',
        'bg-red-500 text-white',
        className
      )}
    >
      {labels[status] || status}
    </span>
  );
}

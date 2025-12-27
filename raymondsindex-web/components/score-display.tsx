'use client';

import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface ScoreDisplayProps {
  score: number;
  previousScore?: number;
  showChange?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses = {
  sm: 'text-lg',
  md: 'text-2xl',
  lg: 'text-4xl',
};

export function ScoreDisplay({
  score,
  previousScore,
  showChange = false,
  size = 'md',
  className,
}: ScoreDisplayProps) {
  const change = previousScore ? score - previousScore : 0;
  const hasChange = showChange && previousScore !== undefined && change !== 0;

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span className={cn('font-bold', sizeClasses[size])}>
        {score.toFixed(1)}
      </span>
      <span className="text-gray-400 text-sm">점</span>

      {hasChange && (
        <span
          className={cn(
            'flex items-center text-sm font-medium',
            change > 0 ? 'text-green-600' : 'text-red-600'
          )}
        >
          {change > 0 ? (
            <TrendingUp className="w-4 h-4 mr-0.5" />
          ) : (
            <TrendingDown className="w-4 h-4 mr-0.5" />
          )}
          {change > 0 ? '+' : ''}{change.toFixed(1)}
        </span>
      )}
    </div>
  );
}

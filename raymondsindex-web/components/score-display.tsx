'use client';

import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Star } from 'lucide-react';

interface ScoreDisplayProps {
  score: number;
  previousScore?: number;
  showChange?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  /** 우수 점수(95+) 강조 표시 여부 */
  showExcellent?: boolean;
}

const sizeClasses = {
  sm: 'text-lg',
  md: 'text-2xl',
  lg: 'text-4xl',
};

/**
 * 점수 포맷팅
 * - 100 초과: "100+" 표시
 * - 그 외: 소수점 1자리
 */
function formatScore(score: number): string {
  if (score > 100) return '100+';
  return score.toFixed(1);
}

/**
 * 점수 등급에 따른 색상 클래스
 */
function getScoreColorClass(score: number): string {
  if (score >= 95) return 'text-[#FFD700]'; // Gold - A++
  if (score >= 88) return 'text-blue-400';  // A+
  if (score >= 80) return 'text-blue-300';  // A, A-
  return ''; // 기본색
}

export function ScoreDisplay({
  score,
  previousScore,
  showChange = false,
  size = 'md',
  className,
  showExcellent = false,
}: ScoreDisplayProps) {
  const change = previousScore ? score - previousScore : 0;
  const hasChange = showChange && previousScore !== undefined && change !== 0;
  const isExcellent = score >= 95;
  const scoreColorClass = showExcellent ? getScoreColorClass(score) : '';

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span className={cn('font-bold', sizeClasses[size], scoreColorClass)}>
        {formatScore(score)}
      </span>
      <span className="text-gray-400 text-sm">점</span>

      {/* 우수 점수 표시 (95+) */}
      {showExcellent && isExcellent && (
        <Star className="w-4 h-4 text-[#FFD700] fill-[#FFD700]" />
      )}

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

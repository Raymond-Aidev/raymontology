'use client';

import { cn } from '@/lib/utils';
import { GRADE_COLORS, type Grade } from '@/lib/constants';

interface GradeBadgeProps {
  grade: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showLabel?: boolean;
  className?: string;
}

const sizeClasses = {
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-14 h-14 text-lg font-semibold',
  xl: 'w-20 h-20 text-2xl font-bold',
};

export function GradeBadge({ grade, size = 'md', showLabel = false, className }: GradeBadgeProps) {
  const gradeKey = grade as Grade;
  const colors = GRADE_COLORS[gradeKey] || { bg: '#6B7280', text: 'white', label: '미평가' };

  return (
    <div className={cn('flex flex-col items-center gap-1', className)}>
      <div
        className={cn(
          'rounded-lg flex items-center justify-center font-semibold shadow-sm',
          sizeClasses[size]
        )}
        style={{
          backgroundColor: colors.bg,
          color: colors.text,
        }}
      >
        {grade}
      </div>
      {showLabel && (
        <span className="text-xs text-gray-500">{colors.label}</span>
      )}
    </div>
  );
}

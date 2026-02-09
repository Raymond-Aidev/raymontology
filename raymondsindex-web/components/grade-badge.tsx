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

// A++ 등급 특별 스타일 (골드 테두리 + 글로우)
const isTopGrade = (grade: string) => grade === 'A++';

export function GradeBadge({ grade, size = 'md', showLabel = false, className }: GradeBadgeProps) {
  const gradeKey = grade as Grade;
  const colors = GRADE_COLORS[gradeKey] || { bg: '#6B7280', text: 'white', label: '미평가' };
  const isExcellent = isTopGrade(grade);

  return (
    <div className={cn('flex flex-col items-center gap-1', className)}>
      {/* A++ 등급: 골드 외곽 링 */}
      <div
        className={cn(
          'rounded-lg flex items-center justify-center font-semibold',
          sizeClasses[size],
          isExcellent && 'ring-2 ring-[#FFD700] ring-offset-1 ring-offset-white shadow-[0_0_12px_rgba(255,215,0,0.4)]'
        )}
        style={{
          backgroundColor: colors.bg,
          color: colors.text,
        }}
      >
        {grade}
      </div>
      {showLabel && (
        <span className={cn(
          'text-xs',
          isExcellent ? 'text-[#FFD700] font-medium' : 'text-gray-500'
        )}>
          {colors.label}
        </span>
      )}
    </div>
  );
}

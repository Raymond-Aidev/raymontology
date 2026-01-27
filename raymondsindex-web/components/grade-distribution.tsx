'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart3 } from 'lucide-react';
import { GRADE_COLORS, GRADE_ORDER, type Grade } from '@/lib/constants';

interface GradeDistributionProps {
  distribution: {
    grade: string;
    count: number;
    percentage: number;
  }[];
  isLoading?: boolean;
}

export function GradeDistribution({ distribution, isLoading }: GradeDistributionProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5 text-sm">
            <BarChart3 className="w-3.5 h-3.5 text-[#5E6AD2]" />
            전체 등급 분포
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-1">
            {[...Array(9)].map((_, i) => (
              <div key={i} className="h-5 bg-zinc-800 rounded" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Sort by grade order and ensure all grades are present
  const sortedDistribution = GRADE_ORDER.map((grade) => {
    const found = distribution.find((d) => d.grade === grade);
    return {
      grade,
      count: found?.count || 0,
      percentage: found?.percentage || 0,
    };
  });

  const maxPercentage = Math.max(...sortedDistribution.map((d) => d.percentage), 1);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5 text-sm">
          <BarChart3 className="w-3.5 h-3.5 text-[#5E6AD2]" />
          전체 등급 분포
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-1">
          {sortedDistribution.map(({ grade, count, percentage }) => {
            const colors = GRADE_COLORS[grade as Grade];
            const barWidth = (percentage / maxPercentage) * 100;

            return (
              <div key={grade} className="flex items-center gap-2">
                <div
                  className="w-8 h-5 rounded flex items-center justify-center text-[10px] font-semibold shrink-0"
                  style={{
                    backgroundColor: colors?.bg || '#6B7280',
                    color: colors?.text || 'white',
                  }}
                >
                  {grade}
                </div>
                <div className="flex-1 h-5 bg-zinc-800 rounded overflow-hidden">
                  <div
                    className="h-full rounded transition-all duration-500 flex items-center justify-end pr-1.5"
                    style={{
                      width: `${Math.max(barWidth, 5)}%`,
                      backgroundColor: colors?.bg || '#6B7280',
                    }}
                  >
                    {percentage >= 8 && (
                      <span className="text-[10px] font-medium text-white">
                        {percentage.toFixed(1)}%
                      </span>
                    )}
                  </div>
                </div>
                <div className="w-12 text-right text-xs text-zinc-400 shrink-0">
                  {count.toLocaleString()}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

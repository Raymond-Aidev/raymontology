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
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-500" />
            전체 등급 분포
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            {[...Array(9)].map((_, i) => (
              <div key={i} className="h-8 bg-gray-100 rounded" />
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
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-blue-500" />
          전체 등급 분포
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {sortedDistribution.map(({ grade, count, percentage }) => {
            const colors = GRADE_COLORS[grade as Grade];
            const barWidth = (percentage / maxPercentage) * 100;

            return (
              <div key={grade} className="flex items-center gap-3">
                <div
                  className="w-10 h-7 rounded flex items-center justify-center text-xs font-semibold shrink-0"
                  style={{
                    backgroundColor: colors?.bg || '#6B7280',
                    color: colors?.text || 'white',
                  }}
                >
                  {grade}
                </div>
                <div className="flex-1 h-7 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500 flex items-center justify-end pr-2"
                    style={{
                      width: `${Math.max(barWidth, 5)}%`,
                      backgroundColor: colors?.bg || '#6B7280',
                    }}
                  >
                    {percentage >= 5 && (
                      <span className="text-xs font-medium text-white">
                        {percentage.toFixed(1)}%
                      </span>
                    )}
                  </div>
                </div>
                <div className="w-16 text-right text-sm text-gray-600 shrink-0">
                  {count.toLocaleString()}개
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

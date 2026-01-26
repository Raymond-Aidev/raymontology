'use client';

import { useTopRanking } from '@/hooks/use-ranking';
import { useStatistics } from '@/hooks/use-statistics';
import { TopCompaniesTable } from '@/components/top-companies-table';
import { GradeDistribution } from '@/components/grade-distribution';
import { KPICard, KPIGrid } from '@/components/kpi-card';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Building2, Calendar, BarChart3, Trophy, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export default function HomePage() {
  const { data: rankingData, isLoading: rankingLoading } = useTopRanking(10);
  const { data: statsData, isLoading: statsLoading } = useStatistics();

  // A등급 이상 기업 수 계산
  const aGradeCount = statsData?.grade_distribution
    ?.filter(g => g.grade.startsWith('A'))
    .reduce((sum, g) => sum + g.count, 0) || 0;

  const aGradePercentage = statsData?.total_companies
    ? (aGradeCount / statsData.total_companies) * 100
    : 0;

  return (
    <div className="min-h-screen bg-background">
      {/* 컴팩트 헤더 섹션 */}
      <section className="border-b bg-gradient-to-b from-blue-50/50 to-background">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-foreground">
                RaymondsIndex<sup className="text-sm">TM</sup> 2025
              </h1>
              <p className="text-muted-foreground mt-1">
                당신의 투자금, 제대로 쓰이고 있습니까?
              </p>
            </div>
            <Link
              href="/methodology"
              className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              평가 방법론 <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* KPI 카드 그리드 */}
      <section className="container mx-auto px-4 py-6">
        <KPIGrid columns={4}>
          <KPICard
            title="분석 기업"
            value={statsData?.total_companies || '-'}
            suffix="개"
            icon={Building2}
            isLoading={statsLoading}
          />
          <KPICard
            title="평균 점수"
            value={statsData?.average_score?.toFixed(1) || '-'}
            suffix="점"
            icon={BarChart3}
            trend={{ direction: 'stable' }}
            isLoading={statsLoading}
          />
          <KPICard
            title="A등급 이상"
            value={aGradeCount || '-'}
            suffix="개"
            icon={Trophy}
            percentage={aGradePercentage}
            isLoading={statsLoading}
          />
          <KPICard
            title="데이터 기준일"
            value={statsData?.updated_at
              ? new Date(statsData.updated_at).toLocaleDateString('ko-KR', {
                  year: 'numeric',
                  month: 'short',
                })
              : '-'}
            icon={Calendar}
            subtitle={statsData?.updated_at
              ? `${Math.floor((Date.now() - new Date(statsData.updated_at).getTime()) / (1000 * 60 * 60 * 24))}일 전`
              : undefined}
            isLoading={statsLoading}
          />
        </KPIGrid>
      </section>

      {/* 메인 콘텐츠 */}
      <section className="container mx-auto px-4 pb-12">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* TOP 10 테이블 (2/3) */}
          <div className="lg:col-span-2">
            <TopCompaniesTable
              companies={rankingData?.items || []}
              isLoading={rankingLoading}
            />
          </div>

          {/* 사이드 패널 (1/3) */}
          <div className="space-y-6">
            {/* 등급 분포 */}
            <GradeDistribution
              distribution={statsData?.grade_distribution || []}
              isLoading={statsLoading}
            />

            {/* 빠른 링크 */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">빠른 탐색</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Link
                  href="/screener"
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors"
                >
                  <span className="font-medium">전체 기업 스크리너</span>
                  <ArrowRight className="w-4 h-4 text-muted-foreground" />
                </Link>
                <Link
                  href="/ma-target"
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors"
                >
                  <span className="font-medium">M&A 타겟 분석</span>
                  <ArrowRight className="w-4 h-4 text-muted-foreground" />
                </Link>
                <Link
                  href="/screener?grade=A%2B%2B,A%2B,A,A-"
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors"
                >
                  <span className="font-medium">A등급 기업만 보기</span>
                  <ArrowRight className="w-4 h-4 text-muted-foreground" />
                </Link>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
    </div>
  );
}

'use client';

import { useState, useEffect } from 'react';
import { useBottomRanking } from '@/hooks/use-ranking';
import { useStatistics } from '@/hooks/use-statistics';
import { RiskCompaniesTable } from '@/components/risk-companies-table';
import { SubIndexTabs } from '@/components/sub-index-tabs';
import { VulnerableMACards } from '@/components/vulnerable-ma-cards';
import { GradeDistribution } from '@/components/grade-distribution';
import { KPICard, KPIGrid } from '@/components/kpi-card';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Building2, Calendar, BarChart3, AlertTriangle, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export default function HomePage() {
  const { data: riskData, isLoading: riskLoading } = useBottomRanking(10);
  const { data: statsData, isLoading: statsLoading } = useStatistics();

  // C등급 이하 기업 수 계산 (위험기업)
  const cGradeCount = statsData?.grade_distribution
    ?.filter(g => g.grade.startsWith('C'))
    .reduce((sum, g) => sum + g.count, 0) || 0;

  const cGradePercentage = statsData?.total_companies
    ? (cGradeCount / statsData.total_companies) * 100
    : 0;

  // 데이터 업데이트 경과일 계산 (requestAnimationFrame으로 setState 지연)
  const [daysSinceUpdate, setDaysSinceUpdate] = useState<string | undefined>(undefined);
  useEffect(() => {
    const rafId = requestAnimationFrame(() => {
      if (statsData?.updated_at) {
        const diff = Date.now() - new Date(statsData.updated_at).getTime();
        setDaysSinceUpdate(`${Math.floor(diff / (1000 * 60 * 60 * 24))}일 전`);
      } else {
        setDaysSinceUpdate(undefined);
      }
    });
    return () => cancelAnimationFrame(rafId);
  }, [statsData?.updated_at]);

  return (
    <div className="min-h-screen bg-background">
      {/* 컴팩트 헤더 섹션 - Linear 스타일 */}
      <section className="border-b border-gray-200">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-semibold text-foreground">
                RaymondsIndex<sup className="text-[10px]">TM</sup> 2025
              </h1>
              <span className="text-xs text-muted-foreground">
                당신의 투자금, 제대로 쓰이고 있습니까?
              </span>
            </div>
            <Link
              href="/methodology"
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              Whitepaper <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </section>

      {/* KPI 카드 그리드 */}
      <section className="container mx-auto px-4 py-3">
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
            title="C등급 이하"
            value={cGradeCount || '-'}
            suffix="개"
            icon={AlertTriangle}
            percentage={cGradePercentage}
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
            subtitle={daysSinceUpdate}
            isLoading={statsLoading}
          />
        </KPIGrid>
      </section>

      {/* 메인 콘텐츠 */}
      <section className="container mx-auto px-4 py-3">
        <div className="grid lg:grid-cols-3 gap-3">
          {/* 왼쪽 영역 (2/3) */}
          <div className="lg:col-span-2 space-y-3">
            {/* 위험기업 TOP 10 */}
            <RiskCompaniesTable
              companies={riskData?.items || []}
              isLoading={riskLoading}
            />

            {/* Sub-Index별 위험기업 */}
            <SubIndexTabs />
          </div>

          {/* 오른쪽 사이드 패널 (1/3) */}
          <div className="space-y-3">
            {/* M&A 취약기업 */}
            <VulnerableMACards limit={5} />

            {/* 등급 분포 */}
            <GradeDistribution
              distribution={statsData?.grade_distribution || []}
              isLoading={statsLoading}
            />

            {/* 빠른 링크 */}
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-sm">빠른 탐색</CardTitle>
              </CardHeader>
              <CardContent className="space-y-0.5">
                <Link
                  href="/screener"
                  className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-gray-50 transition-colors"
                >
                  <span className="text-sm text-gray-700">전체 기업 스크리너</span>
                  <ArrowRight className="w-3 h-3 text-gray-500" />
                </Link>
                <Link
                  href="/ma-target"
                  className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-gray-50 transition-colors"
                >
                  <span className="text-sm text-gray-700">적대적 M&A 분석</span>
                  <ArrowRight className="w-3 h-3 text-gray-500" />
                </Link>
                <Link
                  href="/screener?grade=C%2B,C"
                  className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-gray-50 transition-colors"
                >
                  <span className="text-sm text-gray-700">C등급 기업만 보기</span>
                  <ArrowRight className="w-3 h-3 text-gray-500" />
                </Link>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
    </div>
  );
}

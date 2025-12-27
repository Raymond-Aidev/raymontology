'use client';

import { useTopRanking } from '@/hooks/use-ranking';
import { useStatistics } from '@/hooks/use-statistics';
import { CompanySearchBar } from '@/components/company-search-bar';
import { TopCompaniesTable } from '@/components/top-companies-table';
import { GradeDistribution } from '@/components/grade-distribution';
import { BarChart3, Building2, Calendar } from 'lucide-react';

export default function HomePage() {
  const { data: rankingData, isLoading: rankingLoading } = useTopRanking(10);
  const { data: statsData, isLoading: statsLoading } = useStatistics();

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="bg-gradient-to-b from-blue-50 to-white py-16 md:py-24">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto text-center">
            <h1 className="text-3xl md:text-5xl font-bold text-gray-900 mb-4">
              RaymondsIndex<sup className="text-lg">TM</sup> 2025
            </h1>
            <p className="text-xl md:text-2xl text-gray-600 mb-8">
              당신의 투자금, 제대로 쓰이고 있습니까?
            </p>

            {/* Search Bar */}
            <div className="max-w-xl mx-auto mb-8">
              <CompanySearchBar
                placeholder="삼성전자, 현대차, SK하이닉스..."
                size="lg"
              />
            </div>

            {/* Stats */}
            <div className="flex flex-wrap justify-center gap-6 text-sm text-gray-500">
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4" />
                <span>
                  분석 기업 수:{' '}
                  <strong className="text-gray-900">
                    {statsData?.total_companies?.toLocaleString() || '-'}개
                  </strong>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                <span>
                  최근 업데이트:{' '}
                  <strong className="text-gray-900">
                    {statsData?.updated_at
                      ? new Date(statsData.updated_at).toLocaleDateString('ko-KR')
                      : '-'}
                  </strong>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                <span>
                  평균 점수:{' '}
                  <strong className="text-gray-900">
                    {statsData?.average_score?.toFixed(1) || '-'}점
                  </strong>
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <section className="py-12">
        <div className="container mx-auto px-4">
          <div className="grid lg:grid-cols-2 gap-8">
            {/* TOP 10 Table */}
            <TopCompaniesTable
              companies={rankingData?.items || []}
              isLoading={rankingLoading}
            />

            {/* Grade Distribution */}
            <GradeDistribution
              distribution={statsData?.grade_distribution || []}
              isLoading={statsLoading}
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-12 bg-gray-50">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            자본 배분 효율성이란?
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto mb-6">
            기업이 벌어들인 돈을 어디에, 어떻게 쓰는지 분석합니다.
            현금만 쌓아두는 기업과 성장에 재투자하는 기업을 구별하여
            투자자 관점의 인사이트를 제공합니다.
          </p>
          <a
            href="/methodology"
            className="inline-flex items-center gap-2 text-blue-600 font-medium hover:text-blue-700"
          >
            평가 방법론 자세히 보기 →
          </a>
        </div>
      </section>
    </div>
  );
}

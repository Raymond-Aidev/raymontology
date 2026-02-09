'use client';

import Link from 'next/link';
import { GradeBadge } from './grade-badge';
import { MarketBadge } from './market-badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle, ArrowRight } from 'lucide-react';
import type { RaymondsIndexResponse } from '@/lib/types';

interface RiskCompaniesTableProps {
  companies: RaymondsIndexResponse[];
  isLoading?: boolean;
  title?: string;
}

export function RiskCompaniesTable({
  companies,
  isLoading,
  title = 'RaymondsIndex 위험기업 TOP 10'
}: RiskCompaniesTableProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-1.5 text-sm">
            <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-2">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="h-14 bg-gray-200 rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-1.5 text-sm">
          <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
          {title}
        </CardTitle>
        <Button variant="ghost" size="sm" asChild className="h-6 text-xs">
          <Link href="/screener?sort=score_asc" className="flex items-center gap-1">
            전체 보기 <ArrowRight className="w-3 h-3" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-2">
          {companies.map((company, index) => (
            <RiskCompanyCard key={company.id} company={company} rank={index + 1} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

interface RiskCompanyCardProps {
  company: RaymondsIndexResponse;
  rank: number;
}

function RiskCompanyCard({ company, rank }: RiskCompanyCardProps) {
  return (
    <Link
      href={`/company/${company.company_id}`}
      className="flex items-center gap-2 p-2 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors border border-gray-200"
    >
      {/* 순위 */}
      <span className="text-xs font-bold text-gray-500 w-5 text-center">{rank}</span>

      {/* 기업 정보 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="font-medium text-gray-900 text-sm truncate">
            {company.company_name}
          </span>
          {company.market && (
            <MarketBadge
              market={company.market}
              tradingStatus={company.trading_status}
              size="sm"
            />
          )}
        </div>
        <span className="text-[10px] text-gray-500">{company.stock_code}</span>
      </div>

      {/* 등급 & 점수 */}
      <div className="flex items-center gap-2">
        <GradeBadge grade={company.grade} size="sm" />
        <span className="text-sm font-semibold text-red-400 w-10 text-right">
          {company.total_score.toFixed(1)}
        </span>
      </div>
    </Link>
  );
}

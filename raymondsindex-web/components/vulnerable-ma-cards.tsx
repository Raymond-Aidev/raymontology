'use client';

import Link from 'next/link';
import { GradeBadge } from './grade-badge';
import { MarketBadge } from './market-badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Target, ArrowRight, AlertTriangle, Users, TrendingDown } from 'lucide-react';
import { useVulnerableMA } from '@/hooks/use-ranking';
import type { VulnerableMACompany } from '@/lib/types';

interface VulnerableMACardsProps {
  limit?: number;
}

export function VulnerableMACards({ limit = 5 }: VulnerableMACardsProps) {
  const { data, isLoading } = useVulnerableMA({ limit, max_share_ratio: 5 });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5 text-sm">
            <Target className="w-3.5 h-3.5 text-purple-500" />
            적대적 M&A 취약기업 TOP {limit}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-20 bg-zinc-800 rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const companies = data?.rankings || [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-1.5 text-sm">
          <Target className="w-3.5 h-3.5 text-purple-500" />
          적대적 M&A 취약기업 TOP {limit}
        </CardTitle>
        <Button variant="ghost" size="sm" asChild className="h-6 text-xs">
          <Link href="/ma-target" className="flex items-center gap-1">
            더 보기 <ArrowRight className="w-3 h-3" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="text-xs text-zinc-500 mb-3">
          <AlertTriangle className="w-3 h-3 inline mr-1 text-yellow-500" />
          CEI+CGI 점수가 낮고 대주주 지분율 5% 이하인 기업
        </p>
        {companies.length === 0 ? (
          <div className="text-center py-6 text-zinc-500 text-sm">
            조건에 맞는 기업이 없습니다
          </div>
        ) : (
          companies.map((company, index) => (
            <VulnerableMACard key={company.company_id} company={company} rank={index + 1} />
          ))
        )}
      </CardContent>
    </Card>
  );
}

interface VulnerableMACardProps {
  company: VulnerableMACompany;
  rank: number;
}

function VulnerableMACard({ company, rank }: VulnerableMACardProps) {
  return (
    <Link
      href={`/company/${company.company_id}`}
      className="block p-3 rounded-lg bg-zinc-800/50 hover:bg-zinc-800 transition-colors border border-zinc-700/50"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-purple-400">#{rank}</span>
            <span className="font-medium text-white text-sm truncate">
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
          <p className="text-[10px] text-zinc-500 mt-0.5">{company.stock_code}</p>
        </div>
        <GradeBadge grade={company.grade} size="sm" />
      </div>
      <div className="grid grid-cols-3 gap-2 mt-2 text-xs">
        <div className="bg-zinc-900/50 rounded p-1.5">
          <div className="flex items-center gap-1 text-zinc-500">
            <TrendingDown className="w-3 h-3" />
            <span>CEI+CGI</span>
          </div>
          <p className="font-semibold text-orange-400">
            {company.vulnerability_score !== null
              ? company.vulnerability_score.toFixed(1)
              : '-'}
          </p>
        </div>
        <div className="bg-zinc-900/50 rounded p-1.5">
          <div className="flex items-center gap-1 text-zinc-500">
            <Users className="w-3 h-3" />
            <span>대주주</span>
          </div>
          <p className="font-semibold text-red-400">
            {company.largest_shareholder_ratio !== null
              ? `${company.largest_shareholder_ratio.toFixed(2)}%`
              : '-'}
          </p>
        </div>
        <div className="bg-zinc-900/50 rounded p-1.5">
          <div className="text-zinc-500">종합점수</div>
          <p className="font-semibold text-white">{company.total_score.toFixed(1)}</p>
        </div>
      </div>
      {company.largest_shareholder_name && (
        <p className="text-[10px] text-zinc-500 mt-1.5 truncate">
          최대주주: {company.largest_shareholder_name}
        </p>
      )}
    </Link>
  );
}

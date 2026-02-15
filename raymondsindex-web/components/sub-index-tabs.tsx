'use client';

import Link from 'next/link';
import { GradeBadge } from './grade-badge';
import { MarketBadge } from './market-badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowRight, TrendingDown, Building, Coins, Activity } from 'lucide-react';
import { useSubIndexRanking } from '@/hooks/use-ranking';

type SubIndexType = 'cei' | 'rii' | 'cgi' | 'mai';

interface SubIndexConfig {
  key: SubIndexType;
  label: string;
  fullName: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
  scoreKey: 'cei_score' | 'rii_score' | 'cgi_score' | 'mai_score';
}

const SUB_INDEX_CONFIG: SubIndexConfig[] = [
  {
    key: 'cei',
    label: 'CEI',
    fullName: '자본효율성',
    icon: Coins,
    description: '자본 활용 효율이 낮은 기업',
    scoreKey: 'cei_score',
  },
  {
    key: 'rii',
    label: 'RII',
    fullName: '재투자강도',
    icon: TrendingDown,
    description: '재투자가 부족한 기업',
    scoreKey: 'rii_score',
  },
  {
    key: 'cgi',
    label: 'CGI',
    fullName: '현금거버넌스',
    icon: Building,
    description: '현금 관리가 미흡한 기업',
    scoreKey: 'cgi_score',
  },
  {
    key: 'mai',
    label: 'MAI',
    fullName: '모멘텀정합성',
    icon: Activity,
    description: '성장-투자 동조성이 낮은 기업',
    scoreKey: 'mai_score',
  },
];

export function SubIndexCards() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {SUB_INDEX_CONFIG.map((config) => (
        <SubIndexCard key={config.key} config={config} />
      ))}
    </div>
  );
}

// 기존 export 호환 유지 (다른 곳에서 import 시 빌드 에러 방지)
export { SubIndexCards as SubIndexTabs };

interface SubIndexCardProps {
  config: SubIndexConfig;
}

function SubIndexCard({ config }: SubIndexCardProps) {
  const { data, isLoading } = useSubIndexRanking(config.key, 5, true);
  const companies = data?.items || [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-1.5 text-sm">
          <config.icon className="w-3.5 h-3.5 text-blue-500" />
          {config.fullName}
          <span className="text-xs font-normal text-gray-400">({config.label})</span>
        </CardTitle>
        <Button variant="ghost" size="sm" asChild className="h-6 text-xs">
          <Link href={`/screener?sort=${config.key}_asc`} className="flex items-center gap-1">
            더 보기 <ArrowRight className="w-3 h-3" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="animate-pulse space-y-1.5">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-7 bg-gray-200 rounded" />
            ))}
          </div>
        ) : (
          <>
            <p className="text-[11px] text-gray-400 mb-2">{config.description}</p>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8 px-1">#</TableHead>
                  <TableHead className="px-1">기업명</TableHead>
                  <TableHead className="text-center px-1">등급</TableHead>
                  <TableHead className="text-right px-1">{config.label}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {companies.map((company, index) => {
                  const subIndexScore = company[config.scoreKey];
                  return (
                    <TableRow key={company.id}>
                      <TableCell className="font-medium text-gray-400 text-xs px-1">
                        {index + 1}
                      </TableCell>
                      <TableCell className="px-1">
                        <div className="flex items-center gap-1">
                          <Link
                            href={`/company/${company.company_id}`}
                            className="font-medium text-gray-900 hover:text-[#8B95E8] text-xs transition-colors truncate max-w-[100px]"
                          >
                            {company.company_name}
                          </Link>
                          {company.market && (
                            <MarketBadge
                              market={company.market}
                              tradingStatus={company.trading_status}
                              size="sm"
                            />
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-center px-1">
                        <div className="flex justify-center">
                          <GradeBadge grade={company.grade} size="sm" />
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-semibold text-xs text-orange-400 px-1">
                        {subIndexScore !== null ? subIndexScore.toFixed(1) : '-'}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </>
        )}
      </CardContent>
    </Card>
  );
}

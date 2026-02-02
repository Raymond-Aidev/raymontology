'use client';

import { useState } from 'react';
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { BarChart3, ArrowRight, TrendingDown, Building, Coins, Activity } from 'lucide-react';
import { useSubIndexRanking } from '@/hooks/use-ranking';
import type { RaymondsIndexResponse } from '@/lib/types';

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

export function SubIndexTabs() {
  const [activeTab, setActiveTab] = useState<SubIndexType>('cei');

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-1.5 text-sm">
          <BarChart3 className="w-3.5 h-3.5 text-blue-500" />
          Sub-Index별 위험기업 TOP 10
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as SubIndexType)}>
          <TabsList className="grid grid-cols-4 mb-3">
            {SUB_INDEX_CONFIG.map((config) => (
              <TabsTrigger key={config.key} value={config.key} className="text-xs">
                {config.label}
              </TabsTrigger>
            ))}
          </TabsList>
          {SUB_INDEX_CONFIG.map((config) => (
            <TabsContent key={config.key} value={config.key}>
              <SubIndexTabContent config={config} />
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
}

interface SubIndexTabContentProps {
  config: SubIndexConfig;
}

function SubIndexTabContent({ config }: SubIndexTabContentProps) {
  const { data, isLoading } = useSubIndexRanking(config.key, 10, true);

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-1.5">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-8 bg-zinc-800 rounded" />
        ))}
      </div>
    );
  }

  const companies = data?.items || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-zinc-500">
          <config.icon className="w-3 h-3 inline mr-1" />
          {config.fullName} ({config.label}) - {config.description}
        </p>
        <Button variant="ghost" size="sm" asChild className="h-6 text-xs">
          <Link href={`/screener?sort=${config.key}_asc`} className="flex items-center gap-1">
            더 보기 <ArrowRight className="w-3 h-3" />
          </Link>
        </Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10">#</TableHead>
            <TableHead>기업명</TableHead>
            <TableHead className="text-center">등급</TableHead>
            <TableHead className="text-right">{config.label}</TableHead>
            <TableHead className="text-right hidden sm:table-cell">종합</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {companies.map((company, index) => {
            const subIndexScore = company[config.scoreKey];
            return (
              <TableRow key={company.id}>
                <TableCell className="font-medium text-zinc-500 text-xs">
                  {index + 1}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    <Link
                      href={`/company/${company.company_id}`}
                      className="font-medium text-white hover:text-[#8B95E8] text-sm transition-colors truncate max-w-[120px]"
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
                <TableCell className="text-center">
                  <div className="flex justify-center">
                    <GradeBadge grade={company.grade} size="sm" />
                  </div>
                </TableCell>
                <TableCell className="text-right font-semibold text-sm text-orange-400">
                  {subIndexScore !== null ? subIndexScore.toFixed(1) : '-'}
                </TableCell>
                <TableCell className="text-right text-xs text-zinc-500 hidden sm:table-cell">
                  {company.total_score.toFixed(1)}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

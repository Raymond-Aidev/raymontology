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
  title = '위험기업 TOP 10'
}: RiskCompaniesTableProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5 text-sm">
            <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-1.5">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-8 bg-zinc-800 rounded" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-1.5 text-sm">
          <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
          {title}
        </CardTitle>
        <Button variant="ghost" size="sm" asChild className="h-7 text-xs">
          <Link href="/screener?sort=score_asc" className="flex items-center gap-1">
            전체 보기 <ArrowRight className="w-3 h-3" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">#</TableHead>
              <TableHead>기업명</TableHead>
              <TableHead className="text-center">등급</TableHead>
              <TableHead className="text-right">점수</TableHead>
              <TableHead className="hidden md:table-cell">핵심 리스크</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {companies.map((company, index) => (
              <TableRow key={company.id}>
                <TableCell className="font-medium text-zinc-500 text-xs">
                  {index + 1}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    <Link
                      href={`/company/${company.company_id}`}
                      className="font-medium text-white hover:text-[#8B95E8] text-sm transition-colors"
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
                  <p className="text-[10px] text-zinc-500">{company.stock_code}</p>
                </TableCell>
                <TableCell className="text-center">
                  <div className="flex justify-center">
                    <GradeBadge grade={company.grade} size="sm" />
                  </div>
                </TableCell>
                <TableCell className="text-right font-semibold text-sm text-red-400">
                  {company.total_score.toFixed(1)}
                </TableCell>
                <TableCell className="hidden md:table-cell text-xs text-zinc-500">
                  {getRisk(company)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function getRisk(company: RaymondsIndexResponse): string {
  if (company.rii_score !== null && company.rii_score < 30) {
    return '재투자 부족';
  }
  if (company.cei_score !== null && company.cei_score < 30) {
    return '자본 효율성 낮음';
  }
  if (company.cgi_score !== null && company.cgi_score < 30) {
    return '현금 거버넌스 취약';
  }
  if (company.red_flags && company.red_flags.length > 0) {
    return company.red_flags[0];
  }
  return '종합 리스크';
}

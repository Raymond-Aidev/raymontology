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
import { Trophy, ArrowRight } from 'lucide-react';
import type { RaymondsIndexResponse } from '@/lib/types';

interface TopCompaniesTableProps {
  companies: RaymondsIndexResponse[];
  isLoading?: boolean;
}

export function TopCompaniesTable({ companies, isLoading }: TopCompaniesTableProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-yellow-500" />
            TOP 10 기업
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-100 rounded" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Trophy className="w-5 h-5 text-yellow-500" />
          TOP 10 기업
        </CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/screener" className="flex items-center gap-1">
            전체 보기 <ArrowRight className="w-4 h-4" />
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
              <TableHead className="hidden md:table-cell">핵심 강점</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {companies.map((company, index) => (
              <TableRow key={company.id}>
                <TableCell className="font-bold text-gray-500">
                  {index + 1}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/company/${company.company_id}`}
                      className="font-medium text-gray-900 hover:text-blue-600"
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
                  <p className="text-xs text-gray-500">{company.stock_code}</p>
                </TableCell>
                <TableCell className="text-center">
                  <div className="flex justify-center">
                    <GradeBadge grade={company.grade} size="sm" />
                  </div>
                </TableCell>
                <TableCell className="text-right font-semibold">
                  {company.total_score.toFixed(1)}
                </TableCell>
                <TableCell className="hidden md:table-cell text-sm text-gray-600">
                  {getStrength(company)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function getStrength(company: RaymondsIndexResponse): string {
  const scores = [
    { name: '높은 ROIC', score: company.roic || 0 },
    { name: '적극 재투자', score: company.reinvestment_rate || 0 },
    { name: '균형 배분', score: company.total_score },
  ];

  if (company.rii_score && company.rii_score >= 80) {
    return '적극 재투자';
  }
  if (company.cei_score && company.cei_score >= 85) {
    return '높은 ROIC';
  }
  if (company.cgi_score && company.cgi_score >= 80) {
    return '현금 거버넌스 우수';
  }
  return '균형 배분';
}

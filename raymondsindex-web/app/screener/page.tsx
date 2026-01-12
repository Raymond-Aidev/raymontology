'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRanking } from '@/hooks/use-ranking';
import { GradeBadge } from '@/components/grade-badge';
import { MarketBadge } from '@/components/market-badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Slider } from '@/components/ui/slider';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Filter, RotateCcw, ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { GRADE_ORDER, type Grade } from '@/lib/constants';
import type { RankingParams } from '@/lib/types';

const PAGE_SIZE = 20;
const MARKETS = ['KOSPI', 'KOSDAQ', 'KONEX'] as const;

export default function ScreenerPage() {
  const [params, setParams] = useState<RankingParams>({
    page: 1,
    size: PAGE_SIZE,
    sort: 'score_desc',
  });
  const [selectedGrades, setSelectedGrades] = useState<string[]>([]);
  const [selectedMarkets, setSelectedMarkets] = useState<string[]>([]);
  const [scoreRange, setScoreRange] = useState<[number, number]>([0, 100]);

  const { data, isLoading } = useRanking({
    ...params,
    grade: selectedGrades.length === 1 ? selectedGrades[0] : undefined,
    min_score: scoreRange[0] > 0 ? scoreRange[0] : undefined,
    max_score: scoreRange[1] < 100 ? scoreRange[1] : undefined,
  });

  const handleGradeToggle = (grade: string) => {
    setSelectedGrades((prev) =>
      prev.includes(grade)
        ? prev.filter((g) => g !== grade)
        : [...prev, grade]
    );
    setParams((prev) => ({ ...prev, page: 1 }));
  };

  const handleMarketToggle = (market: string) => {
    setSelectedMarkets((prev) =>
      prev.includes(market)
        ? prev.filter((m) => m !== market)
        : [...prev, market]
    );
    setParams((prev) => ({ ...prev, page: 1 }));
  };

  const handleReset = () => {
    setSelectedGrades([]);
    setSelectedMarkets([]);
    setScoreRange([0, 100]);
    setParams({ page: 1, size: PAGE_SIZE, sort: 'score_desc' });
  };

  const handlePageChange = (newPage: number) => {
    setParams((prev) => ({ ...prev, page: newPage }));
  };

  const filteredItems = data?.items.filter((item) => {
    if (selectedGrades.length > 0 && !selectedGrades.includes(item.grade)) {
      return false;
    }
    if (selectedMarkets.length > 0 && item.market && !selectedMarkets.includes(item.market)) {
      return false;
    }
    return true;
  }) || [];

  const totalPages = data?.total_pages || 1;
  const currentPage = params.page || 1;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">스크리너</h1>
        <p className="text-gray-600">
          조건에 맞는 기업을 검색하고 비교해보세요
        </p>
      </div>

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Filter Panel */}
        <Card className="lg:col-span-1 h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Filter className="w-5 h-5" />
              필터 조건
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Market Filter */}
            <div>
              <h4 className="font-medium text-gray-900 mb-3">거래소 필터</h4>
              <div className="flex gap-2">
                {MARKETS.map((market) => (
                  <button
                    key={market}
                    onClick={() => handleMarketToggle(market)}
                    className={`px-3 py-1.5 text-sm font-medium rounded border transition-colors ${
                      selectedMarkets.includes(market)
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-gray-700 border-gray-200 hover:border-blue-400'
                    }`}
                  >
                    {market}
                  </button>
                ))}
              </div>
            </div>

            {/* Grade Filter */}
            <div>
              <h4 className="font-medium text-gray-900 mb-3">등급 필터</h4>
              <div className="grid grid-cols-3 gap-2">
                {GRADE_ORDER.map((grade) => (
                  <button
                    key={grade}
                    onClick={() => handleGradeToggle(grade)}
                    className={`px-2 py-1.5 text-sm font-medium rounded border transition-colors ${
                      selectedGrades.includes(grade)
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-gray-700 border-gray-200 hover:border-blue-400'
                    }`}
                  >
                    {grade}
                  </button>
                ))}
              </div>
            </div>

            {/* Score Range */}
            <div>
              <h4 className="font-medium text-gray-900 mb-3">점수 범위</h4>
              <div className="px-1">
                <Slider
                  value={scoreRange}
                  onValueChange={(value) => {
                    setScoreRange(value as [number, number]);
                    setParams((prev) => ({ ...prev, page: 1 }));
                  }}
                  min={0}
                  max={100}
                  step={5}
                />
                <div className="flex justify-between text-sm text-gray-500 mt-2">
                  <span>{scoreRange[0]}점</span>
                  <span>{scoreRange[1]}점</span>
                </div>
              </div>
            </div>

            {/* Sort */}
            <div>
              <h4 className="font-medium text-gray-900 mb-3">정렬</h4>
              <Select
                value={params.sort}
                onValueChange={(value) =>
                  setParams((prev) => ({ ...prev, sort: value as RankingParams['sort'] }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="score_desc">점수 높은 순</SelectItem>
                  <SelectItem value="score_asc">점수 낮은 순</SelectItem>
                  <SelectItem value="name_asc">이름순 (ㄱ-ㅎ)</SelectItem>
                  <SelectItem value="name_desc">이름순 (ㅎ-ㄱ)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Reset Button */}
            <Button
              variant="outline"
              onClick={handleReset}
              className="w-full"
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              필터 초기화
            </Button>
          </CardContent>
        </Card>

        {/* Results Table */}
        <div className="lg:col-span-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>
                검색 결과: {data?.total?.toLocaleString() || 0}개 기업
              </CardTitle>
              {selectedGrades.length > 0 && (
                <div className="flex gap-1">
                  {selectedGrades.map((grade) => (
                    <Badge key={grade} variant="secondary">
                      {grade}
                    </Badge>
                  ))}
                </div>
              )}
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="animate-pulse space-y-3">
                  {[...Array(10)].map((_, i) => (
                    <div key={i} className="h-14 bg-gray-100 rounded" />
                  ))}
                </div>
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>기업명</TableHead>
                        <TableHead className="text-center">등급</TableHead>
                        <TableHead className="text-right">종합</TableHead>
                        <TableHead className="text-right hidden md:table-cell">CEI</TableHead>
                        <TableHead className="text-right hidden md:table-cell">RII</TableHead>
                        <TableHead className="text-right hidden md:table-cell">CGI</TableHead>
                        <TableHead className="text-right hidden md:table-cell">MAI</TableHead>
                        <TableHead className="text-center">상세</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredItems.map((company) => (
                        <TableRow key={company.id}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <p className="font-medium">{company.company_name}</p>
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
                          <TableCell className="text-right hidden md:table-cell text-gray-600">
                            {company.cei_score?.toFixed(1) || '-'}
                          </TableCell>
                          <TableCell className="text-right hidden md:table-cell text-gray-600">
                            {company.rii_score?.toFixed(1) || '-'}
                          </TableCell>
                          <TableCell className="text-right hidden md:table-cell text-gray-600">
                            {company.cgi_score?.toFixed(1) || '-'}
                          </TableCell>
                          <TableCell className="text-right hidden md:table-cell text-gray-600">
                            {company.mai_score?.toFixed(1) || '-'}
                          </TableCell>
                          <TableCell className="text-center">
                            <Button variant="ghost" size="sm" asChild>
                              <Link href={`/company/${company.company_id}`}>
                                보기
                              </Link>
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-center gap-2 mt-6">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={currentPage === 1}
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </Button>
                      <span className="text-sm text-gray-600">
                        {currentPage} / {totalPages}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={currentPage >= totalPages}
                      >
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

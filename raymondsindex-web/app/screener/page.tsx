'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { useRanking } from '@/hooks/use-ranking';
import { GradeBadge } from '@/components/grade-badge';
import { MarketBadge } from '@/components/market-badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Filter, RotateCcw, ChevronLeft, ChevronRight, ChevronDown, AlertTriangle, Check } from 'lucide-react';
import { GRADE_ORDER } from '@/lib/constants';
import { useCompareStore, MAX_COMPARE_ITEMS } from '@/lib/compare-store';
import { CompareBar } from '@/components/compare-bar';
import { CompareModal } from '@/components/compare-modal';
import type { RankingParams } from '@/lib/types';

const PAGE_SIZE = 20;
const MARKETS = ['KOSPI', 'KOSDAQ'] as const;

// 필터 상태 타입 정의 (확장 가능)
interface FilterState {
  grades: string[];
  markets: string[];
  scoreRange: [number, number];
  // Sub-Index 필터 (확장)
  ceiRange: [number, number];
  riiRange: [number, number];
  cgiRange: [number, number];
  maiRange: [number, number];
  // 기타 필터
  gapRange: [number, number];
  hasRedFlags: boolean | null;
}

const DEFAULT_FILTERS: FilterState = {
  grades: [],
  markets: [],
  scoreRange: [0, 100],
  ceiRange: [0, 100],
  riiRange: [0, 100],
  cgiRange: [0, 100],
  maiRange: [0, 100],
  gapRange: [-100, 100],
  hasRedFlags: null,
};

export default function ScreenerPage() {
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<RankingParams['sort']>('score_asc');
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  // API 파라미터 구성 (서버 사이드 필터링)
  const buildParams = useCallback((): RankingParams => {
    const params: RankingParams = {
      page,
      size: PAGE_SIZE,
      sort,
    };

    // 등급 필터 (복수 지원)
    if (filters.grades.length > 0) {
      params.grade = filters.grades.join(',');
    }

    // 시장 필터 (복수 지원)
    if (filters.markets.length > 0) {
      params.market = filters.markets.join(',');
    }

    // 점수 범위 필터
    if (filters.scoreRange[0] > 0) {
      params.min_score = filters.scoreRange[0];
    }
    if (filters.scoreRange[1] < 100) {
      params.max_score = filters.scoreRange[1];
    }

    // Sub-Index 필터 (고급)
    if (filters.ceiRange[0] > 0) params.min_cei = filters.ceiRange[0];
    if (filters.ceiRange[1] < 100) params.max_cei = filters.ceiRange[1];
    if (filters.riiRange[0] > 0) params.min_rii = filters.riiRange[0];
    if (filters.riiRange[1] < 100) params.max_rii = filters.riiRange[1];
    if (filters.cgiRange[0] > 0) params.min_cgi = filters.cgiRange[0];
    if (filters.cgiRange[1] < 100) params.max_cgi = filters.cgiRange[1];
    if (filters.maiRange[0] > 0) params.min_mai = filters.maiRange[0];
    if (filters.maiRange[1] < 100) params.max_mai = filters.maiRange[1];

    // 투자괴리율 필터
    if (filters.gapRange[0] > -100) params.min_gap = filters.gapRange[0];
    if (filters.gapRange[1] < 100) params.max_gap = filters.gapRange[1];

    // Red Flag 필터
    if (filters.hasRedFlags !== null) {
      params.has_red_flags = filters.hasRedFlags;
    }

    return params;
  }, [page, sort, filters]);

  const { data, isLoading } = useRanking(buildParams());

  // 비교 기능
  const { items: compareItems, toggleItem, isSelected } = useCompareStore();

  // 필터 토글 핸들러
  const handleGradeToggle = (grade: string) => {
    setFilters((prev) => ({
      ...prev,
      grades: prev.grades.includes(grade)
        ? prev.grades.filter((g) => g !== grade)
        : [...prev.grades, grade],
    }));
    setPage(1);
  };

  const handleMarketToggle = (market: string) => {
    setFilters((prev) => ({
      ...prev,
      markets: prev.markets.includes(market)
        ? prev.markets.filter((m) => m !== market)
        : [...prev.markets, market],
    }));
    setPage(1);
  };

  const handleReset = () => {
    setFilters(DEFAULT_FILTERS);
    setSort('score_desc');
    setPage(1);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  // 활성 필터 카운트
  const activeFilterCount =
    filters.grades.length +
    filters.markets.length +
    (filters.scoreRange[0] > 0 || filters.scoreRange[1] < 100 ? 1 : 0) +
    (filters.ceiRange[0] > 0 || filters.ceiRange[1] < 100 ? 1 : 0) +
    (filters.riiRange[0] > 0 || filters.riiRange[1] < 100 ? 1 : 0) +
    (filters.cgiRange[0] > 0 || filters.cgiRange[1] < 100 ? 1 : 0) +
    (filters.maiRange[0] > 0 || filters.maiRange[1] < 100 ? 1 : 0) +
    (filters.gapRange[0] > -100 || filters.gapRange[1] < 100 ? 1 : 0) +
    (filters.hasRedFlags !== null ? 1 : 0);

  const totalPages = data?.total_pages || 1;
  const currentPage = page;

  return (
    <div className={`container mx-auto px-4 py-3 ${compareItems.length > 0 ? 'pb-20' : ''}`}>
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-white">스크리너</h1>
          <p className="text-xs text-zinc-500">
            조건에 맞는 기업을 검색하고 비교해보세요
          </p>
        </div>
        {/* 프리셋 필터 (빠른 필터) - 인라인 */}
        <div className="flex flex-wrap gap-1.5">
          <Button
            variant={filters.grades.length === 4 && filters.grades.includes('A++') ? 'default' : 'outline'}
            size="sm"
            className="h-7 text-xs"
            onClick={() => {
              setFilters((prev) => ({
                ...prev,
                grades: ['A++', 'A+', 'A', 'A-'],
              }));
              setPage(1);
            }}
          >
            A등급 이상
          </Button>
          <Button
            variant={filters.hasRedFlags === false ? 'default' : 'outline'}
            size="sm"
            className="h-7 text-xs"
            onClick={() => {
              setFilters((prev) => ({
                ...prev,
                hasRedFlags: prev.hasRedFlags === false ? null : false,
              }));
              setPage(1);
            }}
          >
            위험신호 없음
          </Button>
          <Button
            variant={filters.scoreRange[0] >= 70 ? 'default' : 'outline'}
            size="sm"
            className="h-7 text-xs"
            onClick={() => {
              setFilters((prev) => ({
                ...prev,
                scoreRange: [70, 100],
              }));
              setPage(1);
            }}
          >
            70점 이상
          </Button>
          <Button
            variant={filters.ceiRange[0] >= 80 ? 'default' : 'outline'}
            size="sm"
            className="h-7 text-xs hidden md:inline-flex"
            onClick={() => {
              setFilters((prev) => ({
                ...prev,
                ceiRange: [80, 100],
              }));
              setPage(1);
              setAdvancedOpen(true);
            }}
          >
            높은 ROIC
          </Button>
          <Button
            variant={filters.gapRange[1] <= 0 ? 'default' : 'outline'}
            size="sm"
            className="h-7 text-xs hidden md:inline-flex"
            onClick={() => {
              setFilters((prev) => ({
                ...prev,
                gapRange: [-100, 0],
              }));
              setPage(1);
              setAdvancedOpen(true);
            }}
          >
            과소투자
          </Button>
        </div>
      </div>

      <div className="grid lg:grid-cols-4 gap-3">
        {/* Filter Panel */}
        <Card className="lg:col-span-1 h-fit">
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-1.5">
                <Filter className="w-3.5 h-3.5" />
                필터 조건
              </span>
              {activeFilterCount > 0 && (
                <Badge variant="secondary" className="text-[10px] h-5">{activeFilterCount}</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Market Filter */}
            <div>
              <h4 className="text-xs font-medium text-zinc-400 mb-1.5">거래소</h4>
              <div className="flex gap-1.5">
                {MARKETS.map((market) => (
                  <button
                    key={market}
                    onClick={() => handleMarketToggle(market)}
                    className={`px-2 py-1 text-xs font-medium rounded border transition-colors ${
                      filters.markets.includes(market)
                        ? 'bg-[#5E6AD2] text-white border-[#5E6AD2]'
                        : 'bg-zinc-800 text-zinc-300 border-white/10 hover:border-[#5E6AD2]/50'
                    }`}
                  >
                    {market}
                  </button>
                ))}
              </div>
            </div>

            {/* Grade Filter */}
            <div>
              <h4 className="text-xs font-medium text-zinc-400 mb-1.5">등급</h4>
              <div className="grid grid-cols-3 gap-1">
                {GRADE_ORDER.map((grade) => (
                  <button
                    key={grade}
                    onClick={() => handleGradeToggle(grade)}
                    className={`px-1.5 py-1 text-xs font-medium rounded border transition-colors ${
                      filters.grades.includes(grade)
                        ? 'bg-[#5E6AD2] text-white border-[#5E6AD2]'
                        : 'bg-zinc-800 text-zinc-300 border-white/10 hover:border-[#5E6AD2]/50'
                    }`}
                  >
                    {grade}
                  </button>
                ))}
              </div>
            </div>

            {/* Score Range */}
            <div>
              <h4 className="text-xs font-medium text-zinc-400 mb-1.5">종합 점수</h4>
              <div className="px-0.5">
                <Slider
                  value={filters.scoreRange}
                  onValueChange={(value) => {
                    setFilters((prev) => ({ ...prev, scoreRange: value as [number, number] }));
                    setPage(1);
                  }}
                  min={0}
                  max={100}
                  step={5}
                />
                <div className="flex justify-between text-xs text-zinc-300 mt-1">
                  <span>{filters.scoreRange[0]}점</span>
                  <span>{filters.scoreRange[1]}점</span>
                </div>
              </div>
            </div>

            {/* Red Flag Filter */}
            <div>
              <h4 className="text-xs font-medium text-zinc-400 mb-1.5">위험 신호</h4>
              <div className="flex gap-1.5">
                <button
                  onClick={() => {
                    setFilters((prev) => ({
                      ...prev,
                      hasRedFlags: prev.hasRedFlags === false ? null : false,
                    }));
                    setPage(1);
                  }}
                  className={`px-2 py-1 text-xs font-medium rounded border transition-colors ${
                    filters.hasRedFlags === false
                      ? 'bg-green-600 text-white border-green-600'
                      : 'bg-zinc-800 text-zinc-300 border-white/10 hover:border-green-500/50'
                  }`}
                >
                  없음
                </button>
                <button
                  onClick={() => {
                    setFilters((prev) => ({
                      ...prev,
                      hasRedFlags: prev.hasRedFlags === true ? null : true,
                    }));
                    setPage(1);
                  }}
                  className={`flex items-center gap-0.5 px-2 py-1 text-xs font-medium rounded border transition-colors ${
                    filters.hasRedFlags === true
                      ? 'bg-red-600 text-white border-red-600'
                      : 'bg-zinc-800 text-zinc-300 border-white/10 hover:border-red-500/50'
                  }`}
                >
                  <AlertTriangle className="w-2.5 h-2.5" />
                  있음
                </button>
              </div>
            </div>

            {/* Sort */}
            <div>
              <h4 className="text-xs font-medium text-zinc-400 mb-1.5">정렬</h4>
              <Select
                value={sort}
                onValueChange={(value) => {
                  setSort(value as RankingParams['sort']);
                  setPage(1);
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="score_desc">점수 높은 순</SelectItem>
                  <SelectItem value="score_asc">점수 낮은 순</SelectItem>
                  <SelectItem value="name_asc">이름순 (ㄱ-ㅎ)</SelectItem>
                  <SelectItem value="name_desc">이름순 (ㅎ-ㄱ)</SelectItem>
                  <SelectItem value="cei_desc">CEI 높은 순</SelectItem>
                  <SelectItem value="rii_desc">RII 높은 순</SelectItem>
                  <SelectItem value="cgi_desc">CGI 높은 순</SelectItem>
                  <SelectItem value="mai_desc">MAI 높은 순</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Advanced Filters (Collapsible) */}
            <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" className="w-full justify-between h-7 text-xs">
                  <span>고급 필터</span>
                  <ChevronDown className={`w-3 h-3 transition-transform ${advancedOpen ? 'rotate-180' : ''}`} />
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="space-y-2.5 pt-2">
                {/* CEI Range */}
                <div>
                  <h4 className="text-[10px] font-medium text-zinc-500 mb-1">CEI (자본효율성)</h4>
                  <Slider
                    value={filters.ceiRange}
                    onValueChange={(value) => {
                      setFilters((prev) => ({ ...prev, ceiRange: value as [number, number] }));
                      setPage(1);
                    }}
                    min={0}
                    max={100}
                    step={5}
                  />
                  <div className="flex justify-between text-[10px] text-zinc-500 mt-0.5">
                    <span>{filters.ceiRange[0]}</span>
                    <span>{filters.ceiRange[1]}</span>
                  </div>
                </div>

                {/* RII Range */}
                <div>
                  <h4 className="text-[10px] font-medium text-zinc-500 mb-1">RII (재투자)</h4>
                  <Slider
                    value={filters.riiRange}
                    onValueChange={(value) => {
                      setFilters((prev) => ({ ...prev, riiRange: value as [number, number] }));
                      setPage(1);
                    }}
                    min={0}
                    max={100}
                    step={5}
                  />
                  <div className="flex justify-between text-[10px] text-zinc-500 mt-0.5">
                    <span>{filters.riiRange[0]}</span>
                    <span>{filters.riiRange[1]}</span>
                  </div>
                </div>

                {/* CGI Range */}
                <div>
                  <h4 className="text-[10px] font-medium text-zinc-500 mb-1">CGI (현금거버넌스)</h4>
                  <Slider
                    value={filters.cgiRange}
                    onValueChange={(value) => {
                      setFilters((prev) => ({ ...prev, cgiRange: value as [number, number] }));
                      setPage(1);
                    }}
                    min={0}
                    max={100}
                    step={5}
                  />
                  <div className="flex justify-between text-[10px] text-zinc-500 mt-0.5">
                    <span>{filters.cgiRange[0]}</span>
                    <span>{filters.cgiRange[1]}</span>
                  </div>
                </div>

                {/* MAI Range */}
                <div>
                  <h4 className="text-[10px] font-medium text-zinc-500 mb-1">MAI (시장정렬)</h4>
                  <Slider
                    value={filters.maiRange}
                    onValueChange={(value) => {
                      setFilters((prev) => ({ ...prev, maiRange: value as [number, number] }));
                      setPage(1);
                    }}
                    min={0}
                    max={100}
                    step={5}
                  />
                  <div className="flex justify-between text-[10px] text-zinc-500 mt-0.5">
                    <span>{filters.maiRange[0]}</span>
                    <span>{filters.maiRange[1]}</span>
                  </div>
                </div>

                {/* Investment Gap Range */}
                <div>
                  <h4 className="text-[10px] font-medium text-zinc-500 mb-1">투자괴리율 (%)</h4>
                  <Slider
                    value={filters.gapRange}
                    onValueChange={(value) => {
                      setFilters((prev) => ({ ...prev, gapRange: value as [number, number] }));
                      setPage(1);
                    }}
                    min={-100}
                    max={100}
                    step={10}
                  />
                  <div className="flex justify-between text-[10px] text-zinc-500 mt-0.5">
                    <span>{filters.gapRange[0]}%</span>
                    <span>{filters.gapRange[1]}%</span>
                  </div>
                </div>
              </CollapsibleContent>
            </Collapsible>

            {/* Reset Button */}
            <Button
              variant="outline"
              onClick={handleReset}
              className="w-full h-7 text-xs"
              disabled={activeFilterCount === 0 && sort === 'score_desc'}
            >
              <RotateCcw className="w-3 h-3 mr-1" />
              필터 초기화
            </Button>
          </CardContent>
        </Card>

        {/* Results Table */}
        <div className="lg:col-span-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-sm">
                Filtered: {data?.total?.toLocaleString() || 0}개 기업
              </CardTitle>
              <div className="flex gap-1 flex-wrap">
                {filters.grades.map((grade) => (
                  <Badge key={grade} variant="secondary" className="text-[10px] h-5">
                    {grade}
                  </Badge>
                ))}
                {filters.markets.map((market) => (
                  <Badge key={market} variant="outline" className="text-[10px] h-5">
                    {market}
                  </Badge>
                ))}
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="animate-pulse space-y-1">
                  {[...Array(10)].map((_, i) => (
                    <div key={i} className="h-9 bg-zinc-800 rounded" />
                  ))}
                </div>
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-10">비교</TableHead>
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
                      {data?.items.map((company) => (
                        <TableRow key={company.id}>
                          <TableCell>
                            <button
                              onClick={() => toggleItem(company)}
                              disabled={!isSelected(company.company_id) && compareItems.length >= MAX_COMPARE_ITEMS}
                              className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                                isSelected(company.company_id)
                                  ? 'bg-[#5E6AD2] border-[#5E6AD2] text-white'
                                  : compareItems.length >= MAX_COMPARE_ITEMS
                                    ? 'bg-zinc-800 border-zinc-700 text-zinc-600 cursor-not-allowed'
                                    : 'border-zinc-600 hover:border-[#5E6AD2]'
                              }`}
                            >
                              {isSelected(company.company_id) && <Check className="w-3 h-3" />}
                            </button>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1.5">
                              <p className="font-medium text-sm text-white">{company.company_name}</p>
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
                          <TableCell className="text-right font-semibold text-sm text-white">
                            {company.total_score.toFixed(1)}
                          </TableCell>
                          <TableCell className="text-right hidden md:table-cell text-zinc-500 text-xs">
                            {company.cei_score?.toFixed(1) || '-'}
                          </TableCell>
                          <TableCell className="text-right hidden md:table-cell text-zinc-500 text-xs">
                            {company.rii_score?.toFixed(1) || '-'}
                          </TableCell>
                          <TableCell className="text-right hidden md:table-cell text-zinc-500 text-xs">
                            {company.cgi_score?.toFixed(1) || '-'}
                          </TableCell>
                          <TableCell className="text-right hidden md:table-cell text-zinc-500 text-xs">
                            {company.mai_score?.toFixed(1) || '-'}
                          </TableCell>
                          <TableCell className="text-center">
                            <Button variant="ghost" size="sm" asChild className="h-6 text-xs">
                              <Link href={`/company/${company.company_id}`}>
                                보기
                              </Link>
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  {/* Empty State */}
                  {data?.items.length === 0 && (
                    <div className="text-center py-8 text-zinc-500">
                      <p className="text-sm">조건에 맞는 기업이 없습니다.</p>
                      <Button variant="link" onClick={handleReset} className="text-xs text-[#8B95E8]">
                        필터 초기화하기
                      </Button>
                    </div>
                  )}

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-center gap-1.5 mt-4">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 w-7 p-0"
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={currentPage === 1}
                      >
                        <ChevronLeft className="w-3.5 h-3.5" />
                      </Button>
                      <span className="text-xs text-zinc-500 min-w-[60px] text-center">
                        {currentPage} / {totalPages}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 w-7 p-0"
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={currentPage >= totalPages}
                      >
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 비교 바 (선택된 기업이 있을 때 표시) */}
      <CompareBar />

      {/* 비교 모달 */}
      <CompareModal />
    </div>
  );
}

'use client';

import { useState, useCallback, useEffect } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { MarketBadge } from '@/components/market-badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CompactRangeInput } from '@/components/range-input';
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
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Filter,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  Target,
  TrendingUp,
  TrendingDown,
  Building2,
  HelpCircle,
  Loader2,
} from 'lucide-react';
import type { MATargetResponse, MATargetParams, MATargetStatsResponse } from '@/lib/types';
import { VulnerableMACards } from '@/components/vulnerable-ma-cards';

const PAGE_SIZE = 20;
const MARKETS = ['KOSPI', 'KOSDAQ'] as const;
const MA_GRADES = ['A+', 'A', 'B+', 'B', 'C+', 'C', 'D'] as const;

// M&A 타겟 등급별 색상
const MA_GRADE_COLORS: Record<string, string> = {
  'A+': 'bg-blue-600 text-white',
  'A': 'bg-blue-500 text-white',
  'B+': 'bg-green-500 text-white',
  'B': 'bg-green-400 text-white',
  'C+': 'bg-yellow-500 text-white',
  'C': 'bg-orange-500 text-white',
  'D': 'bg-gray-500 text-white',
};

// 필터 상태 타입
interface FilterState {
  grades: string[];
  markets: string[];
  marketCapRange: [number, number];  // 억원 (100억 ~ 10조)
  cashAssetsRange: [number, number]; // 억원 (0 ~ 5조)
  cashRatioRange: [number, number];  // % (0 ~ 100)
  revenueGrowthRange: [number, number]; // % (-50 ~ 100)
  tangibleGrowthRange: [number, number]; // % (-50 ~ 100)
}

const DEFAULT_FILTERS: FilterState = {
  grades: [],
  markets: [],
  marketCapRange: [100, 100000],  // 100억 ~ 10조
  cashAssetsRange: [0, 50000],    // 0 ~ 5조
  cashRatioRange: [0, 100],       // 0 ~ 100%
  revenueGrowthRange: [-50, 100], // -50 ~ 100%
  tangibleGrowthRange: [-50, 100], // -50 ~ 100%
};

// 숫자 포맷팅 함수
function formatNumber(num: number | null | undefined): string {
  if (num === null || num === undefined) return '-';
  return num.toLocaleString('ko-KR');
}

function formatMarketCap(num: number | null | undefined): string {
  if (num === null || num === undefined) return '-';
  const bil = num / 100_000_000;  // 억원
  if (bil >= 10000) {
    return `${(bil / 10000).toFixed(1)}조`;
  }
  return `${Math.round(bil).toLocaleString()}억`;
}

function formatPercent(num: number | null | undefined): string {
  if (num === null || num === undefined) return '-';
  const sign = num >= 0 ? '+' : '';
  return `${sign}${num.toFixed(1)}%`;
}

// M&A 등급 배지 컴포넌트
function MAGradeBadge({ grade }: { grade: string | null }) {
  if (!grade) return <span className="text-zinc-500">-</span>;
  return (
    <Badge className={`${MA_GRADE_COLORS[grade] || 'bg-zinc-600'} font-medium`}>
      {grade}
    </Badge>
  );
}

export default function MATargetPage() {
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<MATargetParams['sort']>('score_desc');
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);

  // 데이터 상태
  const [data, setData] = useState<{
    items: MATargetResponse[];
    total: number;
    total_pages: number;
    snapshot_date: string | null;
  } | null>(null);
  const [stats, setStats] = useState<MATargetStatsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // API 파라미터 구성
  const buildParams = useCallback((): MATargetParams => {
    const params: MATargetParams = {
      page,
      size: PAGE_SIZE,
      sort,
    };

    if (filters.grades.length > 0) {
      params.grade = filters.grades.join(',');
    }

    if (filters.markets.length > 0) {
      params.market = filters.markets.join(',');
    }

    // 시가총액 범위 (100억 ~ 10조)
    if (filters.marketCapRange[0] > 100) {
      params.min_market_cap = filters.marketCapRange[0];
    }
    if (filters.marketCapRange[1] < 100000) {
      params.max_market_cap = filters.marketCapRange[1];
    }

    // 현금성자산 범위 (0 ~ 5조)
    if (filters.cashAssetsRange[0] > 0) {
      params.min_cash_assets = filters.cashAssetsRange[0];
    }
    if (filters.cashAssetsRange[1] < 50000) {
      params.max_cash_assets = filters.cashAssetsRange[1];
    }

    // 현금/시총 비율 범위 (0 ~ 100%)
    if (filters.cashRatioRange[0] > 0) {
      params.min_cash_ratio = filters.cashRatioRange[0];
    }
    if (filters.cashRatioRange[1] < 100) {
      params.max_cash_ratio = filters.cashRatioRange[1];
    }

    // 매출 성장률 범위 (-50 ~ 100%)
    if (filters.revenueGrowthRange[0] > -50) {
      params.min_revenue_growth = filters.revenueGrowthRange[0];
    }
    if (filters.revenueGrowthRange[1] < 100) {
      params.max_revenue_growth = filters.revenueGrowthRange[1];
    }

    // 유형자산 증가율 범위 (-50 ~ 100%)
    if (filters.tangibleGrowthRange[0] > -50) {
      params.min_tangible_growth = filters.tangibleGrowthRange[0];
    }
    if (filters.tangibleGrowthRange[1] < 100) {
      params.max_tangible_growth = filters.tangibleGrowthRange[1];
    }

    return params;
  }, [page, sort, filters]);

  // 데이터 로드
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const params = buildParams();
        const [rankingData, statsData] = await Promise.all([
          api.maTarget.getRanking(params),
          api.maTarget.getStats(params),
        ]);
        setData(rankingData);
        setStats(statsData);
      } catch (err) {
        setError('데이터를 불러오는 중 오류가 발생했습니다.');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [buildParams]);

  // 필터 핸들러
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
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const totalPages = data?.total_pages || 0;

  // 활성화된 필터 개수 계산
  const countActiveFilters = () => {
    let count = 0;
    if (filters.grades.length > 0) count++;
    if (filters.markets.length > 0) count++;
    if (filters.marketCapRange[0] > 100 || filters.marketCapRange[1] < 100000) count++;
    if (filters.cashAssetsRange[0] > 0 || filters.cashAssetsRange[1] < 50000) count++;
    if (filters.cashRatioRange[0] > 0 || filters.cashRatioRange[1] < 100) count++;
    if (filters.revenueGrowthRange[0] > -50 || filters.revenueGrowthRange[1] < 100) count++;
    if (filters.tangibleGrowthRange[0] > -50 || filters.tangibleGrowthRange[1] < 100) count++;
    return count;
  };

  const activeFilterCount = countActiveFilters();
  const hasActiveFilters = activeFilterCount > 0;

  return (
    <div className="container mx-auto px-4 py-8">
      {/* 헤더 */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Target className="w-8 h-8 text-red-500" />
          <h1 className="text-3xl font-bold text-white">적대적 M&A 분석</h1>
        </div>
        <p className="text-zinc-400">
          적대적 M&A 검토 대상 기업을 분석합니다. 현금성 자산, 시가총액, 성장성 지표를 종합 평가합니다.
        </p>
        {data?.snapshot_date && (
          <p className="text-sm text-zinc-500 mt-1">
            기준일: {data.snapshot_date}
          </p>
        )}
      </div>

      {/* 통계 카드 */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-[#8B95E8]" />
                <div>
                  <p className="text-sm text-zinc-500">분석 기업</p>
                  <p className="text-2xl font-bold text-white">{formatNumber(stats.total_companies)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-2">
                <Target className="w-5 h-5 text-red-500" />
                <div>
                  <p className="text-sm text-zinc-500">평균 점수</p>
                  <p className="text-2xl font-bold text-white">{stats.average_score?.toFixed(1) || '-'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-400" />
                <div>
                  <p className="text-sm text-zinc-500">최고 점수</p>
                  <p className="text-2xl font-bold text-white">{stats.max_score?.toFixed(1) || '-'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-2">
                <TrendingDown className="w-5 h-5 text-orange-400" />
                <div>
                  <p className="text-sm text-zinc-500">최저 점수</p>
                  <p className="text-2xl font-bold text-white">{stats.min_score?.toFixed(1) || '-'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 적대적 M&A 취약기업 TOP 5 (컴팩트 그리드) */}
      <div className="mb-6">
        <VulnerableMACards limit={5} compact />
      </div>

      {/* 필터 섹션 */}
      <Card className="mb-6">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5" />
              <CardTitle className="text-lg">필터</CardTitle>
              {hasActiveFilters && (
                <Badge variant="secondary" className="ml-2">
                  {activeFilterCount}개 적용
                </Badge>
              )}
            </div>
            <Button variant="ghost" size="sm" onClick={handleReset}>
              <RotateCcw className="w-4 h-4 mr-1" />
              초기화
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* 등급 필터 */}
          <div>
            <p className="text-sm font-medium text-zinc-300 mb-2">적대적 M&A 등급</p>
            <div className="flex flex-wrap gap-2">
              {MA_GRADES.map((grade) => (
                <Badge
                  key={grade}
                  variant={filters.grades.includes(grade) ? 'default' : 'outline'}
                  className={`cursor-pointer ${
                    filters.grades.includes(grade) ? MA_GRADE_COLORS[grade] : ''
                  }`}
                  onClick={() => handleGradeToggle(grade)}
                >
                  {grade}
                </Badge>
              ))}
            </div>
          </div>

          {/* 시장 필터 */}
          <div>
            <p className="text-sm font-medium text-zinc-300 mb-2">시장</p>
            <div className="flex flex-wrap gap-2">
              {MARKETS.map((market) => (
                <Badge
                  key={market}
                  variant={filters.markets.includes(market) ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => handleMarketToggle(market)}
                >
                  {market}
                </Badge>
              ))}
            </div>
          </div>

          {/* 수치 필터 (컴팩트 그리드) */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
            {/* 시가총액 범위 */}
            <CompactRangeInput
              label="시가총액"
              minValue={filters.marketCapRange[0]}
              maxValue={filters.marketCapRange[1]}
              min={100}
              max={100000}
              step={100}
              formatValue={(v) => v >= 10000 ? `${(v / 10000).toFixed(1)}조` : `${v.toLocaleString()}억`}
              onChange={(min, max) => {
                setFilters((prev) => ({ ...prev, marketCapRange: [min, max] }));
                setPage(1);
              }}
              tooltip="100억 단위 조절"
            />

            {/* 현금성자산 범위 */}
            <CompactRangeInput
              label="현금성자산"
              minValue={filters.cashAssetsRange[0]}
              maxValue={filters.cashAssetsRange[1]}
              min={0}
              max={50000}
              step={100}
              formatValue={(v) => v >= 10000 ? `${(v / 10000).toFixed(1)}조` : `${v.toLocaleString()}억`}
              onChange={(min, max) => {
                setFilters((prev) => ({ ...prev, cashAssetsRange: [min, max] }));
                setPage(1);
              }}
              tooltip="현금 + 단기금융상품 (100억 단위)"
            />

            {/* 현금/시총 비율 */}
            <CompactRangeInput
              label="현금/시총 비율"
              minValue={filters.cashRatioRange[0]}
              maxValue={filters.cashRatioRange[1]}
              min={0}
              max={100}
              step={10}
              unit="%"
              onChange={(min, max) => {
                setFilters((prev) => ({ ...prev, cashRatioRange: [min, max] }));
                setPage(1);
              }}
              tooltip="현금성 자산 / 시가총액 (10% 단위)"
            />

            {/* 매출 성장률 */}
            <CompactRangeInput
              label="매출 성장률"
              minValue={filters.revenueGrowthRange[0]}
              maxValue={filters.revenueGrowthRange[1]}
              min={-50}
              max={100}
              step={10}
              unit="%"
              onChange={(min, max) => {
                setFilters((prev) => ({ ...prev, revenueGrowthRange: [min, max] }));
                setPage(1);
              }}
              tooltip="YoY 매출 성장률 (10% 단위)"
            />

            {/* 유형자산 증가율 */}
            <CompactRangeInput
              label="유형자산 증가율"
              minValue={filters.tangibleGrowthRange[0]}
              maxValue={filters.tangibleGrowthRange[1]}
              min={-50}
              max={100}
              step={10}
              unit="%"
              onChange={(min, max) => {
                setFilters((prev) => ({ ...prev, tangibleGrowthRange: [min, max] }));
                setPage(1);
              }}
              tooltip="YoY 유형자산 증가율 (10% 단위)"
            />
          </div>
        </CardContent>
      </Card>

      {/* 정렬 및 결과 수 */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-zinc-400">
          총 <span className="font-medium text-white">{formatNumber(data?.total || 0)}</span>개 기업
        </p>
        <Select value={sort} onValueChange={(value) => {
          setSort(value as MATargetParams['sort']);
          setPage(1);
        }}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="정렬 기준" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="score_desc">점수 높은 순</SelectItem>
            <SelectItem value="score_asc">점수 낮은 순</SelectItem>
            <SelectItem value="cash_ratio_desc">현금비율 높은 순</SelectItem>
            <SelectItem value="market_cap_asc">시가총액 낮은 순</SelectItem>
            <SelectItem value="market_cap_desc">시가총액 높은 순</SelectItem>
            <SelectItem value="revenue_growth_desc">매출성장률 높은 순</SelectItem>
            <SelectItem value="tangible_growth_desc">유형자산 증가율 높은 순</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* 결과 테이블 */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 animate-spin text-[#5E6AD2]" />
            </div>
          ) : error ? (
            <div className="text-center py-20 text-zinc-500">
              <p>{error}</p>
            </div>
          ) : data?.items.length === 0 ? (
            <div className="text-center py-20 text-zinc-500">
              <p>조건에 맞는 기업이 없습니다.</p>
              <p className="text-sm mt-2">필터 조건을 조정해 보세요.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12 text-center">#</TableHead>
                  <TableHead>기업명</TableHead>
                  <TableHead className="text-center">등급</TableHead>
                  <TableHead className="text-center">점수</TableHead>
                  <TableHead className="text-right">시가총액</TableHead>
                  <TableHead className="text-right">현금성 자산</TableHead>
                  <TableHead className="text-right">매출 성장률</TableHead>
                  <TableHead className="text-right">유형자산 증가율</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((company, index) => (
                  <TableRow key={company.company_id} className="hover:bg-white/5">
                    <TableCell className="text-center text-zinc-500">
                      {(page - 1) * PAGE_SIZE + index + 1}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/company/${company.company_id}`}
                          className="font-medium text-white hover:text-[#8B95E8]"
                        >
                          {company.name}
                        </Link>
                        {company.market && (
                          <MarketBadge
                            market={company.market}
                            tradingStatus={company.trading_status}
                            size="sm"
                          />
                        )}
                      </div>
                      <p className="text-xs text-zinc-500">{company.stock_code}</p>
                    </TableCell>
                    <TableCell className="text-center">
                      <MAGradeBadge grade={company.ma_target_grade} />
                    </TableCell>
                    <TableCell className="text-center font-medium text-white">
                      {company.ma_target_score?.toFixed(1) || '-'}
                    </TableCell>
                    <TableCell className="text-right text-zinc-300">
                      {formatMarketCap(company.market_cap_calculated)}
                    </TableCell>
                    <TableCell className="text-right text-zinc-300">
                      {formatMarketCap(company.total_liquid_assets)}
                    </TableCell>
                    <TableCell className="text-right">
                      <span className={company.revenue_growth && company.revenue_growth >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {formatPercent(company.revenue_growth)}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className={company.tangible_assets_growth && company.tangible_assets_growth >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {formatPercent(company.tangible_assets_growth)}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handlePageChange(page - 1)}
            disabled={page === 1}
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <span className="text-sm text-zinc-400 px-4">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handlePageChange(page + 1)}
            disabled={page === totalPages}
          >
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      )}

      {/* 점수 계산 기준 설명 */}
      <Card className="mt-8">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <HelpCircle className="w-5 h-5 text-zinc-400" />
            적대적 M&A 점수 계산 기준
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="p-3 bg-zinc-800/50 rounded-lg border border-white/5">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-white">현금/시총 비율</span>
                <Badge variant="outline">25점</Badge>
              </div>
              <p className="text-xs text-zinc-500">현금성 자산이 시가총액 대비 높을수록 고점수</p>
            </div>
            <div className="p-3 bg-zinc-800/50 rounded-lg border border-white/5">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-white">유형자산 증가율</span>
                <Badge variant="outline">20점</Badge>
              </div>
              <p className="text-xs text-zinc-500">YoY 유형자산 성장률 (20% 이상 만점)</p>
            </div>
            <div className="p-3 bg-zinc-800/50 rounded-lg border border-white/5">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-white">매출 증감율</span>
                <Badge variant="outline">20점</Badge>
              </div>
              <p className="text-xs text-zinc-500">YoY 매출 성장률 (20% 이상 만점)</p>
            </div>
            <div className="p-3 bg-zinc-800/50 rounded-lg border border-white/5">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-white">영업이익 증감율</span>
                <Badge variant="outline">20점</Badge>
              </div>
              <p className="text-xs text-zinc-500">YoY 영업이익 성장률 (20% 이상 만점)</p>
            </div>
            <div className="p-3 bg-zinc-800/50 rounded-lg border border-white/5">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-white">시가총액 규모</span>
                <Badge variant="outline">15점</Badge>
              </div>
              <p className="text-xs text-zinc-500">적정 인수 규모 (500억~5000억 만점)</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

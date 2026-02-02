'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useCompany } from '@/hooks/use-company';
import { GradeBadge } from '@/components/grade-badge';
import { ScoreDisplay } from '@/components/score-display';
import { MetricCard } from '@/components/metric-card';
import { SubIndexRadar } from '@/components/sub-index-radar';
import { RiskFlagsPanel } from '@/components/risk-flags-panel';
import { AIAnalysisSection } from '@/components/ai-analysis-section';
import { StockPriceChart } from '@/components/stock-price-chart';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Calendar, Building2, TrendingUp, TrendingDown, Minus, AlertTriangle, Loader2 } from 'lucide-react';
import { GRADE_COLORS, METRIC_DESCRIPTIONS, type Grade } from '@/lib/constants';
import type { RaymondsIndexResponse } from '@/lib/types';

/**
 * 데이터 완전성 체크: Sub-Index가 모두 NULL인지 확인
 * RaymondsIndex 계산에 필요한 다년도 재무 데이터가 부족한 경우 true 반환
 */
function isDataIncomplete(company: RaymondsIndexResponse): boolean {
  return (
    company.cei_score === null &&
    company.rii_score === null &&
    company.cgi_score === null &&
    company.mai_score === null
  );
}

export default function CompanyDetailPage() {
  const params = useParams();
  const companyId = params.id as string;
  const { data: company, isLoading, error } = useCompany(companyId);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 bg-zinc-800 rounded" />
          <div className="h-40 bg-zinc-800/50 rounded-lg" />
          <div className="grid lg:grid-cols-2 gap-6">
            <div className="h-80 bg-zinc-800/50 rounded-lg" />
            <div className="h-80 bg-zinc-800/50 rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !company) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <h2 className="text-xl font-semibold text-white mb-2">
            기업 정보를 불러올 수 없습니다
          </h2>
          <p className="text-zinc-400 mb-4">
            요청하신 기업 정보가 존재하지 않거나 오류가 발생했습니다.
          </p>
          <Button asChild>
            <Link href="/screener">스크리너로 돌아가기</Link>
          </Button>
        </div>
      </div>
    );
  }

  const gradeColors = GRADE_COLORS[company.grade as Grade];
  // capexTrendIcon은 추후 CAPEX 추세 시각화에 사용 예정
  const _capexTrendIcon = company.capex_trend === 'increasing' ? TrendingUp :
                          company.capex_trend === 'decreasing' ? TrendingDown : Minus;
  void _capexTrendIcon; // ESLint 경고 방지 (추후 사용 예정)

  // 데이터 완전성 체크
  const dataIncomplete = isDataIncomplete(company);

  // Determine status for metrics
  const getStatus = (value: number | null, thresholds: { good: number; warning: number }) => {
    if (value === null) return 'neutral';
    if (value >= thresholds.good) return 'good';
    if (value >= thresholds.warning) return 'warning';
    return 'danger';
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Back Button */}
      <Button variant="ghost" size="sm" asChild className="mb-4">
        <Link href="/screener">
          <ArrowLeft className="w-4 h-4 mr-2" />
          뒤로
        </Link>
      </Button>

      {/* Header Section */}
      <Card className="mb-6">
        <CardContent className="py-6">
          <div className="flex flex-col lg:flex-row lg:items-center gap-6">
            {/* Company Info */}
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-2xl font-bold text-white">
                  {company.company_name}
                </h1>
                <Badge variant="outline">{company.stock_code}</Badge>
              </div>
              {company.sector && (
                <div className="flex items-center gap-2 text-zinc-400">
                  <Building2 className="w-4 h-4" />
                  <span>{company.sector}</span>
                </div>
              )}
            </div>

            {/* Score Section */}
            <div
              className="flex items-center gap-6 p-6 rounded-xl"
              style={{ backgroundColor: `${gradeColors?.bg}10` }}
            >
              <GradeBadge grade={company.grade} size="xl" showLabel />
              <div>
                <ScoreDisplay score={company.total_score} size="lg" />
                <p className="text-sm text-zinc-500 mt-1">
                  {getPercentileText(company.total_score)}
                </p>
              </div>
            </div>
          </div>

          {/* Meta Info */}
          <div className="flex flex-wrap gap-4 mt-4 pt-4 border-t border-white/10 text-sm text-zinc-500">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              <span>
                기준일: {company.calculation_date
                  ? new Date(company.calculation_date).toLocaleDateString('ko-KR')
                  : '-'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span>회계연도: {company.fiscal_year}</span>
            </div>
            {company.violation_count > 0 && (
              <Badge variant="destructive">
                특별규칙 위반 {company.violation_count}건
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 데이터 수집 중 안내 배너 */}
      {dataIncomplete && (
        <div className="mb-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 p-2 bg-amber-500/20 rounded-full">
              <Loader2 className="w-5 h-5 text-amber-500 animate-spin" />
            </div>
            <div>
              <h3 className="font-semibold text-amber-500 mb-1 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                세부 지표 수집 중
              </h3>
              <p className="text-sm text-zinc-400">
                이 기업은 아직 다년도 재무 데이터 수집이 완료되지 않아 세부 지표를 계산할 수 없습니다.
                종합 점수와 등급은 참고용이며, 정확한 분석을 위해 데이터 수집 완료 후 다시 확인해 주세요.
              </p>
              <p className="text-xs text-zinc-500 mt-2">
                RaymondsIndex 계산에는 최소 3년 이상의 연간 사업보고서 데이터가 필요합니다.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid lg:grid-cols-2 gap-6 mb-6">
        {/* Sub-Index Radar */}
        <SubIndexRadar
          cei={company.cei_score}
          rii={company.rii_score}
          cgi={company.cgi_score}
          mai={company.mai_score}
          dataIncomplete={dataIncomplete}
        />

        {/* Risk Flags */}
        <RiskFlagsPanel
          redFlags={company.red_flags || []}
          yellowFlags={company.yellow_flags || []}
        />
      </div>

      {/* Stock Price Chart */}
      {company.stock_code && (
        <div className="mb-6">
          <StockPriceChart
            companyId={company.company_id}
            companyName={company.company_name}
            ticker={company.stock_code}
          />
        </div>
      )}

      {/* Core Metrics Grid */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">핵심 지표</h2>
          {dataIncomplete && (
            <span className="text-xs text-amber-500 bg-amber-500/10 px-2 py-1 rounded">
              데이터 수집 중
            </span>
          )}
        </div>
        <div className={`grid sm:grid-cols-2 lg:grid-cols-3 gap-4 ${dataIncomplete ? 'opacity-50' : ''}`}>
          <MetricCard
            label="투자괴리율 (v2.1)"
            value={company.investment_gap_v21?.toFixed(1) ?? company.investment_gap?.toFixed(1)}
            unit="%p"
            status={getStatus(
              company.investment_gap_v21 ?? company.investment_gap,
              { good: 0, warning: 20 }
            )}
            description="현금 CAGR - CAPEX 성장률"
            tooltip={METRIC_DESCRIPTIONS.investment_gap.description}
            dataFlag={company.investment_gap_v21_flag}
          />
          <MetricCard
            label="재투자율"
            value={company.reinvestment_rate?.toFixed(1)}
            unit="%"
            status={getStatus(company.reinvestment_rate, { good: 30, warning: 15 })}
            description="영업현금흐름 대비 CAPEX 비율"
            tooltip={METRIC_DESCRIPTIONS.reinvestment_rate.description}
          />
          <MetricCard
            label="ROIC"
            value={company.roic?.toFixed(1)}
            unit="%"
            status={getStatus(company.roic, { good: 10, warning: 5 })}
            description="투하자본수익률"
            tooltip={METRIC_DESCRIPTIONS.roic.description}
          />
          <MetricCard
            label="현금/유형자산 비율"
            value={company.cash_tangible_ratio?.toFixed(1)}
            unit=":1"
            status={
              company.cash_tangible_ratio && company.cash_tangible_ratio > 30
                ? 'danger'
                : company.cash_tangible_ratio && company.cash_tangible_ratio > 10
                ? 'warning'
                : 'good'
            }
            description="현금 대비 유형자산 증가율 비율"
            tooltip={METRIC_DESCRIPTIONS.cash_tangible_ratio.description}
          />
          <MetricCard
            label="단기금융비율"
            value={company.short_term_ratio?.toFixed(1)}
            unit="%"
            status={
              company.short_term_ratio && company.short_term_ratio > 65
                ? 'danger'
                : company.short_term_ratio && company.short_term_ratio > 40
                ? 'warning'
                : 'good'
            }
            description="현금 중 단기금융상품 비율"
            tooltip={METRIC_DESCRIPTIONS.short_term_ratio.description}
          />
          <MetricCard
            label="주주환원율"
            value={company.shareholder_return?.toFixed(1)}
            unit="%"
            status={getStatus(company.shareholder_return, { good: 30, warning: 10 })}
            description="배당 및 자사주 매입 비율"
            tooltip={METRIC_DESCRIPTIONS.shareholder_return.description}
          />
        </div>
      </div>

      {/* Additional Metrics */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">추가 지표</h2>
          {dataIncomplete && (
            <span className="text-xs text-amber-500 bg-amber-500/10 px-2 py-1 rounded">
              데이터 수집 중
            </span>
          )}
        </div>
        <div className={`grid sm:grid-cols-2 lg:grid-cols-4 gap-4 ${dataIncomplete ? 'opacity-50' : ''}`}>
          <MetricCard
            label="유휴현금비율"
            value={company.idle_cash_ratio?.toFixed(1)}
            unit="%"
            status={
              company.idle_cash_ratio && company.idle_cash_ratio > 50
                ? 'warning'
                : 'neutral'
            }
            tooltip={METRIC_DESCRIPTIONS.idle_cash_ratio.description}
          />
          <MetricCard
            label="조달자금 전환율"
            value={company.fundraising_utilization?.toFixed(1)}
            unit="%"
            status={getStatus(company.fundraising_utilization, { good: 50, warning: 30 })}
            tooltip={METRIC_DESCRIPTIONS.fundraising_utilization.description}
          />
          <MetricCard
            label="CAPEX 변동계수"
            value={company.capex_cv?.toFixed(2)}
            status={
              company.capex_cv && company.capex_cv > 1
                ? 'warning'
                : 'good'
            }
            description="투자 지속성 (낮을수록 안정)"
            tooltip={METRIC_DESCRIPTIONS.capex_cv.description}
          />
          <MetricCard
            label="CAPEX 추세"
            value={
              company.capex_trend === 'increasing' ? '증가' :
              company.capex_trend === 'decreasing' ? '감소' : '유지'
            }
            status={
              company.capex_trend === 'increasing' ? 'good' :
              company.capex_trend === 'decreasing' ? 'warning' : 'neutral'
            }
            tooltip={METRIC_DESCRIPTIONS.capex_trend.description}
          />
        </div>
      </div>

      {/* AI Analysis */}
      <AIAnalysisSection
        verdict={company.verdict}
        keyRisk={company.key_risk}
        recommendation={company.recommendation}
        watchTrigger={company.watch_trigger}
      />
    </div>
  );
}

function getPercentileText(score: number): string {
  if (score >= 95) return '상위 0.1%';
  if (score >= 90) return '상위 0.5%';
  if (score >= 85) return '상위 2%';
  if (score >= 80) return '상위 5%';
  if (score >= 70) return '상위 15%';
  if (score >= 60) return '상위 40%';
  if (score >= 50) return '평균 이하';
  if (score >= 40) return '하위 25%';
  return '하위 10%';
}

'use client';

import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GradeBadge } from '@/components/grade-badge';
import { MarketBadge } from '@/components/market-badge';
import { useCompareStore } from '@/lib/compare-store';
import Link from 'next/link';

// 지표 행 컴포넌트
function MetricRow({
  label,
  values,
  format = 'number',
  highlight = 'high',
}: {
  label: string;
  values: (number | null | undefined)[];
  format?: 'number' | 'percent' | 'score';
  highlight?: 'high' | 'low' | 'none';
}) {
  const validValues = values.filter((v) => v !== null && v !== undefined) as number[];
  // 빈 배열 안전 처리: Math.max/min에 빈 배열 전달 시 -Infinity/Infinity 반환 방지
  const bestValue =
    validValues.length === 0
      ? null
      : highlight === 'high'
        ? Math.max(...validValues)
        : highlight === 'low'
          ? Math.min(...validValues)
          : null;

  const formatValue = (v: number | null | undefined) => {
    if (v === null || v === undefined) return '-';
    switch (format) {
      case 'percent':
        return `${v.toFixed(1)}%`;
      case 'score':
        return v.toFixed(1);
      default:
        return v.toLocaleString();
    }
  };

  return (
    <tr className="border-b last:border-b-0">
      <td className="py-3 px-4 text-sm font-medium text-gray-700 bg-gray-50">
        {label}
      </td>
      {values.map((value, idx) => {
        const isBest = highlight !== 'none' && value === bestValue && validValues.length > 1;
        return (
          <td
            key={idx}
            className={`py-3 px-4 text-sm text-center ${
              isBest ? 'text-blue-600 font-semibold bg-blue-50' : ''
            }`}
          >
            {formatValue(value)}
          </td>
        );
      })}
    </tr>
  );
}

export function CompareModal() {
  const { items, isOpen, closeModal, clearAll } = useCompareStore();

  if (!isOpen || items.length < 2) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 배경 오버레이 */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={closeModal}
      />

      {/* 모달 콘텐츠 */}
      <div className="relative bg-white rounded-xl shadow-xl max-w-5xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* 헤더 */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-xl font-bold">기업 비교</h2>
          <Button variant="ghost" size="icon" onClick={closeModal}>
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* 비교 테이블 */}
        <div className="overflow-auto flex-1 p-6">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="py-3 px-4 text-left text-sm font-semibold text-gray-500 bg-gray-50 w-32">
                  지표
                </th>
                {items.map((item) => (
                  <th key={item.company_id} className="py-3 px-4 text-center">
                    <div className="flex flex-col items-center gap-1">
                      <Link
                        href={`/company/${item.company_id}`}
                        className="font-semibold text-blue-600 hover:underline"
                        onClick={closeModal}
                      >
                        {item.company_name}
                      </Link>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500">{item.stock_code}</span>
                        {item.market && (
                          <MarketBadge
                            market={item.market}
                            tradingStatus={item.trading_status}
                            size="sm"
                          />
                        )}
                      </div>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* 등급 */}
              <tr className="border-b">
                <td className="py-3 px-4 text-sm font-medium text-gray-700 bg-gray-50">
                  등급
                </td>
                {items.map((item) => (
                  <td key={item.company_id} className="py-3 px-4 text-center">
                    <div className="flex justify-center">
                      <GradeBadge grade={item.grade} />
                    </div>
                  </td>
                ))}
              </tr>

              {/* 종합 점수 */}
              <MetricRow
                label="종합 점수"
                values={items.map((i) => i.total_score)}
                format="score"
                highlight="high"
              />

              {/* Sub-Index */}
              <tr className="bg-gray-100">
                <td colSpan={items.length + 1} className="py-2 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Sub-Index
                </td>
              </tr>
              <MetricRow
                label="CEI (자본효율)"
                values={items.map((i) => i.cei_score)}
                format="score"
                highlight="high"
              />
              <MetricRow
                label="RII (재투자)"
                values={items.map((i) => i.rii_score)}
                format="score"
                highlight="high"
              />
              <MetricRow
                label="CGI (현금거버넌스)"
                values={items.map((i) => i.cgi_score)}
                format="score"
                highlight="high"
              />
              <MetricRow
                label="MAI (시장정렬)"
                values={items.map((i) => i.mai_score)}
                format="score"
                highlight="high"
              />

              {/* 핵심 지표 */}
              <tr className="bg-gray-100">
                <td colSpan={items.length + 1} className="py-2 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  핵심 지표
                </td>
              </tr>
              <MetricRow
                label="투자괴리율"
                values={items.map((i) => i.investment_gap)}
                format="percent"
                highlight="none"
              />
              <MetricRow
                label="ROIC"
                values={items.map((i) => i.roic)}
                format="percent"
                highlight="high"
              />
              <MetricRow
                label="재투자율"
                values={items.map((i) => i.reinvestment_rate)}
                format="percent"
                highlight="high"
              />
              <MetricRow
                label="현금 CAGR"
                values={items.map((i) => i.cash_cagr)}
                format="percent"
                highlight="high"
              />
              <MetricRow
                label="CAPEX 성장률"
                values={items.map((i) => i.capex_growth)}
                format="percent"
                highlight="high"
              />
              <MetricRow
                label="유휴현금비율"
                values={items.map((i) => i.idle_cash_ratio)}
                format="percent"
                highlight="low"
              />

              {/* 위험신호 */}
              <tr className="bg-gray-100">
                <td colSpan={items.length + 1} className="py-2 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  위험 신호
                </td>
              </tr>
              <tr className="border-b">
                <td className="py-3 px-4 text-sm font-medium text-gray-700 bg-gray-50">
                  Red Flags
                </td>
                {items.map((item) => (
                  <td key={item.company_id} className="py-3 px-4 text-center">
                    {item.red_flags.length > 0 ? (
                      <div className="space-y-1">
                        {item.red_flags.map((flag, idx) => (
                          <span
                            key={idx}
                            className="inline-block px-2 py-0.5 text-xs bg-red-100 text-red-700 rounded"
                          >
                            {flag}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-green-600 text-sm">없음</span>
                    )}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>

        {/* 푸터 */}
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t bg-gray-50">
          <Button variant="outline" onClick={clearAll}>
            초기화
          </Button>
          <Button onClick={closeModal}>닫기</Button>
        </div>
      </div>
    </div>
  );
}

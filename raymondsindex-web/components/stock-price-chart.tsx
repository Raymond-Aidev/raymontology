'use client';

import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Area,
  ComposedChart,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Minus, LineChartIcon, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import type { StockPriceChartResponse, StockPriceData } from '@/lib/types';

interface StockPriceChartProps {
  companyId: string;
  companyName?: string;
  ticker?: string;
}

type PeriodType = '1y' | '2y' | '3y' | 'all';

// 기간 옵션
const PERIOD_OPTIONS: { value: PeriodType; label: string }[] = [
  { value: '1y', label: '1년' },
  { value: '2y', label: '2년' },
  { value: '3y', label: '3년' },
  { value: 'all', label: '전체' },
];

// 숫자 포맷 (원 단위)
function formatPrice(value: number): string {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}백만`;
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(0)}천`;
  }
  return value.toLocaleString();
}

// 수익률 배지 컴포넌트
function ReturnBadge({ returnPct }: { returnPct: number }) {
  const isPositive = returnPct > 0;
  const isNegative = returnPct < 0;
  const Icon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus;
  const colorClass = isPositive
    ? 'text-green-600 bg-green-50'
    : isNegative
    ? 'text-red-600 bg-red-50'
    : 'text-gray-600 bg-gray-50';

  return (
    <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium ${colorClass}`}>
      <Icon className="w-4 h-4" />
      <span>{isPositive ? '+' : ''}{returnPct.toFixed(2)}%</span>
    </div>
  );
}

// 커스텀 툴팁
function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ value: number; payload: StockPriceData }>;
  label?: string;
}) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-semibold text-gray-900 mb-2">{label}</p>
      <div className="space-y-1">
        <div className="flex justify-between gap-4">
          <span className="text-gray-500">종가</span>
          <span className="font-medium">{data.close?.toLocaleString()}원</span>
        </div>
        {data.open && (
          <div className="flex justify-between gap-4">
            <span className="text-gray-500">시가</span>
            <span>{data.open.toLocaleString()}원</span>
          </div>
        )}
        {data.high && data.low && (
          <div className="flex justify-between gap-4">
            <span className="text-gray-500">고가/저가</span>
            <span>{data.high.toLocaleString()} / {data.low.toLocaleString()}</span>
          </div>
        )}
        {data.change !== null && (
          <div className="flex justify-between gap-4">
            <span className="text-gray-500">전월비</span>
            <span className={data.change > 0 ? 'text-green-600' : data.change < 0 ? 'text-red-600' : ''}>
              {data.change > 0 ? '+' : ''}{data.change.toFixed(2)}%
            </span>
          </div>
        )}
        {data.volume && (
          <div className="flex justify-between gap-4">
            <span className="text-gray-500">거래량</span>
            <span>{data.volume.toLocaleString()}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export function StockPriceChart({ companyId, companyName, ticker }: StockPriceChartProps) {
  const [period, setPeriod] = useState<PeriodType>('3y');
  const [data, setData] = useState<StockPriceChartResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);

      try {
        const response = await api.stockPrices.getChartData(companyId, period);
        setData(response);
      } catch (err) {
        console.error('주가 데이터 조회 실패:', err);
        setError('주가 데이터를 불러올 수 없습니다');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [companyId, period]);

  // 로딩 상태
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LineChartIcon className="w-5 h-5 text-blue-500" />
            월별 주가 추이
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-gray-400 animate-spin" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // 에러 또는 데이터 없음
  if (error || !data || !data.data || data.data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LineChartIcon className="w-5 h-5 text-blue-500" />
            월별 주가 추이
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-gray-500">
            {error || data?.message || '주가 데이터가 없습니다'}
          </div>
        </CardContent>
      </Card>
    );
  }

  const { performance } = data;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <LineChartIcon className="w-5 h-5 text-blue-500" />
            월별 주가 추이
            {ticker && <span className="text-sm font-normal text-gray-500">({ticker})</span>}
          </CardTitle>

          {/* 기간 선택 버튼 */}
          <div className="flex gap-1">
            {PERIOD_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => setPeriod(option.value)}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  period === option.value
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* 성과 요약 */}
        <div className="flex items-center justify-between mb-4 p-3 bg-gray-50 rounded-lg">
          <div>
            <p className="text-sm text-gray-500">
              {performance.start_month} ~ {performance.end_month}
            </p>
            <p className="text-lg font-semibold">
              {performance.start_price?.toLocaleString()}원 → {performance.end_price?.toLocaleString()}원
            </p>
          </div>
          <ReturnBadge returnPct={performance.total_return_pct} />
        </div>

        {/* 차트 */}
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={data.data}
              margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="month"
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: '#e5e7eb' }}
                interval="preserveStartEnd"
                tickFormatter={(value) => {
                  // 연도가 바뀔 때만 연도 표시
                  const [year, month] = value.split('-');
                  return month === '01' ? `${year}` : `${parseInt(month)}월`;
                }}
              />
              <YAxis
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={formatPrice}
                domain={['auto', 'auto']}
                width={60}
              />
              <RechartsTooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="close"
                stroke="transparent"
                fill="url(#colorClose)"
              />
              <Line
                type="monotone"
                dataKey="close"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 6, fill: '#3b82f6', stroke: 'white', strokeWidth: 2 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* 데이터 포인트 수 */}
        <p className="text-xs text-gray-400 text-right mt-2">
          데이터: {performance.data_points}개월
        </p>
      </CardContent>
    </Card>
  );
}

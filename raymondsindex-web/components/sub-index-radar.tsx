'use client';

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart3, HelpCircle } from 'lucide-react';
import { SUB_INDEX_INFO } from '@/lib/constants';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface SubIndexRadarProps {
  cei: number | null;
  rii: number | null;
  cgi: number | null;
  mai: number | null;
  dataIncomplete?: boolean;
}

// Sub-Index 항목 컴포넌트
function SubIndexItem({
  code,
  value,
  highlighted = false,
}: {
  code: 'CEI' | 'RII' | 'CGI' | 'MAI';
  value: number | null;
  highlighted?: boolean;
}) {
  const info = SUB_INDEX_INFO[code];
  const bgClass = highlighted ? 'bg-blue-50' : 'bg-gray-50';
  const codeClass = highlighted ? 'text-blue-500' : 'text-gray-500';
  const valueClass = highlighted ? 'text-blue-700' : 'text-gray-900';
  const labelClass = highlighted ? 'text-blue-400' : 'text-gray-400';

  return (
    <div className={`text-center p-2 ${bgClass} rounded`}>
      <div className="flex items-center justify-center gap-1">
        <p className={`text-xs ${codeClass}`}>{code}</p>
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                className="text-gray-400 hover:text-gray-600 focus:outline-none"
                aria-label={`${code} 설명`}
              >
                <HelpCircle className="w-3 h-3" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-xs">
              <p className="text-sm font-medium mb-1">{info.label} ({info.weight}%)</p>
              <p className="text-sm text-gray-600">{info.description}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      <p className={`font-semibold ${valueClass}`}>{value?.toFixed(1) || '-'}</p>
      <p className={`text-xs ${labelClass}`}>{info.label}</p>
    </div>
  );
}

export function SubIndexRadar({ cei, rii, cgi, mai, dataIncomplete = false }: SubIndexRadarProps) {
  // v3.1: 핵심 3개 Sub-Index (CEI 45%, CGI 45%, RII 10%)
  // MAI는 가중치 0%이므로 레이더 차트에서 제외, 참고용으로만 표시
  const data = [
    {
      subject: `CEI (${SUB_INDEX_INFO.CEI.weight}%)`,
      value: cei || 0,
      fullMark: 100,
    },
    {
      subject: `RII (${SUB_INDEX_INFO.RII.weight}%)`,
      value: rii || 0,
      fullMark: 100,
    },
    {
      subject: `CGI (${SUB_INDEX_INFO.CGI.weight}%)`,
      value: cgi || 0,
      fullMark: 100,
    },
  ];

  // 데이터 부족 시 안내 메시지 표시
  if (dataIncomplete) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-500" />
            Sub-Index 분석
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center">
            <div className="text-center p-6">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-500/10 flex items-center justify-center">
                <BarChart3 className="w-8 h-8 text-amber-500/50" />
              </div>
              <p className="text-zinc-400 mb-2">데이터 수집 중</p>
              <p className="text-xs text-zinc-500 max-w-[200px]">
                Sub-Index 계산에 필요한 다년도 재무 데이터를 수집하고 있습니다.
              </p>
            </div>
          </div>

          {/* Sub-Index Legend - 데이터 부족 상태 */}
          <div className="grid grid-cols-2 gap-3 mt-4 opacity-50">
            <SubIndexItem code="CEI" value={null} highlighted />
            <SubIndexItem code="CGI" value={null} highlighted />
            <SubIndexItem code="RII" value={null} />
            <div className="text-center p-2 bg-gray-100 rounded opacity-60">
              <p className="text-xs text-gray-400">MAI</p>
              <p className="font-semibold text-gray-500">-</p>
              <p className="text-xs text-gray-400">{SUB_INDEX_INFO.MAI.label}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-blue-500" />
          Sub-Index 분석
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={data} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
              <PolarGrid stroke="#e5e7eb" />
              <PolarAngleAxis
                dataKey="subject"
                tick={{ fill: '#374151', fontSize: 12 }}
              />
              <PolarRadiusAxis
                angle={90}
                domain={[0, 100]}
                tick={{ fill: '#9ca3af', fontSize: 10 }}
              />
              <Radar
                name="점수"
                dataKey="value"
                stroke="#2563eb"
                fill="#3b82f6"
                fillOpacity={0.3}
                strokeWidth={2}
              />
              <RechartsTooltip
                formatter={(value) => [`${Number(value).toFixed(1)}점`, '점수']}
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Sub-Index Legend with Tooltips */}
        {/* v3.1: CEI, CGI 핵심 지표로 강조 */}
        <div className="grid grid-cols-2 gap-3 mt-4">
          <SubIndexItem code="CEI" value={cei} highlighted />
          <SubIndexItem code="CGI" value={cgi} highlighted />
          <SubIndexItem code="RII" value={rii} />
          {/* MAI: 참고용 (가중치 0%) */}
          <div className="text-center p-2 bg-gray-100 rounded opacity-60">
            <div className="flex items-center justify-center gap-1">
              <p className="text-xs text-gray-400">MAI</p>
              <TooltipProvider delayDuration={0}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button className="text-gray-300 hover:text-gray-500 focus:outline-none">
                      <HelpCircle className="w-3 h-3" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
                    <p className="text-sm font-medium mb-1">{SUB_INDEX_INFO.MAI.label} (참고용)</p>
                    <p className="text-sm text-gray-600">{SUB_INDEX_INFO.MAI.description}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <p className="font-semibold text-gray-500">{mai?.toFixed(1) || '-'}</p>
            <p className="text-xs text-gray-400">{SUB_INDEX_INFO.MAI.label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

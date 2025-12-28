'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, XCircle, CheckCircle2, ShieldCheck } from 'lucide-react';

interface RiskFlagsPanelProps {
  redFlags: string[];
  yellowFlags: string[];
  positiveSignals?: string[];
}

// 상태별 설명
const STATUS_DESCRIPTIONS = {
  redFlags: '투자금 배분에 심각한 문제가 발견되었습니다. 투자 전 반드시 추가 조사가 필요합니다.',
  yellowFlags: '투자금 배분에 주의가 필요한 신호입니다. 향후 추이를 관찰하시기 바랍니다.',
  allClear: {
    title: '정상 상태',
    description: '현재 위험 신호가 감지되지 않았습니다. 자본 배분 효율성이 양호한 상태입니다.',
  },
};

export function RiskFlagsPanel({
  redFlags,
  yellowFlags,
  positiveSignals = [],
}: RiskFlagsPanelProps) {
  const hasAnyFlags = redFlags.length > 0 || yellowFlags.length > 0;

  // 모든 플래그가 없는 경우 정상 상태 표시
  if (!hasAnyFlags) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-green-500" />
            위험 신호 분석
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-5 h-5 text-green-600" />
              <span className="font-medium text-green-700">
                {STATUS_DESCRIPTIONS.allClear.title}
              </span>
            </div>
            <p className="text-sm text-green-600 ml-7">
              {STATUS_DESCRIPTIONS.allClear.description}
            </p>
          </div>

          {/* 긍정 신호가 있으면 표시 */}
          {positiveSignals.length > 0 && (
            <div className="mt-4">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 className="w-4 h-4 text-green-500" />
                <span className="font-medium text-green-700">긍정 신호</span>
              </div>
              <ul className="space-y-1 ml-6">
                {positiveSignals.map((signal, index) => (
                  <li
                    key={index}
                    className="text-sm text-gray-700 before:content-['•'] before:mr-2 before:text-green-500"
                  >
                    {signal}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-yellow-500" />
          위험 신호 분석
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Red Flags */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <XCircle className="w-4 h-4 text-red-500" />
            <span className="font-medium text-red-700">Red Flags (심각)</span>
          </div>
          {redFlags.length > 0 ? (
            <>
              <p className="text-xs text-red-600 ml-6 mb-2">
                {STATUS_DESCRIPTIONS.redFlags}
              </p>
              <ul className="space-y-1 ml-6">
                {redFlags.map((flag, index) => (
                  <li
                    key={index}
                    className="text-sm text-gray-700 before:content-['•'] before:mr-2 before:text-red-500"
                  >
                    {flag}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-sm text-gray-500 ml-6">(없음)</p>
          )}
        </div>

        {/* Yellow Flags */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-yellow-500" />
            <span className="font-medium text-yellow-700">Yellow Flags (주의)</span>
          </div>
          {yellowFlags.length > 0 ? (
            <>
              <p className="text-xs text-yellow-600 ml-6 mb-2">
                {STATUS_DESCRIPTIONS.yellowFlags}
              </p>
              <ul className="space-y-1 ml-6">
                {yellowFlags.map((flag, index) => (
                  <li
                    key={index}
                    className="text-sm text-gray-700 before:content-['•'] before:mr-2 before:text-yellow-500"
                  >
                    {flag}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-sm text-gray-500 ml-6">(없음)</p>
          )}
        </div>

        {/* Positive Signals */}
        {positiveSignals.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <span className="font-medium text-green-700">긍정 신호</span>
            </div>
            <ul className="space-y-1 ml-6">
              {positiveSignals.map((signal, index) => (
                <li
                  key={index}
                  className="text-sm text-gray-700 before:content-['•'] before:mr-2 before:text-green-500"
                >
                  {signal}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, XCircle, CheckCircle2 } from 'lucide-react';

interface RiskFlagsPanelProps {
  redFlags: string[];
  yellowFlags: string[];
  positiveSignals?: string[];
}

export function RiskFlagsPanel({
  redFlags,
  yellowFlags,
  positiveSignals = [],
}: RiskFlagsPanelProps) {
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

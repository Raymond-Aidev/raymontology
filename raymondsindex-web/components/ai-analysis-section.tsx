'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Bot, Lightbulb, AlertCircle, ClipboardList } from 'lucide-react';

interface AIAnalysisSectionProps {
  verdict: string | null;
  keyRisk: string | null;
  recommendation: string | null;
  watchTrigger?: string | null;
}

export function AIAnalysisSection({
  verdict,
  keyRisk,
  recommendation,
  watchTrigger,
}: AIAnalysisSectionProps) {
  if (!verdict && !keyRisk && !recommendation) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-purple-500" />
          AI 분석 요약
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Verdict */}
        {verdict && (
          <div className="p-4 bg-purple-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Lightbulb className="w-4 h-4 text-purple-600" />
              <span className="font-medium text-purple-800">핵심 판단</span>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">{verdict}</p>
          </div>
        )}

        {/* Key Risk */}
        {keyRisk && (
          <div className="p-4 bg-yellow-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="w-4 h-4 text-yellow-600" />
              <span className="font-medium text-yellow-800">주요 리스크</span>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">{keyRisk}</p>
          </div>
        )}

        {/* Recommendation */}
        {recommendation && (
          <div className="p-4 bg-blue-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <ClipboardList className="w-4 h-4 text-blue-600" />
              <span className="font-medium text-blue-800">투자자 권고</span>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">{recommendation}</p>
          </div>
        )}

        {/* Watch Trigger */}
        {watchTrigger && (
          <div className="p-3 bg-gray-100 rounded-lg">
            <p className="text-xs text-gray-600">
              <strong>모니터링 포인트:</strong> {watchTrigger}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

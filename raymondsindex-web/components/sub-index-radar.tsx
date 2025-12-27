'use client';

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart3 } from 'lucide-react';
import { SUB_INDEX_INFO } from '@/lib/constants';

interface SubIndexRadarProps {
  cei: number | null;
  rii: number | null;
  cgi: number | null;
  mai: number | null;
}

export function SubIndexRadar({ cei, rii, cgi, mai }: SubIndexRadarProps) {
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
    {
      subject: `MAI (${SUB_INDEX_INFO.MAI.weight}%)`,
      value: mai || 0,
      fullMark: 100,
    },
  ];

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
              <Tooltip
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

        {/* Sub-Index Legend */}
        <div className="grid grid-cols-2 gap-3 mt-4">
          <div className="text-center p-2 bg-gray-50 rounded">
            <p className="text-xs text-gray-500">CEI</p>
            <p className="font-semibold">{cei?.toFixed(1) || '-'}</p>
            <p className="text-xs text-gray-400">{SUB_INDEX_INFO.CEI.label}</p>
          </div>
          <div className="text-center p-2 bg-blue-50 rounded">
            <p className="text-xs text-blue-500">RII</p>
            <p className="font-semibold text-blue-700">{rii?.toFixed(1) || '-'}</p>
            <p className="text-xs text-blue-400">{SUB_INDEX_INFO.RII.label}</p>
          </div>
          <div className="text-center p-2 bg-gray-50 rounded">
            <p className="text-xs text-gray-500">CGI</p>
            <p className="font-semibold">{cgi?.toFixed(1) || '-'}</p>
            <p className="text-xs text-gray-400">{SUB_INDEX_INFO.CGI.label}</p>
          </div>
          <div className="text-center p-2 bg-gray-50 rounded">
            <p className="text-xs text-gray-500">MAI</p>
            <p className="font-semibold">{mai?.toFixed(1) || '-'}</p>
            <p className="text-xs text-gray-400">{SUB_INDEX_INFO.MAI.label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

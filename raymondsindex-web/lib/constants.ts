// RaymondsIndex 등급 색상 및 상수 정의

export const GRADE_COLORS = {
  'A++': { bg: '#1E40AF', text: 'white', label: '최고 효율' },
  'A+': { bg: '#2563EB', text: 'white', label: '매우 우수' },
  'A': { bg: '#3B82F6', text: 'white', label: '우수' },
  'A-': { bg: '#60A5FA', text: 'white', label: '양호' },
  'B+': { bg: '#22C55E', text: 'white', label: '평균 이상' },
  'B': { bg: '#84CC16', text: 'white', label: '평균' },
  'B-': { bg: '#EAB308', text: 'black', label: '평균 이하' },
  'C+': { bg: '#F97316', text: 'white', label: '주의 필요' },
  'C': { bg: '#EF4444', text: 'white', label: '심각한 문제' },
} as const;

export type Grade = keyof typeof GRADE_COLORS;

export const GRADE_ORDER: Grade[] = ['A++', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C'];

export const SUB_INDEX_INFO = {
  CEI: { name: 'Capital Efficiency Index', label: '자본 효율성', weight: 15 },
  RII: { name: 'Reinvestment Intensity Index', label: '재투자 강도', weight: 40 },
  CGI: { name: 'Cash Governance Index', label: '현금 거버넌스', weight: 30 },
  MAI: { name: 'Momentum Alignment Index', label: '모멘텀 정합성', weight: 15 },
} as const;

export const STATUS_COLORS = {
  good: { bg: 'bg-green-100', text: 'text-green-700', icon: 'text-green-500' },
  warning: { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: 'text-yellow-500' },
  danger: { bg: 'bg-red-100', text: 'text-red-700', icon: 'text-red-500' },
  neutral: { bg: 'bg-gray-100', text: 'text-gray-700', icon: 'text-gray-500' },
} as const;

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://raymontology-production.up.railway.app/api';

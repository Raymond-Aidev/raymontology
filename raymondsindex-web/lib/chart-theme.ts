/**
 * 차트 테마 유틸리티
 *
 * Recharts 등 차트 라이브러리에서 CSS 변수를 직접 사용할 수 없으므로,
 * JavaScript에서 CSS 변수 값을 읽어서 전달합니다.
 *
 * 다크모드 지원 시 이 유틸리티를 사용하세요.
 */

// 기본 차트 색상 (라이트 테마)
export const CHART_COLORS = {
  light: {
    primary: '#3b82f6',      // blue-500
    secondary: '#22c55e',    // green-500
    tertiary: '#f59e0b',     // amber-500
    grid: '#e5e7eb',         // gray-200
    axis: '#6b7280',         // gray-500
    text: '#374151',         // gray-700
    background: '#ffffff',
    tooltip: {
      bg: '#ffffff',
      border: '#e5e7eb',
      text: '#1f2937',
    },
  },
  dark: {
    primary: '#60a5fa',      // blue-400
    secondary: '#4ade80',    // green-400
    tertiary: '#fbbf24',     // amber-400
    grid: '#374151',         // gray-700
    axis: '#9ca3af',         // gray-400
    text: '#e5e7eb',         // gray-200
    background: '#1f2937',   // gray-800
    tooltip: {
      bg: '#1f2937',
      border: '#374151',
      text: '#f3f4f6',
    },
  },
} as const;

// 등급별 색상 (테마 독립적 - 브랜드 색상)
export const GRADE_CHART_COLORS = {
  'A++': '#1E40AF',  // blue-800
  'A+': '#2563EB',   // blue-600
  'A': '#3B82F6',    // blue-500
  'A-': '#60A5FA',   // blue-400
  'B+': '#22C55E',   // green-500
  'B': '#84CC16',    // lime-500
  'B-': '#EAB308',   // yellow-500
  'C+': '#F97316',   // orange-500
  'C': '#EF4444',    // red-500
} as const;

// 시장별 색상 (테마 독립적 - 브랜드 색상)
export const MARKET_CHART_COLORS = {
  KOSPI: '#3B82F6',   // blue-500
  KOSDAQ: '#22C55E',  // green-500
  KONEX: '#6B7280',   // gray-500
  ETF: '#8B5CF6',     // violet-500
} as const;

/**
 * 현재 테마에 맞는 차트 색상 반환
 */
export function getChartColors(isDark = false) {
  return isDark ? CHART_COLORS.dark : CHART_COLORS.light;
}

/**
 * CSS 변수에서 색상 값 읽기
 * @param varName CSS 변수 이름 (--로 시작)
 * @param fallback 폴백 색상
 */
export function getCssVariable(varName: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback;

  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(varName)
    .trim();

  return value || fallback;
}

/**
 * 현재 테마가 다크인지 확인
 */
export function isDarkTheme(): boolean {
  if (typeof window === 'undefined') return false;
  return document.documentElement.classList.contains('dark');
}

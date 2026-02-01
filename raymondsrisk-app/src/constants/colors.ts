/**
 * 토스 디자인 시스템 색상
 * 모든 페이지에서 공통으로 사용
 */
export const colors = {
  // Gray Scale
  gray900: '#191f28',
  gray600: '#6b7684',
  gray500: '#8b95a1',
  gray400: '#a0aab4',  // 추가: 블러 처리용
  gray300: '#c4c9cf',  // 추가: 블러 처리용
  gray200: '#dde0e4',  // 추가: 블러 처리용
  gray100: '#f2f4f6',
  gray50: '#f7f8fa',
  white: '#ffffff',

  // Primary
  blue500: '#3182f6',
  blue600: '#1b64da',

  // Semantic
  red500: '#E74C3C',
  green500: '#10B981',
  yellow500: '#F59E0B',
  orange500: '#F97316',  // MEDIUM_RISK 등급용
} as const

export type ColorKey = keyof typeof colors

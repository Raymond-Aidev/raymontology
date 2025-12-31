/**
 * 토스 디자인 시스템 색상
 * 모든 페이지에서 공통으로 사용
 */
export const colors = {
  // Gray Scale
  gray900: '#191f28',
  gray600: '#6b7684',
  gray500: '#8b95a1',
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
} as const

export type ColorKey = keyof typeof colors

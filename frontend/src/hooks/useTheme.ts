import { useState, useEffect, useCallback } from 'react'

type Theme = 'light' | 'dark' | 'system'

// 시스템 테마 감지
function getSystemTheme(): 'light' | 'dark' {
  if (typeof window !== 'undefined' && window.matchMedia) {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return 'dark' // 기본값
}

// 저장된 테마 가져오기
function getSavedTheme(): Theme {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('theme') as Theme | null
    if (saved && ['light', 'dark', 'system'].includes(saved)) {
      return saved
    }
  }
  return 'system' // 기본값: 시스템 설정 따르기
}

// 실제 적용될 테마 계산
function getEffectiveTheme(theme: Theme): 'light' | 'dark' {
  if (theme === 'system') {
    return getSystemTheme()
  }
  return theme
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => getSavedTheme())
  const [effectiveTheme, setEffectiveTheme] = useState<'light' | 'dark'>(() =>
    getEffectiveTheme(getSavedTheme())
  )

  // 테마 변경 함수
  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme)
    localStorage.setItem('theme', newTheme)

    const effective = getEffectiveTheme(newTheme)
    setEffectiveTheme(effective)

    // HTML 클래스 업데이트
    if (effective === 'dark') {
      document.documentElement.classList.add('dark')
      document.documentElement.classList.remove('light')
    } else {
      document.documentElement.classList.add('light')
      document.documentElement.classList.remove('dark')
    }
  }, [])

  // 시스템 테마 변경 감지
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    const handleChange = () => {
      if (theme === 'system') {
        const effective = getSystemTheme()
        setEffectiveTheme(effective)

        if (effective === 'dark') {
          document.documentElement.classList.add('dark')
          document.documentElement.classList.remove('light')
        } else {
          document.documentElement.classList.add('light')
          document.documentElement.classList.remove('dark')
        }
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme])

  // 초기 테마 적용
  useEffect(() => {
    const effective = getEffectiveTheme(theme)
    setEffectiveTheme(effective)

    if (effective === 'dark') {
      document.documentElement.classList.add('dark')
      document.documentElement.classList.remove('light')
    } else {
      document.documentElement.classList.add('light')
      document.documentElement.classList.remove('dark')
    }
  }, [])

  return {
    theme,           // 현재 설정 (light, dark, system)
    effectiveTheme,  // 실제 적용되는 테마 (light, dark)
    setTheme,        // 테마 변경 함수
    isDark: effectiveTheme === 'dark',
    isLight: effectiveTheme === 'light',
  }
}

export default useTheme

# RaymondsIndex 디자인 리뉴얼 계획서

> Linear.app 스타일 다크테마 적용

**작성일**: 2026-01-27
**대상**: raymondsindex.konnect-ai.net
**프로젝트 경로**: `raymondsindex-web/`

---

## 1. 개요

### 1.1 목표
- Linear.app의 세련된 다크테마 디자인 시스템 적용
- 기존 기능 100% 유지 (스크리너, 기업상세, 비교 등)
- 데이터 가독성과 프로페셔널한 느낌 강화

### 1.2 Linear.app 디자인 분석 결과

| 요소 | Linear.app 특징 |
|------|----------------|
| **배경** | 순수 검정 (#000000 ~ #0A0A0A) |
| **텍스트** | 흰색(#FFFFFF), 회색(#7C7C7C) |
| **카드** | 미세하게 밝은 배경, 희미한 보더 |
| **버튼** | 흰색 Primary, 투명 Ghost |
| **폰트** | Hero: Serif (GT Super), Body: Sans-serif |
| **여백** | 넉넉한 패딩, 높은 데이터 밀도 |
| **애니메이션** | 미세한 hover 효과, 부드러운 전환 |

---

## 2. 색상 시스템 (Design Tokens)

### 2.1 새로운 다크테마 팔레트

```css
/* Linear-Style Dark Theme */
:root {
  /* Core Colors */
  --linear-bg-primary: #000000;      /* 메인 배경 */
  --linear-bg-secondary: #0A0A0B;    /* 섹션 배경 */
  --linear-bg-tertiary: #111113;     /* 카드 배경 */
  --linear-bg-elevated: #18181B;     /* 팝오버/드롭다운 */

  /* Text Colors */
  --linear-text-primary: #FFFFFF;    /* 헤딩, 강조 텍스트 */
  --linear-text-secondary: #A1A1AA;  /* 본문 텍스트 */
  --linear-text-tertiary: #71717A;   /* 보조 텍스트 */
  --linear-text-muted: #52525B;      /* 비활성 텍스트 */

  /* Border Colors */
  --linear-border-default: rgba(255, 255, 255, 0.08);
  --linear-border-subtle: rgba(255, 255, 255, 0.05);
  --linear-border-strong: rgba(255, 255, 255, 0.15);

  /* Accent Colors */
  --linear-accent-primary: #5E6AD2;   /* Linear 보라색 */
  --linear-accent-hover: #7C85E0;
  --linear-accent-blue: #3B82F6;
  --linear-accent-green: #22C55E;
  --linear-accent-yellow: #EAB308;
  --linear-accent-red: #EF4444;

  /* Interactive */
  --linear-hover-bg: rgba(255, 255, 255, 0.05);
  --linear-active-bg: rgba(255, 255, 255, 0.08);
  --linear-focus-ring: rgba(94, 106, 210, 0.5);
}
```

### 2.2 등급별 색상 (유지 + 개선)

```typescript
// 기존 등급 색상 유지 (데이터 식별성 위해)
export const GRADE_COLORS_DARK = {
  'A++': { bg: '#1E40AF', text: '#FFFFFF', glow: 'rgba(30, 64, 175, 0.3)' },
  'A+':  { bg: '#2563EB', text: '#FFFFFF', glow: 'rgba(37, 99, 235, 0.3)' },
  'A':   { bg: '#3B82F6', text: '#FFFFFF', glow: 'rgba(59, 130, 246, 0.3)' },
  'A-':  { bg: '#60A5FA', text: '#000000', glow: 'rgba(96, 165, 250, 0.3)' },
  'B+':  { bg: '#22C55E', text: '#FFFFFF', glow: 'rgba(34, 197, 94, 0.3)' },
  'B':   { bg: '#84CC16', text: '#000000', glow: 'rgba(132, 204, 22, 0.3)' },
  'B-':  { bg: '#EAB308', text: '#000000', glow: 'rgba(234, 179, 8, 0.3)' },
  'C+':  { bg: '#F97316', text: '#FFFFFF', glow: 'rgba(249, 115, 22, 0.3)' },
  'C':   { bg: '#EF4444', text: '#FFFFFF', glow: 'rgba(239, 68, 68, 0.3)' },
};
```

---

## 3. 타이포그래피

### 3.1 폰트 시스템

```typescript
// layout.tsx 변경
const displayFont = localFont({
  src: './fonts/GTSuper-Display.woff2',  // Linear 스타일 Hero 폰트
  variable: '--font-display',
  display: 'swap',
});

// 또는 Google Fonts 대안
import { Playfair_Display, Inter } from 'next/font/google';

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
});

const inter = Inter({
  subsets: ['latin', 'latin-ext'],
  variable: '--font-sans',
  display: 'swap',
});
```

### 3.2 타이포그래피 스케일

| 요소 | 크기 | 굵기 | 폰트 |
|------|------|------|------|
| Hero H1 | 48px / 3rem | 700 | Display (Serif) |
| Page H1 | 24px / 1.5rem | 600 | Sans |
| Section H2 | 18px / 1.125rem | 600 | Sans |
| Card Title | 14px / 0.875rem | 600 | Sans |
| Body | 14px / 0.875rem | 400 | Sans |
| Caption | 12px / 0.75rem | 400 | Sans |
| Label | 10px / 0.625rem | 500 | Sans |

---

## 4. 컴포넌트별 변경 사항

### 4.1 Layout (`app/layout.tsx`)

**변경 전:**
```tsx
<body className="...antialiased min-h-screen flex flex-col">
```

**변경 후:**
```tsx
<html lang="ko" className="dark">
  <body className="bg-black text-white antialiased min-h-screen flex flex-col">
```

### 4.2 Header (`components/layout/header.tsx`)

**변경 사항:**
- 배경: `bg-white/95` → `bg-black/95 border-b border-white/10`
- 로고 배경: `bg-blue-600` → `bg-linear-accent` (Linear 보라색)
- 텍스트: `text-gray-900` → `text-white`
- 네비게이션: `text-gray-600` → `text-zinc-400 hover:text-white`
- 버튼: `bg-blue-600` → `bg-white text-black`

```tsx
// 변경 후 Header
<header className="sticky top-0 z-50 w-full border-b border-white/10 bg-black/95 backdrop-blur supports-[backdrop-filter]:bg-black/80">
  <div className="container mx-auto px-4">
    <div className="flex h-14 items-center justify-between">
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-[#5E6AD2] text-white">
          <BarChart3 className="w-4 h-4" />
        </div>
        <span className="text-base font-semibold text-white">RaymondsIndex</span>
      </Link>

      {/* Navigation */}
      <nav className="hidden md:flex items-center gap-6">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'text-sm font-medium transition-colors',
              pathname === item.href
                ? 'text-white'
                : 'text-zinc-400 hover:text-white'
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      {/* Auth */}
      <div className="hidden md:flex items-center gap-3">
        <Link href="/login" className="text-sm text-zinc-400 hover:text-white">
          로그인
        </Link>
        <Link
          href="/signup"
          className="px-4 py-1.5 text-sm font-medium text-black bg-white rounded-lg hover:bg-zinc-200"
        >
          회원가입
        </Link>
      </div>
    </div>
  </div>
</header>
```

### 4.3 Card 컴포넌트 (`components/ui/card.tsx`)

**변경 사항:**
```tsx
function Card({ className, ...props }) {
  return (
    <div
      className={cn(
        "bg-zinc-900/50 text-zinc-100 rounded-lg border border-white/10",
        "backdrop-blur-sm",
        className
      )}
      {...props}
    />
  )
}

function CardHeader({ className, ...props }) {
  return (
    <div
      className={cn("px-4 py-3 border-b border-white/5", className)}
      {...props}
    />
  )
}

function CardTitle({ className, ...props }) {
  return (
    <div
      className={cn("text-sm font-semibold text-white", className)}
      {...props}
    />
  )
}
```

### 4.4 Button 컴포넌트

```tsx
const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5E6AD2]/50 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-white text-black hover:bg-zinc-200",
        secondary: "bg-zinc-800 text-zinc-100 hover:bg-zinc-700 border border-white/10",
        ghost: "text-zinc-400 hover:text-white hover:bg-white/5",
        outline: "border border-white/20 text-zinc-300 hover:bg-white/5 hover:text-white",
        destructive: "bg-red-600 text-white hover:bg-red-700",
      },
      size: {
        default: "h-9 px-4",
        sm: "h-7 px-3 text-xs",
        lg: "h-11 px-6",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);
```

### 4.5 Table 컴포넌트

```tsx
const Table = ({ className, ...props }) => (
  <table
    className={cn("w-full caption-bottom text-sm", className)}
    {...props}
  />
);

const TableHeader = ({ className, ...props }) => (
  <thead
    className={cn("border-b border-white/10 bg-black/50", className)}
    {...props}
  />
);

const TableRow = ({ className, ...props }) => (
  <tr
    className={cn(
      "border-b border-white/5 transition-colors",
      "hover:bg-white/[0.02]",
      className
    )}
    {...props}
  />
);

const TableHead = ({ className, ...props }) => (
  <th
    className={cn(
      "h-10 px-3 text-left align-middle text-xs font-medium text-zinc-400 uppercase tracking-wider",
      className
    )}
    {...props}
  />
);

const TableCell = ({ className, ...props }) => (
  <td
    className={cn("px-3 py-2.5 align-middle text-zinc-300", className)}
    {...props}
  />
);
```

### 4.6 GradeBadge 컴포넌트

```tsx
export function GradeBadge({ grade, size = 'md', className }) {
  const colors = GRADE_COLORS_DARK[grade] || { bg: '#52525B', text: '#FFF' };

  return (
    <div
      className={cn(
        'rounded-md flex items-center justify-center font-semibold',
        'shadow-lg transition-transform hover:scale-105',
        sizeClasses[size],
        className
      )}
      style={{
        backgroundColor: colors.bg,
        color: colors.text,
        boxShadow: `0 0 20px ${colors.glow}`,
      }}
    >
      {grade}
    </div>
  );
}
```

---

## 5. 페이지별 변경 사항

### 5.1 홈페이지 (`app/page.tsx`)

**현재 구조 유지, 스타일만 변경:**

```tsx
export default function HomePage() {
  return (
    <div className="min-h-screen bg-black">
      {/* Hero Section */}
      <section className="border-b border-white/10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-white">
                RaymondsIndex<sup className="text-[10px]">TM</sup> 2025
              </h1>
              <p className="text-xs text-zinc-500">
                당신의 투자금, 제대로 쓰이고 있습니까?
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* KPI Cards - Linear 스타일 */}
      <section className="container mx-auto px-4 py-4">
        <div className="grid grid-cols-4 gap-3">
          {/* KPI 카드들 - 배경 투명, 보더 강조 */}
        </div>
      </section>

      {/* Main Content */}
      <section className="container mx-auto px-4 py-4">
        {/* TOP 10 테이블 + 사이드 패널 */}
      </section>
    </div>
  );
}
```

### 5.2 스크리너 (`app/screener/page.tsx`)

**기존 기능 100% 유지:**
- 필터 패널: 다크 스타일 적용
- 테이블: Linear 스타일 행/열
- 비교 기능: 그대로 작동
- 페이지네이션: 스타일만 변경

### 5.3 기업 상세 (`app/company/[id]/page.tsx`)

- 레이더 차트: 다크 배경에 맞게 색상 조정
- 지표 카드: 글로우 효과 추가
- 위험신호 패널: 빨간색/초록색 강조 유지

---

## 6. globals.css 변경

```css
/* Linear-Style Dark Theme for RaymondsIndex */
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));

/* ============================================
   Linear-Style Dark Theme
   ============================================ */
:root {
  --radius: 0.5rem;

  /* Dark Theme (Default) */
  --background: #000000;
  --foreground: #FFFFFF;
  --card: #0A0A0B;
  --card-foreground: #FAFAFA;
  --popover: #111113;
  --popover-foreground: #FAFAFA;
  --primary: #FFFFFF;
  --primary-foreground: #000000;
  --secondary: #18181B;
  --secondary-foreground: #A1A1AA;
  --muted: #27272A;
  --muted-foreground: #71717A;
  --accent: #5E6AD2;
  --accent-foreground: #FFFFFF;
  --destructive: #EF4444;
  --border: rgba(255, 255, 255, 0.08);
  --input: rgba(255, 255, 255, 0.1);
  --ring: #5E6AD2;

  /* Chart Colors for Dark Theme */
  --chart-1: #5E6AD2;
  --chart-2: #22C55E;
  --chart-3: #3B82F6;
  --chart-4: #F97316;
  --chart-5: #EF4444;
}

@layer base {
  * {
    @apply border-border;
  }

  html {
    color-scheme: dark;
  }

  body {
    @apply bg-black text-white;
    font-synthesis: none;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  /* Selection Color */
  ::selection {
    background: rgba(94, 106, 210, 0.3);
  }
}

/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.25);
}

/* Focus States */
.focus-ring {
  @apply focus:outline-none focus:ring-2 focus:ring-[#5E6AD2]/50 focus:ring-offset-2 focus:ring-offset-black;
}
```

---

## 7. 구현 순서 (Phase)

### Phase 1: 기반 작업 (Day 1)
1. [ ] `globals.css` 다크 테마 변수 적용
2. [ ] `layout.tsx`에 `dark` 클래스 및 기본 배경 적용
3. [ ] 기본 UI 컴포넌트 업데이트 (Card, Button, Table)

### Phase 2: 레이아웃 (Day 2)
4. [ ] Header 컴포넌트 다크 스타일 적용
5. [ ] Footer 컴포넌트 다크 스타일 적용
6. [ ] 검색바 스타일 조정

### Phase 3: 핵심 컴포넌트 (Day 3)
7. [ ] GradeBadge 글로우 효과
8. [ ] KPICard 스타일 업데이트
9. [ ] TopCompaniesTable 스타일 업데이트

### Phase 4: 페이지 (Day 4-5)
10. [ ] 홈페이지 스타일 적용
11. [ ] 스크리너 페이지 (필터 패널, 테이블)
12. [ ] 기업 상세 페이지 (차트, 지표 카드)
13. [ ] 방법론 페이지

### Phase 5: 검증 (Day 6)
14. [ ] 전체 기능 테스트
15. [ ] 반응형 확인 (모바일/태블릿)
16. [ ] 접근성 검사 (컬러 대비)
17. [ ] 성능 최적화

---

## 8. 위험 관리

### 8.1 기능 유지 체크리스트

| 기능 | 테스트 항목 |
|------|------------|
| **인증** | 로그인/회원가입 정상 작동 |
| **검색** | 기업 검색 자동완성 |
| **스크리너** | 모든 필터 조합 |
| **비교** | 최대 4개 기업 비교 |
| **상세** | 레이더 차트, 지표 표시 |
| **CSV 내보내기** | 데이터 정확성 |
| **관리자** | 관리자 페이지 접근 |

### 8.2 롤백 계획

```bash
# 변경 전 브랜치 생성
git checkout -b feat/linear-dark-theme
git checkout -b backup/pre-dark-theme main

# 문제 발생 시 롤백
git checkout main
git reset --hard backup/pre-dark-theme
```

---

## 9. 참고 자료

- [Linear.app](https://linear.app) - 디자인 레퍼런스
- [Tailwind CSS Dark Mode](https://tailwindcss.com/docs/dark-mode)
- [shadcn/ui Theming](https://ui.shadcn.com/docs/theming)

---

## 10. 예상 결과

### Before (현재)
- 밝은 배경, 파란색 악센트
- 표준 카드 UI
- 일반적인 SaaS 느낌

### After (변경 후)
- 프리미엄 다크 테마
- Linear 스타일의 세련된 인터페이스
- 데이터 중심의 프로페셔널한 느낌
- 등급 뱃지 글로우 효과로 시각적 계층 강화

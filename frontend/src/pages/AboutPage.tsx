import { Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'

interface PageContent {
  [section: string]: {
    [field: string]: string
  }
}

// 기본값 (API 로딩 전 또는 실패 시)
const DEFAULT_CONTENT: PageContent = {
  hero: {
    badge: "투자 인텔리전스 플랫폼",
    title: "숨겨진 관계망을 AI로 분석하여\n투자 리스크를 조기 발견",
    description: "공시 자료만으로는 파악할 수 없는 임원의 과거 경력, CB 인수자의 다른 참여 기업, 대주주의 특수관계인 네트워크를 3단계 관계망으로 자동 시각화합니다.",
  },
  why_section: {
    title: "왜 RaymondsRisk인가요?",
    description: "기관투자자만 접근하던 정보를 개인투자자도 동등하게 이용할 수 있습니다.",
  },
  advantage1: {
    title: "정보 비대칭 해소",
    description: "기관투자자는 전문 실사팀과 고가의 터미널로 기업을 분석하지만, 개인투자자는 공시 자료에만 의존합니다. RaymondsRisk는 이러한 정보 격차를 해소합니다.",
  },
  advantage2: {
    title: "특허 기술 기반 신뢰성",
    description: "대한민국 특허청에 출원 중인 '3단계 계층적 관계망 시각화' 및 '포트폴리오 학습 시스템' 특허 기술을 기반으로, 1.5초 이내에 복잡한 관계망을 구축하고 78.3% 정확도로 리스크를 예측합니다.",
  },
  advantage3: {
    title: "실시간 업데이트",
    description: "CB 발행, 대표이사 변경, 대주주 변동, 거래량 급증 등 7가지 위험 신호를 실시간으로 업데이트합니다. 시장 변화에 신속하게 대응할 수 있습니다.",
  },
  advantage4: {
    title: "합법적이고 투명한 데이터",
    description: "금융감독원 DART, 한국거래소 KRX, 대법원 판결문 등 모두 공개된 합법적 데이터만 사용합니다. 불법 내부정보는 절대 활용하지 않으며 PIPA를 완벽히 준수합니다.",
  },
  advantage5: {
    title: "접근성과 경제성",
    description: "합리적인 가격으로 기관투자자 수준의 분석 도구를 이용할 수 있으며, 간편하게 시작할 수 있습니다.",
  },
  features_section: {
    title: "주요 기능",
    description: "AI 기반 관계망 분석부터 실시간 모니터링까지, 투자 의사결정에 필요한 모든 기능을 제공합니다.",
  },
  feature1: {
    badge: "기능 1",
    title: "3단계 관계망 자동 분석",
    description: "검색창에 종목코드나 기업명만 입력하면, AI가 자동으로 3단계 관계망을 1.5초 만에 구축합니다.",
    image: "",
  },
  feature2: {
    badge: "기능 2",
    title: "AI 리스크 조기 경고",
    description: "500개 이상의 부실 기업 패턴을 학습한 AI가 40개 이상의 변수를 종합 분석하여 0~100점의 리스크 점수를 산출합니다.",
    image: "",
  },
  feature3: {
    badge: "기능 3",
    title: "포트폴리오 주가 패턴 예측",
    description: "관계망으로 연결된 기업들을 묶어 포트폴리오로 저장하면, AI가 30차원 특징을 자동 추출하여 30일 후 수익률을 예측합니다.",
    image: "",
  },
  feature4: {
    badge: "기능 4",
    title: "24시간 실시간 모니터링",
    description: "내 포트폴리오에 등록된 모든 기업을 24시간 자동 감시하며, 7가지 이벤트 발생 시 즉시 알림을 발송합니다.",
    image: "",
  },
  stats_section: {
    title: "검증된 성과",
  },
  cta_section: {
    title: "지금 바로 시작하세요",
    description: "RaymondsRisk로 숨겨진 투자 리스크를 발견하세요.",
  },
}

export default function AboutPage() {
  const [content, setContent] = useState<PageContent>(DEFAULT_CONTENT)

  useEffect(() => {
    const loadContent = async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/content/about`)
        if (response.ok) {
          const data = await response.json()
          if (data.content) {
            // 기본값과 API 값 병합
            const merged = { ...DEFAULT_CONTENT }
            for (const section of Object.keys(data.content)) {
              if (merged[section]) {
                merged[section] = { ...merged[section], ...data.content[section] }
              } else {
                merged[section] = data.content[section]
              }
            }
            setContent(merged)
          }
        }
      } catch {
        // API 실패 시 기본값 사용
        console.log('Using default content')
      }
    }
    loadContent()
  }, [])

  // 이미지 URL 처리 (Data URL 또는 상대경로 지원)
  const getImageUrl = (url: string) => {
    if (!url) return ''
    if (url.startsWith('data:')) return url  // Base64 Data URL
    if (url.startsWith('http')) return url
    return `${import.meta.env.VITE_API_URL || ''}${url}`
  }

  return (
    <div className="min-h-screen bg-theme-bg">
      {/* 헤더 - 메인과 동일한 네비게이션 */}
      <header className="sticky top-0 z-50 bg-theme-bg/80 backdrop-blur-lg border-b border-theme-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link to="/" className="inline-block">
            <RaymondsRiskLogo size="md" variant="compact" />
          </Link>

          {/* 네비게이션 */}
          <nav className="hidden md:flex items-center gap-1">
            <Link
              to="/"
              className="px-3 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-theme-hover rounded-lg transition-all"
            >
              검색
            </Link>
            <Link
              to="/about"
              className="px-3 py-2 text-sm text-text-primary font-medium bg-theme-hover rounded-lg"
            >
              서비스 소개
            </Link>
            <Link
              to="/contact"
              className="px-3 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-theme-hover rounded-lg transition-all"
            >
              문의
            </Link>
          </nav>

          <Link
            to="/login"
            className="px-4 py-2 bg-[#5E6AD2] hover:bg-[#4F5ABF] text-white text-sm font-medium rounded-lg transition-colors"
          >
            로그인
          </Link>
        </div>
      </header>

      {/* 히어로 섹션 */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-[#5E6AD2]/5 to-transparent dark:from-[#5E6AD2]/10" />
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-[#5E6AD2]/10 text-[#5E6AD2] rounded-full text-sm font-medium mb-6">
              <span className="w-2 h-2 bg-[#5E6AD2] rounded-full animate-pulse" />
              {content.hero?.badge || '투자 인텔리전스 플랫폼'}
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-text-primary mb-6 leading-tight">
              {(content.hero?.title || '').split('\n').map((line, i, arr) => (
                <span key={i}>
                  {i === arr.length - 1 ? <span className="text-[#5E6AD2]">{line}</span> : line}
                  {i < arr.length - 1 && <br />}
                </span>
              ))}
            </h1>
            <p className="text-lg text-text-secondary mb-8 leading-relaxed">
              {content.hero?.description}
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                to="/login"
                className="w-full sm:w-auto px-8 py-3.5 bg-[#5E6AD2] hover:bg-[#4F5ABF] text-white font-medium rounded-lg transition-colors"
              >
                시작하기
              </Link>
              <a
                href="#features"
                className="w-full sm:w-auto px-8 py-3.5 bg-theme-surface hover:bg-theme-hover border border-theme-border text-text-primary font-medium rounded-lg transition-colors"
              >
                기능 살펴보기
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* 서비스 장점 섹션 */}
      <section className="py-16 sm:py-24 bg-theme-surface">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-text-primary mb-4">
              {content.why_section?.title || '왜 RaymondsRisk인가요?'}
            </h2>
            <p className="text-text-secondary max-w-2xl mx-auto">
              {content.why_section?.description}
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* 장점 1 */}
            <div className="bg-theme-card border border-theme-border rounded-xl p-6 hover:shadow-lg transition-shadow">
              <div className="w-12 h-12 bg-[#5E6AD2]/10 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-[#5E6AD2]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">{content.advantage1?.title}</h3>
              <p className="text-sm text-text-secondary leading-relaxed">
                {content.advantage1?.description}
              </p>
            </div>

            {/* 장점 2 */}
            <div className="bg-theme-card border border-theme-border rounded-xl p-6 hover:shadow-lg transition-shadow">
              <div className="w-12 h-12 bg-accent-success/10 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">{content.advantage2?.title}</h3>
              <p className="text-sm text-text-secondary leading-relaxed">
                {content.advantage2?.description}
              </p>
            </div>

            {/* 장점 3 */}
            <div className="bg-theme-card border border-theme-border rounded-xl p-6 hover:shadow-lg transition-shadow">
              <div className="w-12 h-12 bg-accent-warning/10 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-accent-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">{content.advantage3?.title}</h3>
              <p className="text-sm text-text-secondary leading-relaxed">
                {content.advantage3?.description}
              </p>
            </div>

            {/* 장점 4 */}
            <div className="bg-theme-card border border-theme-border rounded-xl p-6 hover:shadow-lg transition-shadow">
              <div className="w-12 h-12 bg-accent-info/10 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-accent-info" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">{content.advantage4?.title}</h3>
              <p className="text-sm text-text-secondary leading-relaxed">
                {content.advantage4?.description}
              </p>
            </div>

            {/* 장점 5 */}
            <div className="bg-theme-card border border-theme-border rounded-xl p-6 hover:shadow-lg transition-shadow md:col-span-2 lg:col-span-1">
              <div className="w-12 h-12 bg-accent-purple/10 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-accent-purple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">{content.advantage5?.title}</h3>
              <p className="text-sm text-text-secondary leading-relaxed">
                {content.advantage5?.description}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 주요 기능 섹션 */}
      <section id="features" className="py-16 sm:py-24">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <h2 className="text-2xl sm:text-3xl font-bold text-text-primary mb-4">
              {content.features_section?.title || '주요 기능'}
            </h2>
            <p className="text-text-secondary max-w-2xl mx-auto">
              {content.features_section?.description}
            </p>
          </div>

          {/* 기능 1 */}
          <div className="mb-20">
            <div className="grid lg:grid-cols-2 gap-8 items-center">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-[#5E6AD2]/10 text-[#5E6AD2] rounded-full text-sm font-medium mb-4">
                  {content.feature1?.badge || '기능 1'}
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-text-primary mb-4">
                  {content.feature1?.title}
                </h3>
                <p className="text-text-secondary mb-6 leading-relaxed">
                  {content.feature1?.description}
                </p>
                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 bg-data-company/20 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-xs font-bold text-data-company">1</span>
                    </div>
                    <div>
                      <span className="font-medium text-text-primary">제1계층 (직접 관계)</span>
                      <p className="text-sm text-text-secondary">임원진, CB 발행 내역, 대주주 구성</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 bg-data-officer/20 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-xs font-bold text-data-officer">2</span>
                    </div>
                    <div>
                      <span className="font-medium text-text-primary">제2계층 (간접 관계)</span>
                      <p className="text-sm text-text-secondary">임원의 과거 경력 상장사, CB 인수자 정보</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 bg-data-cb/20 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-xs font-bold text-data-cb">3</span>
                    </div>
                    <div>
                      <span className="font-medium text-text-primary">제3계층 (확장 관계)</span>
                      <p className="text-sm text-text-secondary">경력사의 다른 CB 발행 기업, 인수자의 타 참여 기업</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-theme-surface border border-theme-border rounded-xl p-6">
                <div className="aspect-video bg-theme-card rounded-lg flex items-center justify-center overflow-hidden">
                  {content.feature1?.image ? (
                    <img src={getImageUrl(content.feature1.image)} alt={content.feature1?.title} className="w-full h-full object-cover" />
                  ) : (
                    <div className="text-center">
                      <svg className="w-16 h-16 text-text-muted mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                      </svg>
                      <p className="text-sm text-text-muted">관계망 시각화 미리보기</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* 기능 2 */}
          <div className="mb-20">
            <div className="grid lg:grid-cols-2 gap-8 items-center">
              <div className="order-2 lg:order-1 bg-theme-surface border border-theme-border rounded-xl p-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-accent-danger/10 border border-accent-danger/20 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-accent-danger/20 rounded-full flex items-center justify-center">
                        <span className="text-lg">🔴</span>
                      </div>
                      <div>
                        <p className="font-medium text-text-primary">고위험</p>
                        <p className="text-xs text-text-secondary">투자 재검토 권장</p>
                      </div>
                    </div>
                    <span className="text-2xl font-bold text-accent-danger">70+</span>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-accent-warning/10 border border-accent-warning/20 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-accent-warning/20 rounded-full flex items-center justify-center">
                        <span className="text-lg">🟡</span>
                      </div>
                      <div>
                        <p className="font-medium text-text-primary">중위험</p>
                        <p className="text-xs text-text-secondary">신중한 접근 필요</p>
                      </div>
                    </div>
                    <span className="text-2xl font-bold text-accent-warning">50-69</span>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-accent-success/10 border border-accent-success/20 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-accent-success/20 rounded-full flex items-center justify-center">
                        <span className="text-lg">🟢</span>
                      </div>
                      <div>
                        <p className="font-medium text-text-primary">저위험</p>
                        <p className="text-xs text-text-secondary">상대적 안정</p>
                      </div>
                    </div>
                    <span className="text-2xl font-bold text-accent-success">&lt;50</span>
                  </div>
                </div>
              </div>
              <div className="order-1 lg:order-2">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-accent-danger/10 text-accent-danger rounded-full text-sm font-medium mb-4">
                  {content.feature2?.badge || '기능 2'}
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-text-primary mb-4">
                  {content.feature2?.title}
                </h3>
                <p className="text-text-secondary mb-6 leading-relaxed">
                  {content.feature2?.description}
                </p>
                <ul className="space-y-2 text-sm text-text-secondary">
                  <li className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    대표이사 횡령 전력 탐지
                  </li>
                  <li className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    작전세력 연루 여부 확인
                  </li>
                  <li className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    최대주주 잦은 변경 패턴 감지
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* 기능 3 */}
          <div className="mb-20">
            <div className="grid lg:grid-cols-2 gap-8 items-center">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-accent-purple/10 text-accent-purple rounded-full text-sm font-medium mb-4">
                  {content.feature3?.badge || '기능 3'}
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-text-primary mb-4">
                  {content.feature3?.title}
                </h3>
                <p className="text-text-secondary mb-6 leading-relaxed">
                  {content.feature3?.description}
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-theme-surface border border-theme-border rounded-lg p-4">
                    <p className="text-2xl font-bold text-[#5E6AD2]">78.3%</p>
                    <p className="text-xs text-text-secondary">예측 정확도</p>
                  </div>
                  <div className="bg-theme-surface border border-theme-border rounded-lg p-4">
                    <p className="text-2xl font-bold text-text-primary">30일</p>
                    <p className="text-xs text-text-secondary">예측 기간</p>
                  </div>
                  <div className="bg-theme-surface border border-theme-border rounded-lg p-4">
                    <p className="text-2xl font-bold text-text-primary">127</p>
                    <p className="text-xs text-text-secondary">유사 사례 제공</p>
                  </div>
                  <div className="bg-theme-surface border border-theme-border rounded-lg p-4">
                    <p className="text-2xl font-bold text-text-primary">SHAP</p>
                    <p className="text-xs text-text-secondary">설명 가능 AI</p>
                  </div>
                </div>
              </div>
              <div className="bg-theme-surface border border-theme-border rounded-xl p-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-text-primary">예측 결과</span>
                    <span className="px-2 py-1 bg-accent-success/10 text-accent-success text-xs rounded">상승 예측</span>
                  </div>
                  <div className="h-2 bg-theme-border rounded-full overflow-hidden">
                    <div className="h-full w-[78%] bg-gradient-to-r from-[#5E6AD2] to-accent-success rounded-full" />
                  </div>
                  <div className="flex justify-between text-xs text-text-muted">
                    <span>하락</span>
                    <span>보합</span>
                    <span>상승</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 기능 4 */}
          <div>
            <div className="grid lg:grid-cols-2 gap-8 items-center">
              <div className="order-2 lg:order-1 bg-theme-surface border border-theme-border rounded-xl p-6">
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { icon: '📄', label: 'CB 발행', desc: '전환사채 발행 공시' },
                    { icon: '👔', label: '대표이사 변경', desc: '경영진 교체 신호' },
                    { icon: '📊', label: '대주주 변동', desc: '5% 이상 지분 변동' },
                    { icon: '📈', label: '거래량 급증', desc: '평균 대비 2배 이상' },
                    { icon: '⚡', label: '주가 급등락', desc: '±10% 이상 등락' },
                    { icon: '🚫', label: '거래정지', desc: '매매 거래정지' },
                    { icon: '⚠️', label: '관리종목 지정', desc: '상장폐지 위험', className: 'col-span-2' },
                  ].map((item, i) => (
                    <div
                      key={i}
                      className={`flex items-center gap-3 p-3 bg-theme-card border border-theme-border rounded-lg ${item.className || ''}`}
                    >
                      <span className="text-xl">{item.icon}</span>
                      <div>
                        <p className="text-sm font-medium text-text-primary">{item.label}</p>
                        <p className="text-xs text-text-secondary">{item.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="order-1 lg:order-2">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-accent-warning/10 text-accent-warning rounded-full text-sm font-medium mb-4">
                  {content.feature4?.badge || '기능 4'}
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-text-primary mb-4">
                  {content.feature4?.title}
                </h3>
                <p className="text-text-secondary mb-6 leading-relaxed">
                  {content.feature4?.description}
                </p>
                <ul className="space-y-2 text-sm text-text-secondary">
                  <li className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    이벤트 선택, 시간대 설정, 주말 제외 커스터마이징
                  </li>
                  <li className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    과도한 알림 방지 (1시간 1회, 하루 20건 제한)
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 검증된 성과 섹션 */}
      <section className="py-16 sm:py-24 bg-theme-surface">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-text-primary mb-4">
              {content.stats_section?.title || '검증된 성과'}
            </h2>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-5 gap-6">
            {[
              { value: '90%', label: '실사 시간 단축', sub: '3개월 → 3시간' },
              { value: '80%', label: '비용 절감', sub: '3억 → 6천만원' },
              { value: '95%', label: '리스크 탐지율', sub: '기존 70% 대비 +25%p' },
              { value: '78.3%', label: 'AI 예측 정확도', sub: '무작위 33% 대비 2.4배' },
              { value: '1.5초', label: '관계망 구축', sub: '1~3계층 전체 생성' },
            ].map((stat, i) => (
              <div key={i} className="text-center p-6 bg-theme-card border border-theme-border rounded-xl">
                <p className="text-3xl sm:text-4xl font-bold text-[#5E6AD2] mb-2">{stat.value}</p>
                <p className="font-medium text-text-primary mb-1">{stat.label}</p>
                <p className="text-xs text-text-secondary">{stat.sub}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 추천 대상 섹션 */}
      <section className="py-16 sm:py-24">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-text-primary mb-4">
              이런 분들에게 추천합니다
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { icon: '👤', title: '개인투자자', desc: '기관과 동등한 정보로 공정하게 투자하고 싶은 분' },
              { icon: '💼', title: '직장인 투자자', desc: '시간이 부족해 효율적으로 리스크를 관리하고 싶은 분' },
              { icon: '🏢', title: '중소 VC', desc: '스타트업 실사에 시간과 비용을 절감하고 싶은 투자사' },
              { icon: '📋', title: '상장사 IR팀', desc: '자사 주주 구조와 관계망을 상시 모니터링하려는 기업' },
            ].map((item, i) => (
              <div key={i} className="bg-theme-card border border-theme-border rounded-xl p-6 text-center hover:shadow-lg transition-shadow">
                <span className="text-4xl mb-4 block">{item.icon}</span>
                <h3 className="text-lg font-semibold text-text-primary mb-2">{item.title}</h3>
                <p className="text-sm text-text-secondary">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA 섹션 */}
      <section className="py-16 sm:py-24 bg-gradient-to-r from-[#5E6AD2] to-[#4F5ABF]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-white mb-4">
            {content.cta_section?.title || '지금 바로 시작하세요'}
          </h2>
          <p className="text-white/80 mb-8 max-w-2xl mx-auto">
            {content.cta_section?.description}
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/login"
              className="w-full sm:w-auto px-8 py-3.5 bg-white text-[#5E6AD2] font-medium rounded-lg hover:bg-gray-100 transition-colors"
            >
              시작하기
            </Link>
            <Link
              to="/contact"
              className="w-full sm:w-auto px-8 py-3.5 border border-white/30 text-white font-medium rounded-lg hover:bg-white/10 transition-colors"
            >
              문의하기
            </Link>
          </div>
        </div>
      </section>

      {/* 푸터 */}
      <footer className="py-12 bg-theme-card border-t border-theme-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <RaymondsRiskLogo size="sm" variant="compact" />
            <div className="flex items-center gap-6 text-sm text-text-secondary">
              <Link to="/terms" className="hover:text-text-primary transition-colors">이용약관</Link>
              <Link to="/privacy" className="hover:text-text-primary transition-colors">개인정보처리방침</Link>
              <a href="mailto:contact@konnect-ai.net" className="hover:text-text-primary transition-colors">문의</a>
            </div>
            <p className="text-sm text-text-muted">
              © 2024 Raymond Partners. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

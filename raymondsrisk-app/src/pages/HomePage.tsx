import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { colors } from '../constants/colors'
import { ListItem } from '../components'
import { getPlatformStats, type PlatformStats } from '../api/company'

export default function HomePage() {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [stats, setStats] = useState<PlatformStats | null>(null)

  // 통계 데이터 로드
  useEffect(() => {
    let isMounted = true  // 메모리 릭 방지

    getPlatformStats().then(data => {
      if (isMounted) setStats(data)
    })

    return () => {
      isMounted = false  // cleanup
    }
  }, [])

  const handleSearch = () => {
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery)}`)
    }
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: colors.white }}>
      {/* Top Navigation Bar - 토스 스타일 */}
      <header
        style={{
          padding: '12px 20px',
          paddingTop: 'max(env(safe-area-inset-top), 12px)',
          backgroundColor: colors.white,
          position: 'sticky',
          top: 0,
          zIndex: 100,
        }}
        role="banner"
      >
        <h1 style={{
          fontSize: '22px',
          fontWeight: '700',
          margin: 0,
          letterSpacing: '-0.02em'
        }}>
          <span style={{ color: colors.gray900 }}>레이먼즈</span>
          <span style={{ color: colors.red500 }}>리스크</span>
        </h1>
        <p style={{
          fontSize: '14px',
          color: colors.gray500,
          margin: '2px 0 0 0',
          fontWeight: '400'
        }}>
          관계형 리스크 추적 및 분석
        </p>
      </header>

      <main style={{ padding: '0 20px 32px' }} role="main">
        {/* 검색 섹션 */}
        <section style={{ marginBottom: '28px' }} aria-label="기업 검색">
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="기업명 검색"
              aria-label="기업명 검색"
              style={{
                flex: 1,
                padding: '14px 16px',
                borderRadius: '12px',
                border: 'none',
                backgroundColor: colors.gray50,
                color: colors.gray900,
                fontSize: '16px',
                fontWeight: '400',
                outline: 'none',
                minHeight: '48px',
              }}
            />
            <button
              onClick={handleSearch}
              aria-label="검색하기"
              style={{
                padding: '14px 20px',
                borderRadius: '12px',
                border: 'none',
                backgroundColor: colors.blue500,
                color: colors.white,
                fontSize: '16px',
                fontWeight: '600',
                cursor: 'pointer',
                minWidth: '48px',
                minHeight: '48px',
              }}
            >
              검색
            </button>
          </div>
        </section>

        {/* 통계 카드 그리드 */}
        <section style={{ marginBottom: '32px' }} aria-label="서비스 통계">
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '12px',
          }}>
            <StatCard label="분석 기업" value={stats?.companies.toLocaleString() || '-'} />
            <StatCard label="CB 발행" value={stats?.convertible_bonds.toLocaleString() || '-'} />
            <StatCard label="등기임원" value={stats?.officers.toLocaleString() || '-'} />
            <StatCard label="주주변동" value={stats?.major_shareholders.toLocaleString() || '-'} />
          </div>
        </section>

        {/* 내 메뉴 */}
        <section aria-label="내 메뉴" style={{ marginBottom: '24px' }}>
          <h2 style={{
            fontSize: '13px',
            fontWeight: '600',
            color: colors.gray500,
            margin: '0 0 12px 0',
            textTransform: 'uppercase',
            letterSpacing: '0.02em'
          }}>
            MY
          </h2>
          <nav
            style={{
              backgroundColor: colors.gray50,
              borderRadius: '16px',
              overflow: 'hidden',
            }}
            aria-label="내 메뉴"
          >
            <ListItem
              title="내 조회 기업"
              description="조회한 기업 30일간 무료 재열람"
              onClick={() => navigate('/my')}
              isLast
            />
          </nav>
        </section>

        {/* 기능 목록 */}
        <section aria-label="주요 기능">
          <h2 style={{
            fontSize: '13px',
            fontWeight: '600',
            color: colors.gray500,
            margin: '0 0 12px 0',
            textTransform: 'uppercase',
            letterSpacing: '0.02em'
          }}>
            주요 기능
          </h2>
          <nav
            style={{
              backgroundColor: colors.white,
              borderRadius: '16px',
              overflow: 'hidden',
            }}
            aria-label="기능 메뉴"
          >
            <ListItem
              title="이해관계자 네트워크"
              description="임원, 투자자, 주주간 연결 관계 시각화"
            />
            <ListItem
              title="리스크 패턴 탐지"
              description="부실 투자자, 반복 CB 발행 등 위험 신호"
            />
            <ListItem
              title="재무건전성 분석"
              description="부채비율, 유동비율 등 핵심 재무지표"
              isLast
            />
          </nav>
        </section>

        {/* 법적 면책 고지 */}
        <section
          style={{
            marginTop: '8px',
            padding: '16px',
            backgroundColor: colors.gray50,
            borderRadius: '12px',
          }}
          aria-label="투자 유의사항"
        >
          <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '14px', flexShrink: 0, marginTop: '1px' }}>ℹ️</span>
            <p style={{
              fontSize: '11px',
              color: colors.gray500,
              lineHeight: '1.5',
              margin: 0,
            }}>
              본 서비스는 투자 권유가 아닌 정보 제공 목적입니다.
              투자 결정은 본인 책임 하에 이루어져야 하며, 투자 손실에 대해 당사는 책임지지 않습니다.
              <span style={{ display: 'block', marginTop: '4px', color: colors.gray400 }}>
                데이터 출처: 금융감독원 DART
              </span>
            </p>
          </div>
        </section>
      </main>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <article
      style={{
        padding: '20px 16px',
        borderRadius: '16px',
        backgroundColor: colors.gray50,
        textAlign: 'center',
      }}
      aria-label={`${label}: ${value}`}
    >
      <div style={{
        fontSize: '24px',
        fontWeight: '700',
        color: colors.gray900,
        marginBottom: '4px',
        letterSpacing: '-0.02em'
      }}>
        {value}
      </div>
      <div style={{
        fontSize: '13px',
        fontWeight: '500',
        color: colors.gray500,
      }}>
        {label}
      </div>
    </article>
  )
}


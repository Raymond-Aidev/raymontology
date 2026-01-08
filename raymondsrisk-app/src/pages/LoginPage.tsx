import { useState } from 'react'
import { useAuth, debugLogs } from '../contexts/AuthContext'
import { colors } from '../constants/colors'

export default function LoginPage() {
  const { login, isLoading, error } = useAuth()
  const [loginInProgress, setLoginInProgress] = useState(false)
  const [showDebug, setShowDebug] = useState(false)

  const handleLogin = async () => {
    setLoginInProgress(true)
    try {
      await login()
    } catch {
      // 에러는 AuthContext에서 처리
    } finally {
      setLoginInProgress(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: colors.white,
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* 헤더 */}
      <header
        style={{
          padding: '12px 20px',
          paddingTop: 'max(env(safe-area-inset-top), 12px)',
          backgroundColor: colors.white,
        }}
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
      </header>

      {/* 메인 콘텐츠 */}
      <main style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 20px',
        textAlign: 'center',
      }}>
        {/* 아이콘 */}
        <div style={{
          width: '100px',
          height: '100px',
          borderRadius: '50%',
          backgroundColor: colors.blue500 + '15',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '32px',
          fontSize: '48px',
        }}>
          🔐
        </div>

        {/* 제목 */}
        <h2 style={{
          fontSize: '24px',
          fontWeight: '700',
          color: colors.gray900,
          margin: '0 0 12px 0',
        }}>
          토스로 시작하기
        </h2>

        {/* 설명 */}
        <p style={{
          fontSize: '15px',
          color: colors.gray500,
          margin: '0 0 40px 0',
          lineHeight: '1.5',
        }}>
          토스 계정으로 간편하게 로그인하고<br />
          기업 리스크 분석 서비스를 이용하세요
        </p>

        {/* 에러 메시지 */}
        {error && (
          <div style={{
            padding: '12px 16px',
            backgroundColor: colors.red500 + '10',
            borderRadius: '8px',
            marginBottom: '20px',
            width: '100%',
            maxWidth: '320px',
          }}>
            <p style={{
              fontSize: '14px',
              color: colors.red500,
              margin: 0,
            }}>
              {error}
            </p>
          </div>
        )}

        {/* 로그인 버튼 */}
        <button
          onClick={handleLogin}
          disabled={isLoading || loginInProgress}
          style={{
            width: '100%',
            maxWidth: '320px',
            padding: '16px 24px',
            borderRadius: '12px',
            border: 'none',
            backgroundColor: colors.blue500,
            color: colors.white,
            fontSize: '17px',
            fontWeight: '600',
            cursor: isLoading || loginInProgress ? 'not-allowed' : 'pointer',
            opacity: isLoading || loginInProgress ? 0.7 : 1,
          }}
        >
          {isLoading || loginInProgress ? '로그인 중...' : '토스로 로그인'}
        </button>

        {/* 서비스 소개 */}
        <div style={{
          marginTop: '48px',
          padding: '20px',
          backgroundColor: colors.gray50,
          borderRadius: '12px',
          width: '100%',
          maxWidth: '320px',
        }}>
          <h3 style={{
            fontSize: '14px',
            fontWeight: '600',
            color: colors.gray900,
            margin: '0 0 12px 0',
          }}>
            레이먼즈리스크 서비스
          </h3>
          <ul style={{
            margin: 0,
            padding: '0 0 0 16px',
            fontSize: '13px',
            color: colors.gray500,
            textAlign: 'left',
            lineHeight: '1.8',
          }}>
            <li>3,900+ 상장기업 리스크 분석</li>
            <li>CB 투자자, 임원, 주주 관계망</li>
            <li>부실 투자자 패턴 탐지</li>
          </ul>
        </div>

        {/* 디버그 패널 (개발용) */}
        <div style={{ marginTop: '32px' }}>
          <button
            onClick={() => setShowDebug(!showDebug)}
            style={{
              padding: '8px 16px',
              fontSize: '12px',
              backgroundColor: colors.gray100,
              border: 'none',
              borderRadius: '8px',
              color: colors.gray600,
              cursor: 'pointer',
            }}
          >
            {showDebug ? '디버그 숨기기' : '디버그 보기'}
          </button>

          {showDebug && (
            <div style={{
              marginTop: '12px',
              padding: '12px',
              backgroundColor: '#1a1a2e',
              borderRadius: '8px',
              maxHeight: '300px',
              overflowY: 'auto',
              textAlign: 'left',
              width: '100%',
              maxWidth: '320px',
            }}>
              <div style={{
                fontFamily: 'monospace',
                fontSize: '11px',
                color: '#00ff00',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}>
                <div style={{ marginBottom: '8px', color: '#ffff00' }}>
                  === 환경 정보 ===
                </div>
                <div>DEV: {String(import.meta.env.DEV)}</div>
                <div>MODE: {import.meta.env.MODE}</div>
                <div>PROD: {String(import.meta.env.PROD)}</div>

                <div style={{ marginTop: '8px', marginBottom: '8px', color: '#ffff00' }}>
                  === 디버그 로그 ({debugLogs.length}개) ===
                </div>
                {debugLogs.length === 0 ? (
                  <div style={{ color: '#888' }}>(로그 없음)</div>
                ) : (
                  debugLogs.map((log, i) => (
                    <div key={i} style={{ marginBottom: '2px' }}>{log}</div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

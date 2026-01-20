import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { colors } from '../constants/colors'

export default function PaywallPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, isLoading, credits, login, error: authError } = useAuth()
  const [loginInProgress, setLoginInProgress] = useState(false)

  // 이전 페이지에서 전달된 기업 정보
  const returnTo = location.state?.returnTo || '/'
  const companyName = location.state?.companyName || '기업'

  const handleLogin = async () => {
    setLoginInProgress(true)
    try {
      await login()
      // 로그인 성공 후 이용권 있으면 원래 페이지로, 없으면 구매 페이지로
      if (credits > 0 || credits === -1) {
        navigate(returnTo, { replace: true })
      } else {
        navigate('/purchase', { state: { returnTo, companyName } })
      }
    } catch {
      // 에러는 AuthContext에서 처리
    } finally {
      setLoginInProgress(false)
    }
  }

  const handlePurchase = () => {
    navigate('/purchase', { state: { returnTo, companyName } })
  }

  if (isLoading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: colors.white,
      }}>
        <div style={{ color: colors.gray500 }}>로딩 중...</div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: colors.white }}>
      {/* 헤더 */}
      <header
        style={{
          padding: '12px 20px',
          paddingTop: 'max(env(safe-area-inset-top), 12px)',
          backgroundColor: colors.white,
          position: 'sticky',
          top: 0,
          zIndex: 100,
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

      <main style={{ padding: '40px 20px', textAlign: 'center' }}>
        {/* 아이콘 */}
        <div style={{
          width: '80px',
          height: '80px',
          borderRadius: '50%',
          backgroundColor: colors.blue500 + '15',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 24px',
          fontSize: '36px',
        }}>
          🔒
        </div>

        {/* 제목 */}
        <h2 style={{
          fontSize: '24px',
          fontWeight: '700',
          color: colors.gray900,
          margin: '0 0 8px 0',
          letterSpacing: '-0.02em',
        }}>
          프리미엄 리포트
        </h2>

        {/* 설명 */}
        <p style={{
          fontSize: '16px',
          color: colors.gray600,
          margin: '0 0 32px 0',
          lineHeight: '1.5',
        }}>
          <strong style={{ color: colors.gray900 }}>{companyName}</strong>의 상세 분석을<br />
          확인하려면 이용권이 필요해요
        </p>

        {/* 기능 목록 */}
        <div style={{
          backgroundColor: colors.gray50,
          borderRadius: '16px',
          padding: '20px',
          marginBottom: '32px',
          textAlign: 'left',
        }}>
          <div style={{ fontSize: '14px', fontWeight: '600', color: colors.gray900, marginBottom: '12px' }}>
            프리미엄 리포트에서 확인할 수 있어요
          </div>
          <ul style={{ margin: 0, padding: '0 0 0 20px', color: colors.gray600, fontSize: '14px', lineHeight: '1.8' }}>
            <li>종합 리스크 점수 및 등급</li>
            <li>CB(전환사채) 발행 이력</li>
            <li>임원 및 이해관계자 네트워크</li>
            <li>재무건전성 분석</li>
            <li>위험 신호 탐지 결과</li>
          </ul>
        </div>

        {/* 버튼 영역 - credits === -1은 무제한 */}
        {!isAuthenticated ? (
          <>
            <button
              onClick={handleLogin}
              disabled={loginInProgress}
              style={{
                width: '100%',
                padding: '16px',
                borderRadius: '12px',
                border: 'none',
                backgroundColor: loginInProgress ? colors.gray500 : colors.blue500,
                color: colors.white,
                fontSize: '17px',
                fontWeight: '600',
                cursor: loginInProgress ? 'not-allowed' : 'pointer',
                marginBottom: '12px',
                minHeight: '54px',
              }}
            >
              {loginInProgress ? '로그인 중...' : '토스로 시작하기'}
            </button>
            <p style={{
              fontSize: '13px',
              color: colors.gray500,
              margin: 0,
            }}>
              토스 계정으로 간편하게 로그인하고 이용권을 구매하세요
            </p>
          </>
        ) : (credits > 0 || credits === -1) ? (
          <>
            <div style={{
              backgroundColor: colors.gray50,
              borderRadius: '12px',
              padding: '16px',
              marginBottom: '16px',
            }}>
              <div style={{ fontSize: '14px', color: colors.gray500, marginBottom: '4px' }}>
                보유 이용권
              </div>
              <div style={{ fontSize: '28px', fontWeight: '700', color: colors.blue500 }}>
                {credits === -1 ? '무제한' : `${credits}건`}
              </div>
            </div>
            <button
              onClick={() => navigate(returnTo, { replace: true })}
              style={{
                width: '100%',
                padding: '16px',
                borderRadius: '12px',
                border: 'none',
                backgroundColor: colors.blue500,
                color: colors.white,
                fontSize: '17px',
                fontWeight: '600',
                cursor: 'pointer',
                minHeight: '54px',
              }}
            >
              리포트 확인하기
            </button>
          </>
        ) : (
          <>
            <button
              onClick={handlePurchase}
              style={{
                width: '100%',
                padding: '16px',
                borderRadius: '12px',
                border: 'none',
                backgroundColor: colors.blue500,
                color: colors.white,
                fontSize: '17px',
                fontWeight: '600',
                cursor: 'pointer',
                marginBottom: '12px',
                minHeight: '54px',
              }}
            >
              이용권 구매하기
            </button>
            <p style={{
              fontSize: '13px',
              color: colors.gray500,
              margin: 0,
            }}>
              리포트 1건당 300원부터
            </p>
          </>
        )}

        {/* 에러 메시지 표시 */}
        {authError && (
          <div style={{
            marginTop: '16px',
            padding: '16px',
            backgroundColor: colors.red500 + '10',
            borderRadius: '12px',
          }}>
            <p style={{
              fontSize: '14px',
              color: colors.red500,
              margin: 0,
              textAlign: 'center',
            }}>
              {authError}
            </p>
          </div>
        )}

        {/* 뒤로가기 */}
        <button
          onClick={() => navigate(-1)}
          style={{
            marginTop: '24px',
            padding: '12px 24px',
            borderRadius: '8px',
            border: `1px solid ${colors.gray100}`,
            backgroundColor: colors.white,
            color: colors.gray600,
            fontSize: '15px',
            fontWeight: '500',
            cursor: 'pointer',
            minHeight: '44px',
          }}
        >
          돌아가기
        </button>

      </main>
    </div>
  )
}

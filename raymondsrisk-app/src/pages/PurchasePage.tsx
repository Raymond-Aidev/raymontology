import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { IAP } from '@apps-in-toss/web-framework'
import { useAuth, debugLogs } from '../contexts/AuthContext'
import '../types/auth' // 전역 타입 선언 import
import * as creditService from '../services/creditService'
import type { CreditProduct } from '../services/creditService'
import { colors } from '../constants/colors'

// 기본 상품 목록 (API 실패 시 폴백)
const DEFAULT_PRODUCTS: ProductDisplay[] = [
  {
    id: 'report_1',
    name: '리포트 1건',
    credits: 1,
    price: 500,
    pricePerCredit: 500,
    badge: null,
  },
  {
    id: 'report_10',
    name: '리포트 10건',
    credits: 10,
    price: 3000,
    pricePerCredit: 300,
    badge: '추천',
  },
  {
    id: 'report_30',
    name: '리포트 30건',
    credits: 30,
    price: 7000,
    pricePerCredit: 233,
    badge: '최저가',
  },
]

interface ProductDisplay extends CreditProduct {
  pricePerCredit: number
}

export default function PurchasePage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, credits, refreshCredits, login, isLoading: authLoading, error: authError } = useAuth()

  const [products, setProducts] = useState<ProductDisplay[]>(DEFAULT_PRODUCTS)
  const [showDebug, setShowDebug] = useState(false)
  const [, forceUpdate] = useState(0) // 디버그 로그 리렌더용
  const [selectedProduct, setSelectedProduct] = useState(DEFAULT_PRODUCTS[1].id)
  const [isPurchasing, setIsPurchasing] = useState(false)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const returnTo = location.state?.returnTo || '/'

  // 상품 목록 로드
  useEffect(() => {
    const loadProducts = async () => {
      try {
        const apiProducts = await creditService.getProducts()
        const displayProducts: ProductDisplay[] = apiProducts.map(p => ({
          ...p,
          pricePerCredit: Math.round(p.price / p.credits),
        }))
        setProducts(displayProducts)
        // 추천 상품 기본 선택
        const recommended = displayProducts.find(p => p.badge === '추천')
        if (recommended) {
          setSelectedProduct(recommended.id)
        }
      } catch (err) {
        console.error('상품 목록 로드 실패:', err)
        // 폴백 상품 사용
      }
    }
    loadProducts()
  }, [])

  // 결제 cleanup 함수 저장용 ref
  const purchaseCleanupRef = useRef<(() => void) | null>(null)

  const handlePurchase = async () => {
    if (!isAuthenticated) {
      navigate('/paywall', { state: location.state })
      return
    }

    setIsPurchasing(true)
    setError(null)

    try {
      // 개발 환경: 모의 결제
      if (import.meta.env.DEV) {
        await new Promise(resolve => setTimeout(resolve, 1500))
        // 백엔드 API 호출 (개발 환경에서도 실제 DB 기록)
        const result = await creditService.purchaseCredits(selectedProduct)
        if (result.success) {
          await refreshCredits()
          navigate(returnTo, { replace: true })
          return
        }
        throw new Error(result.message || '결제 처리 실패')
      }

      // 프로덕션: @apps-in-toss/web-framework IAP 호출
      purchaseCleanupRef.current = IAP.createOneTimePurchaseOrder({
        options: {
          sku: selectedProduct,
          processProductGrant: async ({ orderId }) => {
            try {
              // 백엔드에 결제 기록 및 이용권 충전
              const result = await creditService.purchaseCredits(selectedProduct, orderId)
              return result.success
            } catch {
              return false
            }
          },
        },
        onEvent: async () => {
          // 결제 성공
          await refreshCredits()
          setIsPurchasing(false)
          purchaseCleanupRef.current?.()
          navigate(returnTo, { replace: true })
        },
        onError: (error: unknown) => {
          // 결제 실패 또는 취소
          const errorMessage = error instanceof Error ? error.message : '결제가 취소되었습니다.'
          setError(errorMessage)
          setIsPurchasing(false)
          purchaseCleanupRef.current?.()
        },
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : '결제에 실패했습니다.')
      setIsPurchasing(false)
    }
  }

  const selected = products.find(p => p.id === selectedProduct) || products[1]

  return (
    <div style={{ minHeight: '100vh', backgroundColor: colors.gray50 }}>
      {/* 헤더 */}
      <header
        style={{
          padding: '12px 20px',
          paddingTop: 'max(env(safe-area-inset-top), 12px)',
          backgroundColor: colors.white,
          position: 'sticky',
          top: 0,
          zIndex: 100,
          borderBottom: `1px solid ${colors.gray100}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={() => navigate(-1)}
            style={{
              padding: '8px',
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              fontSize: '20px',
              color: colors.gray900,
            }}
            aria-label="뒤로가기"
          >
            ←
          </button>
          <h1 style={{
            fontSize: '18px',
            fontWeight: '600',
            margin: 0,
            color: colors.gray900,
          }}>
            이용권 구매
          </h1>
        </div>
      </header>

      <main style={{ padding: '20px' }}>
        {/* 현재 보유 이용권 */}
        <section style={{
          backgroundColor: colors.white,
          borderRadius: '16px',
          padding: '20px',
          marginBottom: '16px',
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div>
              <div style={{ fontSize: '14px', color: colors.gray500, marginBottom: '4px' }}>
                보유 이용권
              </div>
              <div style={{ fontSize: '28px', fontWeight: '700', color: colors.gray900 }}>
                {credits}건
              </div>
            </div>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: '12px',
              backgroundColor: colors.blue500 + '15',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '24px',
            }}>
              🎫
            </div>
          </div>
        </section>

        {/* 상품 선택 */}
        <section style={{ marginBottom: '20px' }}>
          <h2 style={{
            fontSize: '14px',
            fontWeight: '600',
            color: colors.gray500,
            margin: '0 0 12px 0',
          }}>
            이용권 선택
          </h2>

          {products.map(product => (
            <div
              key={product.id}
              onClick={() => setSelectedProduct(product.id)}
              role="button"
              tabIndex={0}
              style={{
                backgroundColor: colors.white,
                borderRadius: '16px',
                padding: '20px',
                marginBottom: '12px',
                border: selectedProduct === product.id
                  ? `2px solid ${colors.blue500}`
                  : `1px solid ${colors.gray100}`,
                cursor: 'pointer',
                transition: 'border-color 0.2s',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{
                      fontSize: '17px',
                      fontWeight: '600',
                      color: colors.gray900,
                    }}>
                      {product.name}
                    </span>
                    {product.badge && (
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: '600',
                        backgroundColor: product.badge === '추천' ? colors.blue500 : colors.green500,
                        color: colors.white,
                      }}>
                        {product.badge}
                      </span>
                    )}
                  </div>
                  <div style={{
                    fontSize: '13px',
                    color: colors.gray500,
                  }}>
                    건당 {product.pricePerCredit.toLocaleString()}원
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{
                    fontSize: '20px',
                    fontWeight: '700',
                    color: colors.gray900,
                  }}>
                    {product.price.toLocaleString()}원
                  </div>
                </div>
              </div>

              {/* 선택 인디케이터 */}
              <div style={{
                position: 'absolute',
                right: '20px',
                top: '50%',
                transform: 'translateY(-50%)',
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                border: selectedProduct === product.id
                  ? `2px solid ${colors.blue500}`
                  : `2px solid ${colors.gray100}`,
                backgroundColor: selectedProduct === product.id ? colors.blue500 : 'transparent',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                {selectedProduct === product.id && (
                  <span style={{ color: colors.white, fontSize: '14px' }}>✓</span>
                )}
              </div>
            </div>
          ))}
        </section>

        {/* 에러 메시지 */}
        {error && (
          <div style={{
            backgroundColor: colors.red500 + '10',
            borderRadius: '12px',
            padding: '16px',
            marginBottom: '20px',
          }}>
            <p style={{
              fontSize: '14px',
              color: colors.red500,
              margin: 0,
              textAlign: 'center',
            }}>
              {error}
            </p>
          </div>
        )}

        {/* 로그인 에러 메시지 */}
        {authError && (
          <div style={{
            backgroundColor: colors.red500 + '10',
            borderRadius: '12px',
            padding: '16px',
            marginBottom: '20px',
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

        {/* 결제 버튼 - 미로그인 시 로그인 버튼 표시 */}
        {!isAuthenticated ? (
          <button
            onClick={async () => {
              setIsLoggingIn(true)
              setError(null)
              try {
                await login()
              } catch (err) {
                // 에러는 AuthContext에서 처리됨
                console.error('로그인 실패:', err)
              } finally {
                setIsLoggingIn(false)
              }
            }}
            disabled={isLoggingIn || authLoading}
            style={{
              width: '100%',
              padding: '18px',
              borderRadius: '14px',
              border: 'none',
              backgroundColor: (isLoggingIn || authLoading) ? colors.gray100 : colors.blue500,
              color: (isLoggingIn || authLoading) ? colors.gray500 : colors.white,
              fontSize: '17px',
              fontWeight: '600',
              cursor: (isLoggingIn || authLoading) ? 'not-allowed' : 'pointer',
              minHeight: '56px',
            }}
          >
            {(isLoggingIn || authLoading) ? '로그인 중...' : '토스로 로그인하기'}
          </button>
        ) : (
          <button
            onClick={handlePurchase}
            disabled={isPurchasing}
            style={{
              width: '100%',
              padding: '18px',
              borderRadius: '14px',
              border: 'none',
              backgroundColor: isPurchasing ? colors.gray100 : colors.blue500,
              color: isPurchasing ? colors.gray500 : colors.white,
              fontSize: '17px',
              fontWeight: '600',
              cursor: isPurchasing ? 'not-allowed' : 'pointer',
              minHeight: '56px',
            }}
          >
            {isPurchasing ? '결제 중...' : `${selected.price.toLocaleString()}원 결제하기`}
          </button>
        )}

        {/* 안내 문구 */}
        <div style={{
          marginTop: '20px',
          padding: '16px',
          backgroundColor: colors.gray50,
          borderRadius: '12px',
        }}>
          <p style={{
            fontSize: '13px',
            color: colors.gray500,
            margin: 0,
            lineHeight: '1.6',
          }}>
            • 이용권은 구매 후 1년간 유효합니다<br />
            • 한 번 조회한 기업은 추가 차감 없이 재조회 가능합니다<br />
            • 결제 관련 문의: support@raymondsrisk.com
          </p>
        </div>

        {/* 디버그 패널 토글 버튼 */}
        <div style={{ marginTop: '20px', textAlign: 'center' }}>
          <button
            onClick={() => {
              setShowDebug(!showDebug)
              forceUpdate(n => n + 1)
            }}
            style={{
              padding: '8px 16px',
              fontSize: '12px',
              backgroundColor: colors.gray100,
              border: 'none',
              borderRadius: '8px',
              color: colors.gray600,
            }}
          >
            {showDebug ? '디버그 숨기기' : '디버그 보기'}
          </button>
        </div>

        {/* 디버그 로그 패널 */}
        {showDebug && (
          <div style={{
            marginTop: '12px',
            padding: '12px',
            backgroundColor: '#1a1a2e',
            borderRadius: '8px',
            maxHeight: '300px',
            overflowY: 'auto',
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
              <div>isAuthenticated: {String(isAuthenticated)}</div>
              <div>authLoading: {String(authLoading)}</div>
              <div>authError: {authError || 'null'}</div>
              <div>credits: {credits}</div>
              <div style={{ marginTop: '8px', marginBottom: '8px', color: '#ffff00' }}>
                === 디버그 로그 ===
              </div>
              {debugLogs.length === 0 ? (
                <div style={{ color: '#888' }}>(로그 없음 - 로그인 버튼을 누르면 로그가 표시됩니다)</div>
              ) : (
                debugLogs.map((log, i) => (
                  <div key={i} style={{ marginBottom: '2px' }}>{log}</div>
                ))
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

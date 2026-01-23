import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { IAP } from '@apps-in-toss/web-framework'
import { useAuth } from '../contexts/AuthContext'
import '../types/auth' // 전역 타입 선언 import
import * as creditService from '../services/creditService'
import type { CreditProduct } from '../services/creditService'
import { colors } from '../constants/colors'

// ============================================================================
// 환경 감지 유틸리티
// ============================================================================

/**
 * 샌드박스 환경 여부 감지
 * - 개발 모드 (localhost)
 * - 샌드박스 앱 (userAgent 또는 referrer로 판단)
 */
function isSandboxEnvironment(): boolean {
  // 개발 환경
  if (import.meta.env.DEV) return true

  // 브라우저 환경에서 샌드박스 감지
  if (typeof window !== 'undefined') {
    const userAgent = navigator.userAgent.toLowerCase()
    const referrer = document.referrer.toLowerCase()

    // 샌드박스 앱 감지 패턴
    if (userAgent.includes('sandbox') || userAgent.includes('debug')) return true
    if (referrer.includes('sandbox') || referrer.includes('localhost')) return true

    // 로컬 개발 서버
    if (window.location.hostname === 'localhost') return true
    if (window.location.hostname.startsWith('192.168.')) return true
  }

  return false
}

/**
 * 토스 앱 내부 환경 여부 감지
 */
function isInTossApp(): boolean {
  if (typeof window === 'undefined') return false

  const userAgent = navigator.userAgent.toLowerCase()
  // 토스 앱 WebView 감지
  return userAgent.includes('toss') || userAgent.includes('apps-in-toss')
}

// ============================================================================
// SKU 매핑 (대소문자 및 형식 통일)
// ============================================================================

/**
 * SKU ID 표준화 함수
 * - 로컬 상품 ID를 앱인토스 콘솔에서 등록한 SKU로 변환
 * - 앱인토스 콘솔은 자동 생성된 긴 형식의 SKU 사용
 */
function normalizeSkuId(localId: string): string {
  // 앱인토스 콘솔에 등록된 실제 SKU (2026-01-13 확인)
  const skuMapping: Record<string, string> = {
    'report_10': 'ait.0000016607.492ec06a.bd18e74b63.8287319702',      // 10회 이용권
    'report_30': 'ait.0000016607.fb16c160.4943bb7107.8287358161',      // 30회 이용권
    'report_unlimited': 'ait.0000016607.fb16c160.beb36e9854.8287409873', // 1개월 무제한 이용권
  }

  return skuMapping[localId] || localId
}

// ============================================================================
// 상품 정의
// ============================================================================

// 기본 상품 목록 (API 실패 시 폴백) - 2026-01-09 가격 개편
const DEFAULT_PRODUCTS: ProductDisplay[] = [
  {
    id: 'report_10',
    name: '리포트 10건',
    credits: 10,
    price: 1000,
    pricePerCredit: 100,
    badge: null,
  },
  {
    id: 'report_30',
    name: '리포트 30건',
    credits: 30,
    price: 3000,
    pricePerCredit: 100,
    badge: '추천',
  },
  {
    id: 'report_unlimited',
    name: '무제한 이용권',
    credits: -1,  // -1 = 무제한
    price: 10000,
    pricePerCredit: 0,  // 무제한이므로 건당 가격 없음
    badge: 'BEST',
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
          // 무제한(-1)일 때는 건당 가격 0으로 설정
          pricePerCredit: p.credits === -1 ? 0 : Math.round(p.price / p.credits),
        }))
        setProducts(displayProducts)
        // 추천 상품 기본 선택
        const recommended = displayProducts.find(p => p.badge === '추천')
        if (recommended) {
          setSelectedProduct(recommended.id)
        }
      } catch {
        // 폴백 상품 사용
      }
    }
    loadProducts()
  }, [])

  // 미결 주문 처리 (앱 시작 시)
  // Apps-in-Toss SDK 1.2.2+ 권장: 결제 완료 후 앱 종료 등으로 상품 지급이 완료되지 않은 주문 복원
  useEffect(() => {
    const handlePendingOrders = async () => {
      // 토스 앱 내부가 아니면 건너뛰기
      if (!isInTossApp()) {
        console.log('[PurchasePage] 토스 앱 외부 - 미결 주문 처리 건너뛰기')
        return
      }

      try {
        console.log('[PurchasePage] 미결 주문 확인 중...')
        const pendingResult = await IAP.getPendingOrders()
        const pendingOrders = pendingResult?.orders || []

        if (pendingOrders.length === 0) {
          console.log('[PurchasePage] 미결 주문 없음')
          return
        }

        console.log('[PurchasePage] 미결 주문 발견:', pendingOrders.length, '건')

        for (const order of pendingOrders) {
          try {
            console.log('[PurchasePage] 미결 주문 처리 중:', order.orderId)

            // 백엔드에서 이미 처리됐는지 확인 (중복 방지)
            // 주문이 이미 DB에 있으면 completeProductGrant만 호출
            try {
              // 상품 지급 시도 (이미 지급됐으면 409 에러)
              await creditService.purchaseCredits(order.sku, order.orderId)
              console.log('[PurchasePage] 미결 주문 상품 지급 완료:', order.orderId)
            } catch (err) {
              // 이미 처리된 주문이면 (409 Conflict) 무시
              console.log('[PurchasePage] 미결 주문 이미 처리됨 (또는 에러):', order.orderId, err)
            }

            // SDK에 상품 지급 완료 알림
            await IAP.completeProductGrant({ params: { orderId: order.orderId } })
            console.log('[PurchasePage] completeProductGrant 호출 완료:', order.orderId)

            // 잔액 새로고침
            await refreshCredits()
          } catch (err) {
            console.error('[PurchasePage] 미결 주문 처리 실패:', order.orderId, err)
          }
        }
      } catch (err) {
        console.error('[PurchasePage] 미결 주문 조회 실패:', err)
      }
    }

    if (isAuthenticated) {
      handlePendingOrders()
    }
  }, [isAuthenticated, refreshCredits])

  // 결제 cleanup 함수 저장용 ref
  const purchaseCleanupRef = useRef<(() => void) | null>(null)

  // 환경 상태 계산
  const isSandbox = isSandboxEnvironment()
  const inTossApp = isInTossApp()

  const handlePurchase = async () => {
    if (!isAuthenticated) {
      navigate('/paywall', { state: location.state })
      return
    }

    // 샌드박스 환경에서 IAP 사용 시 경고
    if (isSandbox && !import.meta.env.DEV) {
      setError('샌드박스 환경에서는 실제 결제가 지원되지 않습니다. 토스 앱에서 테스트해주세요.')
      return
    }

    setIsPurchasing(true)
    setError(null)

    // SKU를 앱인토스 콘솔 형식으로 정규화
    const normalizedSku = normalizeSkuId(selectedProduct)
    console.log('[PurchasePage] SKU 정규화:', selectedProduct, '->', normalizedSku)

    try {
      // 개발 환경 또는 샌드박스: 모의 결제
      if (import.meta.env.DEV || (isSandbox && !inTossApp)) {
        console.log('[PurchasePage] 개발/샌드박스 환경 - 모의 결제 진행')
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

      // 프로덕션 (토스 앱 내부): @apps-in-toss/web-framework IAP 호출
      console.log('[PurchasePage] 프로덕션 환경 - IAP 결제 시작, SKU:', normalizedSku)
      purchaseCleanupRef.current = IAP.createOneTimePurchaseOrder({
        options: {
          sku: normalizedSku,  // 정규화된 SKU 사용
          processProductGrant: async ({ orderId }) => {
            // SDK 1.1.3+ 스펙: async 함수로 실제 상품 지급 결과 반환
            console.log('[PurchasePage] processProductGrant 호출됨, orderId:', orderId)

            try {
              // 백엔드 API 호출하여 이용권 충전
              const result = await creditService.purchaseCredits(selectedProduct, orderId)
              console.log('[PurchasePage] 백엔드 응답:', JSON.stringify(result))

              if (result.success) {
                console.log('[PurchasePage] 이용권 충전 성공')
                return true
              } else {
                console.error('[PurchasePage] 이용권 충전 실패:', result.message)
                return false  // SDK에 실패 알림 → PRODUCT_NOT_GRANTED_BY_PARTNER 에러
              }
            } catch (err) {
              console.error('[PurchasePage] 백엔드 API 오류:', err)
              return false  // SDK에 실패 알림
            }
          },
        },
        onEvent: async (event: unknown) => {
          // 결제 이벤트 수신
          console.log('[PurchasePage] onEvent 수신:', JSON.stringify(event))
          // SDK 문서: event.type === 'success' 일 때 결제 성공
          await refreshCredits()
          setIsPurchasing(false)
          purchaseCleanupRef.current?.()
          navigate(returnTo, { replace: true })
        },
        onError: (error: unknown) => {
          // 결제 실패 또는 취소
          console.error('[PurchasePage] onError 수신:', error)
          const errorMessage = error instanceof Error ? error.message : '결제가 취소되었습니다.'
          setError(errorMessage)
          setIsPurchasing(false)
          purchaseCleanupRef.current?.()
        },
      })
    } catch (err) {
      console.error('[PurchasePage] 결제 처리 예외:', err)
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
        {/* 샌드박스/개발 환경 안내 배너 */}
        {(isSandbox || import.meta.env.DEV) && (
          <div style={{
            backgroundColor: '#FEF3C7',
            border: '1px solid #F59E0B',
            borderRadius: '12px',
            padding: '16px',
            marginBottom: '16px',
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
            }}>
              <span style={{ fontSize: '20px' }}>⚠️</span>
              <div>
                <div style={{
                  fontWeight: '600',
                  color: '#92400E',
                  marginBottom: '4px',
                  fontSize: '14px',
                }}>
                  {import.meta.env.DEV ? '개발 환경' : '샌드박스 환경'}
                </div>
                <p style={{
                  fontSize: '13px',
                  color: '#B45309',
                  margin: 0,
                  lineHeight: '1.5',
                }}>
                  {import.meta.env.DEV
                    ? '개발 환경에서는 모의 결제가 진행됩니다. 실제 결제는 토스 앱에서만 가능합니다.'
                    : '샌드박스에서는 인앱 결제가 지원되지 않습니다. 실제 결제를 위해서는 토스 앱에서 테스트하세요.'
                  }
                </p>
                {!import.meta.env.DEV && (
                  <p style={{
                    fontSize: '12px',
                    color: '#92400E',
                    margin: '8px 0 0 0',
                    fontStyle: 'italic',
                  }}>
                    환경: {inTossApp ? '토스앱 내부' : '외부 브라우저'}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

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
                {credits === -1 ? '무제한' : `${credits}건`}
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
                    {product.credits === -1 ? '무제한 조회' : `건당 ${product.pricePerCredit.toLocaleString()}원`}
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
              } catch {
                // 에러는 AuthContext에서 처리됨
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

      </main>
    </div>
  )
}

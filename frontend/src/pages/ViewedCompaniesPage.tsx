import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { getViewHistory, type ViewHistoryItem, type ViewHistoryResponse } from '../api/company'
import { MarketBadge } from '../components/common'
import axios from 'axios'

function ViewedCompaniesPage() {
  const navigate = useNavigate()
  const { isAuthenticated, user } = useAuthStore()

  const [viewHistory, setViewHistory] = useState<ViewHistoryItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<{ message: string; code: string } | null>(null)
  const [page, setPage] = useState(1)
  const [totalItems, setTotalItems] = useState(0)
  const pageSize = 20

  // trial 30일 이내 여부 확인
  const isTrialValid = useCallback(() => {
    if (!user) return false
    if (user.subscription_tier !== 'trial') return true
    if (!user.created_at) return false

    const createdAt = new Date(user.created_at)
    const thirtyDaysLater = new Date(createdAt.getTime() + 30 * 24 * 60 * 60 * 1000)
    return new Date() <= thirtyDaysLater
  }, [user])

  // trial 남은 일수 계산
  const getTrialRemainingDays = useCallback(() => {
    if (!user || user.subscription_tier !== 'trial' || !user.created_at) return 0

    const createdAt = new Date(user.created_at)
    const thirtyDaysLater = new Date(createdAt.getTime() + 30 * 24 * 60 * 60 * 1000)
    const now = new Date()
    const diffTime = thirtyDaysLater.getTime() - now.getTime()
    return Math.max(0, Math.ceil(diffTime / (1000 * 60 * 60 * 24)))
  }, [user])

  // 조회 기록 로드
  const loadViewHistory = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response: ViewHistoryResponse = await getViewHistory(page, pageSize)
      setViewHistory(response.items)
      setTotalItems(response.total)
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        const detail = err.response.data.detail
        setError({
          message: detail.message || '조회 기록을 불러오는데 실패했습니다',
          code: detail.code || 'UNKNOWN',
        })
      } else {
        setError({
          message: '조회 기록을 불러오는데 실패했습니다',
          code: 'UNKNOWN',
        })
      }
    } finally {
      setIsLoading(false)
    }
  }, [page])

  // 로그인 안 된 경우 리다이렉트
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: '/viewed-companies' } })
    }
  }, [isAuthenticated, navigate])

  // 데이터 로드
  useEffect(() => {
    if (isAuthenticated) {
      loadViewHistory()
    }
  }, [isAuthenticated, loadViewHistory])

  // 회사 클릭 핸들러
  const handleCompanyClick = (companyId: string) => {
    navigate(`/company/${companyId}/graph`)
  }

  // 날짜 포맷
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  // 페이지 개수 계산
  const totalPages = Math.ceil(totalItems / pageSize)

  // 에러 상태 렌더링
  if (error) {
    return (
      <div className="min-h-[calc(100vh-200px)] flex flex-col items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gray-800 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 15v2m0 0v2m0-2h2m-2 0H10m4-6V9a4 4 0 10-8 0v4a2 2 0 002 2h4a2 2 0 002-2z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">{error.message}</h2>
          {error.code === 'FREE_USER' && (
            <p className="text-gray-400 mb-6">
              조회한 기업 목록은 유료 회원 전용 기능입니다.
              <br />
              이용권을 구매하시면 이용하실 수 있습니다.
            </p>
          )}
          {error.code === 'TRIAL_EXPIRED' && (
            <p className="text-gray-400 mb-6">
              체험 기간이 만료되었습니다.
              <br />
              계속 이용하시려면 이용권을 구매해 주세요.
            </p>
          )}
          {error.code === 'SUBSCRIPTION_EXPIRED' && (
            <p className="text-gray-400 mb-6">
              이용권 기간이 만료되었습니다.
              <br />
              계속 이용하시려면 이용권을 갱신해 주세요.
            </p>
          )}
          <button
            onClick={() => navigate('/pricing')}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            이용권 보기
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-200px)] py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* 헤더 */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white mb-2">조회한 기업</h1>
          <p className="text-gray-400">최근 조회한 기업 목록입니다</p>
        </div>

        {/* Trial 안내 배너 */}
        {user?.subscription_tier === 'trial' && isTrialValid() && (
          <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <div className="flex items-center gap-2 text-blue-400">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span className="font-medium">
                1회 이용권은 가입일로부터 30일간 유효합니다 (남은 기간: {getTrialRemainingDays()}일)
              </span>
            </div>
          </div>
        )}

        {/* 로딩 상태 */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
            <p className="text-gray-400">조회 기록을 불러오는 중...</p>
          </div>
        ) : viewHistory.length === 0 ? (
          /* 빈 상태 */
          <div className="text-center py-16">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gray-800 flex items-center justify-center">
              <svg
                className="w-8 h-8 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-white mb-2">조회 기록이 없습니다</h3>
            <p className="text-gray-400 mb-6">기업을 검색하고 관계도를 조회해 보세요</p>
            <button
              onClick={() => navigate('/')}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              기업 검색하기
            </button>
          </div>
        ) : (
          /* 조회 기록 목록 */
          <>
            <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">기업명</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">종목코드</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">시장</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">조회일시</th>
                  </tr>
                </thead>
                <tbody>
                  {viewHistory.map((item) => (
                    <tr
                      key={item.id}
                      onClick={() => handleCompanyClick(item.company_id)}
                      className="border-b border-gray-800 last:border-b-0 hover:bg-gray-800/50 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3">
                        <span className="text-white font-medium">
                          {item.company_name || '-'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-400 font-mono">
                        {item.ticker || '-'}
                      </td>
                      <td className="px-4 py-3">
                        {item.market ? (
                          <MarketBadge market={item.market} />
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-sm">
                        {formatDate(item.viewed_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* 페이지네이션 */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-6">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-2 rounded-lg border border-gray-700 text-gray-400 hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  이전
                </button>
                <span className="px-4 py-2 text-gray-400">
                  {page} / {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-2 rounded-lg border border-gray-700 text-gray-400 hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  다음
                </button>
              </div>
            )}

            {/* 총 개수 */}
            <p className="text-center text-sm text-gray-500 mt-4">
              총 {totalItems}건의 조회 기록
            </p>
          </>
        )}
      </div>
    </div>
  )
}

export default ViewedCompaniesPage

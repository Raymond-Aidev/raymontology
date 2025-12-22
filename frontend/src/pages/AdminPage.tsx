import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import apiClient from '../api/client'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'

interface User {
  id: string
  email: string
  username: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
  oauth_provider: string | null
  created_at: string
  last_login: string | null
}

interface Stats {
  total_users: number
  active_users: number
  oauth_users: number
  superusers: number
}

type TabType = 'users' | 'terms' | 'privacy'

function AdminPage() {
  const navigate = useNavigate()
  const { user, isAuthenticated } = useAuthStore()

  const [activeTab, setActiveTab] = useState<TabType>('users')
  const [users, setUsers] = useState<User[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [termsContent, setTermsContent] = useState('')
  const [privacyContent, setPrivacyContent] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // 관리자 권한 체크
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login')
      return
    }
    if (user && !user.is_superuser) {
      navigate('/')
      return
    }
  }, [isAuthenticated, user, navigate])

  // 데이터 로드
  const loadData = useCallback(async () => {
    if (!user?.is_superuser) return

    setIsLoading(true)
    setError(null)

    try {
      // 병렬로 데이터 로드
      const [usersRes, statsRes, termsRes, privacyRes] = await Promise.all([
        apiClient.get('/api/admin/users'),
        apiClient.get('/api/admin/stats'),
        apiClient.get('/api/admin/settings/terms'),
        apiClient.get('/api/admin/settings/privacy')
      ])

      setUsers(usersRes.data.users)
      setStats(statsRes.data)
      setTermsContent(termsRes.data.value || '')
      setPrivacyContent(privacyRes.data.value || '')
    } catch (err) {
      console.error('Failed to load admin data:', err)
      setError('데이터를 불러오는데 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }, [user])

  useEffect(() => {
    loadData()
  }, [loadData])

  // 설정 저장
  const handleSaveSetting = async (key: 'terms' | 'privacy') => {
    setIsSaving(true)
    setSaveSuccess(null)
    setError(null)

    try {
      await apiClient.put('/api/admin/settings', {
        key,
        value: key === 'terms' ? termsContent : privacyContent
      })
      setSaveSuccess(`${key === 'terms' ? '이용약관' : '개인정보처리방침'}이 저장되었습니다.`)
      setTimeout(() => setSaveSuccess(null), 3000)
    } catch (err) {
      console.error('Failed to save setting:', err)
      setError('저장에 실패했습니다.')
    } finally {
      setIsSaving(false)
    }
  }

  // 사용자 활성화/비활성화 토글
  const handleToggleUserActive = async (userId: string) => {
    try {
      await apiClient.patch(`/api/admin/users/${userId}/toggle-active`)
      // 목록 새로고침
      const usersRes = await apiClient.get('/api/admin/users')
      setUsers(usersRes.data.users)
    } catch (err) {
      console.error('Failed to toggle user:', err)
      setError('사용자 상태 변경에 실패했습니다.')
    }
  }

  if (!user?.is_superuser) {
    return null
  }

  return (
    <div className="min-h-screen bg-theme-bg">
      {/* Header */}
      <header className="bg-dark-surface/80 backdrop-blur-xl border-b border-dark-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-4">
              <RaymondsRiskLogo size="sm" variant="compact" />
              <div className="flex items-center gap-2">
                <span className="px-2 py-1 text-xs font-medium bg-accent-primary/20 text-accent-primary rounded">
                  관리자
                </span>
              </div>
            </div>
            <button
              onClick={() => navigate('/')}
              className="px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary hover:bg-dark-hover rounded-lg transition-colors"
            >
              메인으로
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 통계 카드 */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-theme-card border border-theme-border rounded-xl p-4">
              <p className="text-sm text-text-secondary">전체 회원</p>
              <p className="text-2xl font-bold text-text-primary">{stats.total_users}</p>
            </div>
            <div className="bg-theme-card border border-theme-border rounded-xl p-4">
              <p className="text-sm text-text-secondary">활성 회원</p>
              <p className="text-2xl font-bold text-accent-success">{stats.active_users}</p>
            </div>
            <div className="bg-theme-card border border-theme-border rounded-xl p-4">
              <p className="text-sm text-text-secondary">OAuth 가입</p>
              <p className="text-2xl font-bold text-accent-primary">{stats.oauth_users}</p>
            </div>
            <div className="bg-theme-card border border-theme-border rounded-xl p-4">
              <p className="text-sm text-text-secondary">관리자</p>
              <p className="text-2xl font-bold text-accent-warning">{stats.superusers}</p>
            </div>
          </div>
        )}

        {/* 탭 */}
        <div className="flex gap-2 mb-6 border-b border-theme-border">
          {[
            { id: 'users', label: '회원 관리' },
            { id: 'terms', label: '이용약관' },
            { id: 'privacy', label: '개인정보처리방침' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-accent-primary text-accent-primary'
                  : 'border-transparent text-text-secondary hover:text-text-primary'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 에러/성공 메시지 */}
        {error && (
          <div className="mb-4 p-4 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
            <p className="text-sm text-accent-danger">{error}</p>
          </div>
        )}
        {saveSuccess && (
          <div className="mb-4 p-4 bg-accent-success/10 border border-accent-success/30 rounded-lg">
            <p className="text-sm text-accent-success">{saveSuccess}</p>
          </div>
        )}

        {/* 로딩 */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-4 border-accent-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <>
            {/* 회원 관리 탭 */}
            {activeTab === 'users' && (
              <div className="bg-theme-card border border-theme-border rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-theme-surface">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">이메일</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">이름</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">가입방식</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">가입일</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">마지막 로그인</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">상태</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">액션</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-theme-border">
                      {users.map((u) => (
                        <tr key={u.id} className="hover:bg-theme-hover transition-colors">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-text-primary">{u.email}</span>
                              {u.is_superuser && (
                                <span className="px-1.5 py-0.5 text-xs bg-accent-warning/20 text-accent-warning rounded">
                                  관리자
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-text-secondary">
                            {u.full_name || u.username}
                          </td>
                          <td className="px-4 py-3">
                            {u.oauth_provider ? (
                              <span className={`px-2 py-0.5 text-xs rounded ${
                                u.oauth_provider === 'google'
                                  ? 'bg-blue-500/20 text-blue-400'
                                  : 'bg-yellow-500/20 text-yellow-400'
                              }`}>
                                {u.oauth_provider}
                              </span>
                            ) : (
                              <span className="text-xs text-text-muted">이메일</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm text-text-secondary">
                            {new Date(u.created_at).toLocaleDateString('ko-KR')}
                          </td>
                          <td className="px-4 py-3 text-sm text-text-secondary">
                            {u.last_login
                              ? new Date(u.last_login).toLocaleDateString('ko-KR')
                              : '-'}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-0.5 text-xs rounded ${
                              u.is_active
                                ? 'bg-accent-success/20 text-accent-success'
                                : 'bg-accent-danger/20 text-accent-danger'
                            }`}>
                              {u.is_active ? '활성' : '비활성'}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            {!u.is_superuser && (
                              <button
                                onClick={() => handleToggleUserActive(u.id)}
                                className={`px-2 py-1 text-xs rounded transition-colors ${
                                  u.is_active
                                    ? 'bg-accent-danger/10 text-accent-danger hover:bg-accent-danger/20'
                                    : 'bg-accent-success/10 text-accent-success hover:bg-accent-success/20'
                                }`}
                              >
                                {u.is_active ? '비활성화' : '활성화'}
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {users.length === 0 && (
                  <div className="p-8 text-center text-text-secondary">
                    등록된 회원이 없습니다.
                  </div>
                )}
              </div>
            )}

            {/* 이용약관 탭 */}
            {activeTab === 'terms' && (
              <div className="bg-theme-card border border-theme-border rounded-xl p-6">
                <div className="mb-4">
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    이용약관 내용 (Markdown 지원)
                  </label>
                  <textarea
                    value={termsContent}
                    onChange={(e) => setTermsContent(e.target.value)}
                    rows={20}
                    className="w-full px-4 py-3 bg-theme-surface border border-theme-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/30 focus:border-accent-primary font-mono text-sm"
                    placeholder="# 이용약관&#10;&#10;내용을 입력하세요..."
                  />
                </div>
                <div className="flex justify-end">
                  <button
                    onClick={() => handleSaveSetting('terms')}
                    disabled={isSaving}
                    className={`px-6 py-2.5 rounded-lg font-medium text-white transition-colors ${
                      isSaving
                        ? 'bg-accent-primary/50 cursor-not-allowed'
                        : 'bg-accent-primary hover:bg-accent-primary/90'
                    }`}
                  >
                    {isSaving ? '저장 중...' : '저장'}
                  </button>
                </div>
              </div>
            )}

            {/* 개인정보처리방침 탭 */}
            {activeTab === 'privacy' && (
              <div className="bg-theme-card border border-theme-border rounded-xl p-6">
                <div className="mb-4">
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    개인정보처리방침 내용 (Markdown 지원)
                  </label>
                  <textarea
                    value={privacyContent}
                    onChange={(e) => setPrivacyContent(e.target.value)}
                    rows={20}
                    className="w-full px-4 py-3 bg-theme-surface border border-theme-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/30 focus:border-accent-primary font-mono text-sm"
                    placeholder="# 개인정보처리방침&#10;&#10;내용을 입력하세요..."
                  />
                </div>
                <div className="flex justify-end">
                  <button
                    onClick={() => handleSaveSetting('privacy')}
                    disabled={isSaving}
                    className={`px-6 py-2.5 rounded-lg font-medium text-white transition-colors ${
                      isSaving
                        ? 'bg-accent-primary/50 cursor-not-allowed'
                        : 'bg-accent-primary hover:bg-accent-primary/90'
                    }`}
                  >
                    {isSaving ? '저장 중...' : '저장'}
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default AdminPage

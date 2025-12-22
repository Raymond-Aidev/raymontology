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
  const { user, isAuthenticated, login } = useAuthStore()

  // 로그인 상태
  const [showLogin, setShowLogin] = useState(false)
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  // 관리자 페이지 상태
  const [activeTab, setActiveTab] = useState<TabType>('users')
  const [users, setUsers] = useState<User[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [termsContent, setTermsContent] = useState('')
  const [privacyContent, setPrivacyContent] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // 로그인 여부 및 관리자 권한 체크
  useEffect(() => {
    if (!isAuthenticated) {
      setShowLogin(true)
      setIsLoading(false)
      return
    }
    if (user && !user.is_superuser) {
      // 관리자가 아니면 메인으로
      navigate('/')
      return
    }
    setShowLogin(false)
  }, [isAuthenticated, user, navigate])

  // 관리자 로그인 처리
  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoginError(null)
    setIsLoggingIn(true)

    try {
      await login({ email: loginEmail, password: loginPassword })
      // 로그인 성공 후 관리자 권한 체크는 useEffect에서 처리
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setLoginError(error.response?.data?.detail || '로그인에 실패했습니다.')
    } finally {
      setIsLoggingIn(false)
    }
  }

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
    if (user?.is_superuser) {
      loadData()
    }
  }, [loadData, user])

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

  // 로그인 폼 표시
  if (showLogin) {
    return (
      <div className="min-h-screen bg-theme-bg flex flex-col">
        {/* Header */}
        <header className="bg-dark-surface/80 backdrop-blur-xl border-b border-dark-border">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-center h-14">
              <RaymondsRiskLogo size="sm" variant="compact" />
            </div>
          </div>
        </header>

        {/* Login Form */}
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="w-full max-w-md">
            <div className="bg-theme-card border border-theme-border rounded-2xl p-8">
              <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-accent-primary/10 rounded-full mb-4">
                  <svg className="w-8 h-8 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <h1 className="text-2xl font-bold text-text-primary">관리자 로그인</h1>
                <p className="text-sm text-text-secondary mt-2">관리자 계정으로 로그인하세요</p>
              </div>

              <form onSubmit={handleAdminLogin} className="space-y-5">
                {loginError && (
                  <div className="p-4 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
                    <p className="text-sm text-accent-danger">{loginError}</p>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    이메일
                  </label>
                  <input
                    type="email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    placeholder="admin@example.com"
                    className="w-full px-4 py-3 bg-theme-surface border border-theme-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/30 focus:border-accent-primary transition-all"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    비밀번호
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      placeholder="비밀번호 입력"
                      className="w-full px-4 py-3 bg-theme-surface border border-theme-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/30 focus:border-accent-primary transition-all pr-12"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-text-muted hover:text-text-secondary transition-colors"
                    >
                      {showPassword ? (
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                        </svg>
                      ) : (
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoggingIn || !loginEmail || !loginPassword}
                  className={`w-full py-3 rounded-lg font-medium text-white transition-all ${
                    isLoggingIn || !loginEmail || !loginPassword
                      ? 'bg-accent-primary/50 cursor-not-allowed'
                      : 'bg-accent-primary hover:bg-accent-primary/90'
                  }`}
                >
                  {isLoggingIn ? '로그인 중...' : '로그인'}
                </button>
              </form>

              <div className="mt-6 text-center">
                <button
                  onClick={() => navigate('/')}
                  className="text-sm text-text-secondary hover:text-text-primary transition-colors"
                >
                  메인으로 돌아가기
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
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

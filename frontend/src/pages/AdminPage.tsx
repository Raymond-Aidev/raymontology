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
  subscription_tier: string
  subscription_expires_at: string | null
  created_at: string
  last_login: string | null
}

type SubscriptionTier = 'free' | 'light' | 'max'

const TIER_LABELS: Record<SubscriptionTier, string> = {
  free: '무료',
  light: '라이트',
  max: '맥스'
}

const TIER_COLORS: Record<SubscriptionTier, string> = {
  free: 'bg-gray-500/20 text-gray-400',
  light: 'bg-blue-500/20 text-blue-400',
  max: 'bg-purple-500/20 text-purple-400'
}

const TIER_PRICES: Record<SubscriptionTier, string> = {
  free: '무료',
  light: '3,000원/월',
  max: '30,000원/월'
}

interface Stats {
  total_users: number
  active_users: number
  oauth_users: number
  superusers: number
}

type TabType = 'users' | 'database' | 'content' | 'terms' | 'privacy' | 'dataQuality'

interface ContentField {
  field: string
  type: 'text' | 'image'
  default: string
  recommended_size?: {
    width: number
    height: number
    label: string
  }
}

interface ContentSection {
  page: string
  section: string
  fields: ContentField[]
}

interface PageContent {
  [section: string]: {
    [field: string]: string
  }
}

// 데이터베이스 현황 타입
interface TableStats {
  name: string
  display_name: string
  record_count: number
  description: string
  category: string
}

interface DatabaseOverview {
  total_tables: number
  total_records: number
  tables: TableStats[]
  last_updated: string
}

// 데이터 품질 모니터링 타입
interface DataQualityIssue {
  issue_type: string
  description: string
  record_count: number
  company_count: number
  severity: 'critical' | 'warning' | 'info'
  sample_data?: Array<Record<string, unknown>>
}

interface TableQualityStats {
  table_name: string
  total_records: number
  issues: DataQualityIssue[]
  quality_score: number
  last_checked: string
}

interface DataQualityResponse {
  overall_score: number
  tables: TableQualityStats[]
  summary: {
    critical: number
    warning: number
    info: number
  }
}

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

  // 이용권 관리 모달 상태
  const [subscriptionModal, setSubscriptionModal] = useState<{
    isOpen: boolean
    user: User | null
  }>({ isOpen: false, user: null })
  const [selectedTier, setSelectedTier] = useState<SubscriptionTier>('free')
  const [selectedDuration, setSelectedDuration] = useState<number | null>(null) // null = 무기한
  const [isUpdatingSubscription, setIsUpdatingSubscription] = useState(false)

  // 콘텐츠 관리 상태
  const [contentSections, setContentSections] = useState<ContentSection[]>([])
  const [pageContent, setPageContent] = useState<PageContent>({})
  const [editingField, setEditingField] = useState<{section: string, field: string, value: string} | null>(null)
  const [uploadingImage, setUploadingImage] = useState<string | null>(null)

  // 데이터베이스 현황 상태
  const [databaseOverview, setDatabaseOverview] = useState<DatabaseOverview | null>(null)
  const [databaseLoading, setDatabaseLoading] = useState(false)

  // 데이터 품질 모니터링 상태
  const [dataQuality, setDataQuality] = useState<DataQualityResponse | null>(null)
  const [dataQualityLoading, setDataQualityLoading] = useState(false)
  const [cleanupLoading, setCleanupLoading] = useState<string | null>(null)

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

  // 콘텐츠 데이터 로드
  const loadContentData = useCallback(async () => {
    try {
      const [sectionsRes, contentRes] = await Promise.all([
        apiClient.get('/api/content/admin/sections'),
        apiClient.get('/api/content/about')
      ])
      setContentSections(sectionsRes.data.sections || [])
      setPageContent(contentRes.data.content || {})
    } catch (err) {
      console.error('Failed to load content data:', err)
    }
  }, [])

  // 콘텐츠 필드 업데이트
  const handleUpdateContent = async (section: string, field: string, value: string) => {
    setIsSaving(true)
    setError(null)
    try {
      await apiClient.put(`/api/content/about/${section}/${field}`, { value })
      setPageContent(prev => ({
        ...prev,
        [section]: {
          ...prev[section],
          [field]: value
        }
      }))
      setSaveSuccess('저장되었습니다.')
      setTimeout(() => setSaveSuccess(null), 3000)
      setEditingField(null)
    } catch (err) {
      console.error('Failed to update content:', err)
      setError('저장에 실패했습니다.')
    } finally {
      setIsSaving(false)
    }
  }

  // 이미지 업로드
  const handleImageUpload = async (section: string, file: File) => {
    setUploadingImage(section)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await apiClient.post(`/api/content/about/${section}/image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setPageContent(prev => ({
        ...prev,
        [section]: {
          ...prev[section],
          image: response.data.image_url
        }
      }))
      setSaveSuccess('이미지가 업로드되었습니다.')
      setTimeout(() => setSaveSuccess(null), 3000)
    } catch (err) {
      console.error('Failed to upload image:', err)
      setError('이미지 업로드에 실패했습니다.')
    } finally {
      setUploadingImage(null)
    }
  }

  // 이미지 삭제
  const handleDeleteImage = async (section: string) => {
    if (!confirm('이미지를 삭제하시겠습니까?')) return
    try {
      await apiClient.delete(`/api/content/about/${section}/image`)
      setPageContent(prev => ({
        ...prev,
        [section]: {
          ...prev[section],
          image: ''
        }
      }))
      setSaveSuccess('이미지가 삭제되었습니다.')
      setTimeout(() => setSaveSuccess(null), 3000)
    } catch (err) {
      console.error('Failed to delete image:', err)
      setError('이미지 삭제에 실패했습니다.')
    }
  }

  // 콘텐츠 탭 전환 시 데이터 로드
  useEffect(() => {
    if (activeTab === 'content' && user?.is_superuser) {
      loadContentData()
    }
  }, [activeTab, user, loadContentData])

  // 데이터베이스 현황 로드
  const loadDatabaseOverview = useCallback(async () => {
    setDatabaseLoading(true)
    try {
      const response = await apiClient.get('/api/admin/database-overview')
      setDatabaseOverview(response.data)
    } catch (err) {
      console.error('Failed to load database overview:', err)
      setError('데이터베이스 현황을 불러오는데 실패했습니다.')
    } finally {
      setDatabaseLoading(false)
    }
  }, [])

  // 데이터베이스 탭 전환 시 로드
  useEffect(() => {
    if (activeTab === 'database' && user?.is_superuser) {
      loadDatabaseOverview()
    }
  }, [activeTab, user, loadDatabaseOverview])

  // 데이터 품질 로드
  const loadDataQuality = useCallback(async () => {
    setDataQualityLoading(true)
    try {
      const response = await apiClient.get('/api/admin/data-quality')
      setDataQuality(response.data)
    } catch (err) {
      console.error('Failed to load data quality:', err)
      setError('데이터 품질 정보를 불러오는데 실패했습니다.')
    } finally {
      setDataQualityLoading(false)
    }
  }, [])

  // 데이터 품질 탭 전환 시 로드
  useEffect(() => {
    if (activeTab === 'dataQuality' && user?.is_superuser) {
      loadDataQuality()
    }
  }, [activeTab, user, loadDataQuality])

  // 데이터 정제 실행
  const handleDataCleanup = async (tableName: string, issueType: string, dryRun: boolean) => {
    const key = `${tableName}_${issueType}`
    setCleanupLoading(key)
    setError(null)

    try {
      const response = await apiClient.post('/api/admin/data-quality/cleanup', {
        table_name: tableName,
        issue_type: issueType,
        dry_run: dryRun
      })

      if (dryRun) {
        // 시뮬레이션 결과 표시
        setSaveSuccess(`시뮬레이션: ${response.data.affected_records}개 레코드가 삭제될 예정입니다.`)
      } else {
        // 실제 정제 완료
        setSaveSuccess(`${response.data.affected_records}개 레코드가 삭제되었습니다.`)
        // 데이터 새로고침
        await loadDataQuality()
      }
      setTimeout(() => setSaveSuccess(null), 5000)
    } catch (err) {
      console.error('Failed to cleanup data:', err)
      setError('데이터 정제에 실패했습니다.')
    } finally {
      setCleanupLoading(null)
    }
  }

  // 이용권 관리 모달 열기
  const openSubscriptionModal = (u: User) => {
    setSubscriptionModal({ isOpen: true, user: u })
    setSelectedTier(u.subscription_tier as SubscriptionTier || 'free')
    setSelectedDuration(null)
    setError(null)
  }

  // 이용권 관리 모달 닫기
  const closeSubscriptionModal = () => {
    setSubscriptionModal({ isOpen: false, user: null })
    setSelectedTier('free')
    setSelectedDuration(null)
  }

  // 이용권 업데이트
  const handleUpdateSubscription = async () => {
    if (!subscriptionModal.user) return

    setIsUpdatingSubscription(true)
    setError(null)

    try {
      await apiClient.patch(`/api/admin/users/${subscriptionModal.user.id}/subscription`, {
        tier: selectedTier,
        duration_days: selectedDuration
      })

      // 목록 새로고침
      const usersRes = await apiClient.get('/api/admin/users')
      setUsers(usersRes.data.users)

      setSaveSuccess('이용권이 업데이트되었습니다.')
      setTimeout(() => setSaveSuccess(null), 3000)
      closeSubscriptionModal()
    } catch (err) {
      console.error('Failed to update subscription:', err)
      setError('이용권 업데이트에 실패했습니다.')
    } finally {
      setIsUpdatingSubscription(false)
    }
  }

  // 이용권 만료일 포맷
  const formatSubscriptionExpiry = (expiresAt: string | null): string => {
    if (!expiresAt) return '무기한'
    const date = new Date(expiresAt)
    const now = new Date()
    if (date < now) return '만료됨'
    return date.toLocaleDateString('ko-KR')
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
        <div className="flex gap-2 mb-6 border-b border-theme-border overflow-x-auto">
          {[
            { id: 'users', label: '회원 관리' },
            { id: 'database', label: '데이터베이스 현황' },
            { id: 'dataQuality', label: '데이터 품질' },
            { id: 'content', label: '콘텐츠 관리' },
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
                        <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">이용권</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">만료일</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">가입일</th>
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
                          <td className="px-4 py-3">
                            <span className={`px-2 py-0.5 text-xs rounded ${
                              TIER_COLORS[u.subscription_tier as SubscriptionTier] || TIER_COLORS.free
                            }`}>
                              {TIER_LABELS[u.subscription_tier as SubscriptionTier] || '무료'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-text-secondary">
                            {formatSubscriptionExpiry(u.subscription_expires_at)}
                          </td>
                          <td className="px-4 py-3 text-sm text-text-secondary">
                            {new Date(u.created_at).toLocaleDateString('ko-KR')}
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
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => openSubscriptionModal(u)}
                                className="px-2 py-1 text-xs rounded bg-accent-primary/10 text-accent-primary hover:bg-accent-primary/20 transition-colors"
                              >
                                이용권
                              </button>
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
                            </div>
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

            {/* 데이터베이스 현황 탭 */}
            {activeTab === 'database' && (
              <div className="space-y-6">
                {databaseLoading ? (
                  <div className="flex items-center justify-center py-20">
                    <div className="w-8 h-8 border-4 border-accent-primary border-t-transparent rounded-full animate-spin" />
                  </div>
                ) : databaseOverview ? (
                  <>
                    {/* 전체 통계 */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="bg-theme-card border border-theme-border rounded-xl p-6">
                        <p className="text-sm text-text-secondary mb-2">전체 테이블</p>
                        <span className="text-3xl font-bold text-text-primary">
                          {databaseOverview.total_tables}
                        </span>
                      </div>
                      <div className="bg-theme-card border border-theme-border rounded-xl p-6">
                        <p className="text-sm text-text-secondary mb-2">전체 레코드</p>
                        <span className="text-3xl font-bold text-accent-primary">
                          {databaseOverview.total_records.toLocaleString()}
                        </span>
                      </div>
                      <div className="bg-theme-card border border-theme-border rounded-xl p-6">
                        <p className="text-sm text-text-secondary mb-2">마지막 업데이트</p>
                        <span className="text-lg font-medium text-text-primary">
                          {new Date(databaseOverview.last_updated).toLocaleString('ko-KR')}
                        </span>
                      </div>
                    </div>

                    {/* 카테고리별 테이블 */}
                    {['core', 'financial', 'risk', 'user', 'system'].map((category) => {
                      const categoryTables = databaseOverview.tables.filter(t => t.category === category)
                      if (categoryTables.length === 0) return null

                      const categoryLabels: Record<string, { name: string; color: string }> = {
                        core: { name: '핵심 데이터', color: 'border-blue-500/30 bg-blue-500/5' },
                        financial: { name: '재무 데이터', color: 'border-green-500/30 bg-green-500/5' },
                        risk: { name: '리스크/지수', color: 'border-orange-500/30 bg-orange-500/5' },
                        user: { name: '사용자', color: 'border-purple-500/30 bg-purple-500/5' },
                        system: { name: '시스템', color: 'border-gray-500/30 bg-gray-500/5' }
                      }

                      const categoryInfo = categoryLabels[category] || { name: category, color: '' }

                      return (
                        <div key={category} className={`bg-theme-card border rounded-xl p-6 ${categoryInfo.color}`}>
                          <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-text-primary">{categoryInfo.name}</h3>
                            <span className="text-sm text-text-secondary">
                              {categoryTables.reduce((sum, t) => sum + t.record_count, 0).toLocaleString()}개 레코드
                            </span>
                          </div>

                          <div className="overflow-x-auto">
                            <table className="w-full">
                              <thead>
                                <tr className="border-b border-theme-border">
                                  <th className="px-3 py-2 text-left text-xs font-medium text-text-secondary uppercase">테이블명</th>
                                  <th className="px-3 py-2 text-left text-xs font-medium text-text-secondary uppercase">설명</th>
                                  <th className="px-3 py-2 text-right text-xs font-medium text-text-secondary uppercase">레코드 수</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-theme-border">
                                {categoryTables.map((table) => (
                                  <tr key={table.name} className="hover:bg-theme-hover/50 transition-colors">
                                    <td className="px-3 py-2">
                                      <code className="text-sm font-mono text-accent-primary">{table.name}</code>
                                    </td>
                                    <td className="px-3 py-2 text-sm text-text-secondary">{table.description}</td>
                                    <td className="px-3 py-2 text-right">
                                      <span className={`text-sm font-medium ${
                                        table.record_count === 0 ? 'text-accent-danger' : 'text-text-primary'
                                      }`}>
                                        {table.record_count.toLocaleString()}
                                      </span>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )
                    })}

                    {/* 새로고침 버튼 */}
                    <div className="flex justify-center">
                      <button
                        onClick={loadDatabaseOverview}
                        disabled={databaseLoading}
                        className="px-4 py-2 text-sm bg-theme-surface border border-theme-border rounded-lg text-text-secondary hover:text-text-primary hover:bg-theme-hover transition-colors disabled:opacity-50"
                      >
                        <span className="flex items-center gap-2">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                          새로고침
                        </span>
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="p-8 text-center text-text-secondary">
                    데이터를 불러오는 중 오류가 발생했습니다.
                  </div>
                )}
              </div>
            )}

            {/* 데이터 품질 탭 */}
            {activeTab === 'dataQuality' && (
              <div className="space-y-6">
                {dataQualityLoading ? (
                  <div className="flex items-center justify-center py-20">
                    <div className="w-8 h-8 border-4 border-accent-primary border-t-transparent rounded-full animate-spin" />
                  </div>
                ) : dataQuality ? (
                  <>
                    {/* 전체 품질 점수 */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      <div className="bg-theme-card border border-theme-border rounded-xl p-6">
                        <p className="text-sm text-text-secondary mb-2">전체 품질 점수</p>
                        <div className="flex items-center gap-3">
                          <span className={`text-3xl font-bold ${
                            dataQuality.overall_score >= 95 ? 'text-accent-success' :
                            dataQuality.overall_score >= 80 ? 'text-accent-warning' :
                            'text-accent-danger'
                          }`}>
                            {dataQuality.overall_score.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                      <div className="bg-theme-card border border-accent-danger/30 rounded-xl p-6">
                        <p className="text-sm text-text-secondary mb-2">심각 이슈</p>
                        <span className="text-3xl font-bold text-accent-danger">
                          {dataQuality.summary.critical}
                        </span>
                      </div>
                      <div className="bg-theme-card border border-accent-warning/30 rounded-xl p-6">
                        <p className="text-sm text-text-secondary mb-2">경고</p>
                        <span className="text-3xl font-bold text-accent-warning">
                          {dataQuality.summary.warning}
                        </span>
                      </div>
                      <div className="bg-theme-card border border-accent-primary/30 rounded-xl p-6">
                        <p className="text-sm text-text-secondary mb-2">정보</p>
                        <span className="text-3xl font-bold text-accent-primary">
                          {dataQuality.summary.info}
                        </span>
                      </div>
                    </div>

                    {/* 테이블별 품질 현황 */}
                    {dataQuality.tables.map((table) => (
                      <div key={table.table_name} className="bg-theme-card border border-theme-border rounded-xl p-6">
                        <div className="flex items-center justify-between mb-4">
                          <div>
                            <h3 className="text-lg font-semibold text-text-primary">{table.table_name}</h3>
                            <p className="text-sm text-text-secondary">
                              {table.total_records.toLocaleString()}개 레코드
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`text-2xl font-bold ${
                              table.quality_score >= 95 ? 'text-accent-success' :
                              table.quality_score >= 80 ? 'text-accent-warning' :
                              'text-accent-danger'
                            }`}>
                              {table.quality_score.toFixed(1)}%
                            </span>
                            <button
                              onClick={loadDataQuality}
                              className="p-2 text-text-muted hover:text-text-secondary hover:bg-theme-hover rounded-lg transition-colors"
                              title="새로고침"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                              </svg>
                            </button>
                          </div>
                        </div>

                        {table.issues.length === 0 ? (
                          <div className="p-4 bg-accent-success/10 border border-accent-success/30 rounded-lg">
                            <p className="text-sm text-accent-success">이슈 없음</p>
                          </div>
                        ) : (
                          <div className="space-y-3">
                            {table.issues.map((issue) => {
                              const cleanupKey = `${table.table_name}_${issue.issue_type}`
                              const isCleanupLoading = cleanupLoading === cleanupKey

                              return (
                                <div
                                  key={issue.issue_type}
                                  className={`p-4 rounded-lg border ${
                                    issue.severity === 'critical'
                                      ? 'bg-accent-danger/10 border-accent-danger/30'
                                      : issue.severity === 'warning'
                                      ? 'bg-accent-warning/10 border-accent-warning/30'
                                      : 'bg-accent-primary/10 border-accent-primary/30'
                                  }`}
                                >
                                  <div className="flex items-start justify-between">
                                    <div>
                                      <div className="flex items-center gap-2 mb-1">
                                        <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                                          issue.severity === 'critical'
                                            ? 'bg-accent-danger/20 text-accent-danger'
                                            : issue.severity === 'warning'
                                            ? 'bg-accent-warning/20 text-accent-warning'
                                            : 'bg-accent-primary/20 text-accent-primary'
                                        }`}>
                                          {issue.severity === 'critical' ? '심각' : issue.severity === 'warning' ? '경고' : '정보'}
                                        </span>
                                        <span className="text-sm font-medium text-text-primary">
                                          {issue.description}
                                        </span>
                                      </div>
                                      <p className="text-sm text-text-secondary">
                                        {issue.record_count.toLocaleString()}개 레코드
                                        {issue.company_count > 0 && ` (${issue.company_count.toLocaleString()}개 기업)`}
                                      </p>
                                      {issue.sample_data && issue.sample_data.length > 0 && (
                                        <div className="mt-2 p-2 bg-theme-surface rounded text-xs text-text-muted font-mono">
                                          샘플: {issue.sample_data.slice(0, 3).map(s =>
                                            typeof s === 'object' ? JSON.stringify(s).slice(0, 50) : String(s)
                                          ).join(', ')}
                                        </div>
                                      )}
                                    </div>
                                    {['numeric_shareholder_name', 'financial_item_name', 'abnormal_share_count'].includes(issue.issue_type) && (
                                      <div className="flex gap-2">
                                        <button
                                          onClick={() => handleDataCleanup(table.table_name, issue.issue_type, true)}
                                          disabled={isCleanupLoading}
                                          className="px-3 py-1.5 text-xs rounded bg-theme-surface border border-theme-border text-text-secondary hover:bg-theme-hover transition-colors disabled:opacity-50"
                                        >
                                          {isCleanupLoading ? '처리중...' : '시뮬레이션'}
                                        </button>
                                        <button
                                          onClick={() => {
                                            if (confirm(`정말 ${issue.record_count.toLocaleString()}개 레코드를 삭제하시겠습니까?`)) {
                                              handleDataCleanup(table.table_name, issue.issue_type, false)
                                            }
                                          }}
                                          disabled={isCleanupLoading}
                                          className="px-3 py-1.5 text-xs rounded bg-accent-danger/10 border border-accent-danger/30 text-accent-danger hover:bg-accent-danger/20 transition-colors disabled:opacity-50"
                                        >
                                          정제 실행
                                        </button>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    ))}
                  </>
                ) : (
                  <div className="p-8 text-center text-text-secondary">
                    데이터를 불러오는 중 오류가 발생했습니다.
                  </div>
                )}
              </div>
            )}

            {/* 콘텐츠 관리 탭 */}
            {activeTab === 'content' && (
              <div className="space-y-6">
                <div className="bg-theme-card border border-theme-border rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-text-primary mb-4">서비스 소개 페이지 콘텐츠</h3>
                  <p className="text-sm text-text-secondary mb-6">
                    각 섹션의 텍스트와 이미지를 편집할 수 있습니다. 변경사항은 즉시 반영됩니다.
                  </p>

                  <div className="space-y-8">
                    {contentSections.map((section) => {
                      const sectionLabels: Record<string, string> = {
                        hero: '히어로 섹션',
                        why_section: '왜 RaymondsRisk인가요?',
                        advantage1: '장점 1: 정보 비대칭 해소',
                        advantage2: '장점 2: 특허 기술 기반 신뢰성',
                        advantage3: '장점 3: 실시간 업데이트',
                        advantage4: '장점 4: 합법적이고 투명한 데이터',
                        advantage5: '장점 5: 접근성과 경제성',
                        features_section: '주요 기능 섹션',
                        feature1: '기능 1: 3단계 관계망 자동 분석',
                        feature2: '기능 2: AI 리스크 조기 경고',
                        feature3: '기능 3: 포트폴리오 주가 패턴 예측',
                        feature4: '기능 4: 24시간 실시간 모니터링',
                        stats_section: '검증된 성과 섹션',
                        cta_section: 'CTA 섹션'
                      }

                      return (
                        <div key={section.section} className="border border-theme-border rounded-lg p-4">
                          <h4 className="text-sm font-medium text-accent-primary mb-4">
                            {sectionLabels[section.section] || section.section}
                          </h4>

                          <div className="space-y-4">
                            {section.fields.map((field) => {
                              const currentValue = pageContent[section.section]?.[field.field] ?? field.default
                              const isEditing = editingField?.section === section.section && editingField?.field === field.field
                              const fieldLabels: Record<string, string> = {
                                badge: '배지',
                                title: '제목',
                                description: '설명',
                                image: '이미지'
                              }

                              if (field.type === 'image') {
                                return (
                                  <div key={field.field} className="space-y-2">
                                    <label className="block text-xs font-medium text-text-secondary">
                                      {fieldLabels[field.field] || field.field}
                                      {field.recommended_size && (
                                        <span className="ml-2 text-text-muted">
                                          (권장: {field.recommended_size.width}x{field.recommended_size.height}px)
                                        </span>
                                      )}
                                    </label>
                                    <div className="flex items-center gap-4">
                                      {currentValue ? (
                                        <div className="relative">
                                          <img
                                            src={currentValue.startsWith('data:') ? currentValue : (currentValue.startsWith('/') ? `${import.meta.env.VITE_API_URL || ''}${currentValue}` : currentValue)}
                                            alt="Preview"
                                            className="w-32 h-20 object-cover rounded border border-theme-border"
                                          />
                                          <button
                                            onClick={() => handleDeleteImage(section.section)}
                                            className="absolute -top-2 -right-2 w-6 h-6 bg-accent-danger text-white rounded-full flex items-center justify-center text-xs hover:bg-accent-danger/80"
                                          >
                                            ×
                                          </button>
                                        </div>
                                      ) : (
                                        <div className="w-32 h-20 bg-theme-surface border border-dashed border-theme-border rounded flex items-center justify-center">
                                          <span className="text-xs text-text-muted">No image</span>
                                        </div>
                                      )}
                                      <label className="cursor-pointer">
                                        <span className={`px-3 py-1.5 text-xs rounded border transition-colors ${
                                          uploadingImage === section.section
                                            ? 'bg-theme-surface border-theme-border text-text-muted cursor-wait'
                                            : currentValue
                                              ? 'bg-accent-warning/10 border-accent-warning/30 text-accent-warning hover:bg-accent-warning/20'
                                              : 'bg-accent-primary/10 border-accent-primary/30 text-accent-primary hover:bg-accent-primary/20'
                                        }`}>
                                          {uploadingImage === section.section ? '업로드 중...' : (currentValue ? '이미지 교체' : '이미지 업로드')}
                                        </span>
                                        <input
                                          type="file"
                                          accept="image/*"
                                          className="hidden"
                                          disabled={uploadingImage === section.section}
                                          onChange={(e) => {
                                            const file = e.target.files?.[0]
                                            if (file) handleImageUpload(section.section, file)
                                          }}
                                        />
                                      </label>
                                    </div>
                                  </div>
                                )
                              }

                              return (
                                <div key={field.field} className="space-y-2">
                                  <label className="block text-xs font-medium text-text-secondary">
                                    {fieldLabels[field.field] || field.field}
                                  </label>
                                  {isEditing ? (
                                    <div className="flex gap-2">
                                      <textarea
                                        value={editingField.value}
                                        onChange={(e) => setEditingField({...editingField, value: e.target.value})}
                                        rows={field.field === 'description' ? 3 : 1}
                                        className="flex-1 px-3 py-2 bg-theme-surface border border-accent-primary rounded text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/30"
                                      />
                                      <div className="flex flex-col gap-1">
                                        <button
                                          onClick={() => handleUpdateContent(section.section, field.field, editingField.value)}
                                          disabled={isSaving}
                                          className="px-3 py-1 text-xs bg-accent-primary text-white rounded hover:bg-accent-primary/90 disabled:opacity-50"
                                        >
                                          저장
                                        </button>
                                        <button
                                          onClick={() => setEditingField(null)}
                                          className="px-3 py-1 text-xs bg-theme-surface border border-theme-border text-text-secondary rounded hover:bg-theme-hover"
                                        >
                                          취소
                                        </button>
                                      </div>
                                    </div>
                                  ) : (
                                    <div
                                      onClick={() => setEditingField({
                                        section: section.section,
                                        field: field.field,
                                        value: currentValue
                                      })}
                                      className="px-3 py-2 bg-theme-surface border border-theme-border rounded text-sm text-text-primary cursor-pointer hover:border-accent-primary/50 transition-colors"
                                    >
                                      {currentValue || <span className="text-text-muted italic">비어있음 (클릭하여 편집)</span>}
                                    </div>
                                  )}
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
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

      {/* 이용권 관리 모달 */}
      {subscriptionModal.isOpen && subscriptionModal.user && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-theme-card border border-theme-border rounded-2xl w-full max-w-md shadow-2xl">
            {/* 모달 헤더 */}
            <div className="flex items-center justify-between p-6 border-b border-theme-border">
              <div>
                <h3 className="text-lg font-semibold text-text-primary">이용권 관리</h3>
                <p className="text-sm text-text-secondary mt-1">{subscriptionModal.user.email}</p>
              </div>
              <button
                onClick={closeSubscriptionModal}
                className="p-2 text-text-muted hover:text-text-secondary hover:bg-theme-hover rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* 모달 내용 */}
            <div className="p-6 space-y-6">
              {/* 현재 이용권 정보 */}
              <div className="p-4 bg-theme-surface rounded-lg">
                <p className="text-sm text-text-secondary mb-2">현재 이용권</p>
                <div className="flex items-center gap-3">
                  <span className={`px-3 py-1 text-sm font-medium rounded ${
                    TIER_COLORS[subscriptionModal.user.subscription_tier as SubscriptionTier] || TIER_COLORS.free
                  }`}>
                    {TIER_LABELS[subscriptionModal.user.subscription_tier as SubscriptionTier] || '무료'}
                  </span>
                  <span className="text-sm text-text-secondary">
                    {formatSubscriptionExpiry(subscriptionModal.user.subscription_expires_at)}
                  </span>
                </div>
              </div>

              {/* 이용권 선택 */}
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-3">
                  이용권 등급
                </label>
                <div className="space-y-2">
                  {(Object.keys(TIER_LABELS) as SubscriptionTier[]).map((tier) => (
                    <button
                      key={tier}
                      onClick={() => setSelectedTier(tier)}
                      className={`w-full px-4 py-3 rounded-lg border text-left transition-all ${
                        selectedTier === tier
                          ? 'border-accent-primary bg-accent-primary/10'
                          : 'border-theme-border bg-theme-surface hover:border-theme-border-hover'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`font-medium ${selectedTier === tier ? 'text-accent-primary' : 'text-text-primary'}`}>
                          {TIER_LABELS[tier]}
                        </span>
                        <span className={`text-sm ${selectedTier === tier ? 'text-accent-primary' : 'text-text-muted'}`}>
                          {TIER_PRICES[tier]}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* 기간 선택 */}
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-3">
                  유효 기간
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { value: null, label: '무기한' },
                    { value: 30, label: '30일' },
                    { value: 90, label: '90일' },
                    { value: 180, label: '180일' },
                    { value: 365, label: '1년' },
                    { value: 730, label: '2년' }
                  ].map((option) => (
                    <button
                      key={option.label}
                      onClick={() => setSelectedDuration(option.value)}
                      className={`px-3 py-2 rounded-lg border text-sm transition-all ${
                        selectedDuration === option.value
                          ? 'border-accent-primary bg-accent-primary/10 text-accent-primary'
                          : 'border-theme-border bg-theme-surface text-text-secondary hover:border-theme-border-hover'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* 모달 푸터 */}
            <div className="flex items-center justify-end gap-3 p-6 border-t border-theme-border">
              <button
                onClick={closeSubscriptionModal}
                className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors"
              >
                취소
              </button>
              <button
                onClick={handleUpdateSubscription}
                disabled={isUpdatingSubscription}
                className={`px-6 py-2 rounded-lg text-sm font-medium text-white transition-colors ${
                  isUpdatingSubscription
                    ? 'bg-accent-primary/50 cursor-not-allowed'
                    : 'bg-accent-primary hover:bg-accent-primary/90'
                }`}
              >
                {isUpdatingSubscription ? '저장 중...' : '저장'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AdminPage

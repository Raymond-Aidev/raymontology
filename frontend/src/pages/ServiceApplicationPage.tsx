import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'
import {
  getEnterprisePlans,
  getMyApplications,
  createServiceApplication,
  cancelApplication
} from '../api/serviceApplications'
import type {
  EnterprisePlanInfo,
  ServiceApplicationResponse,
  PaymentInfoResponse,
  ApplicationStatus
} from '../types/serviceApplication'
import { APPLICATION_STATUS_INFO } from '../types/serviceApplication'

// 입금 정보 상수
const BANK_INFO = {
  company_name: '코넥트',
  business_number: '686-19-02309',
  bank_name: '카카오뱅크',
  account_number: '3333-31-9041159',
  account_holder: '코넥트 / 박재준'
}

function ServiceApplicationPage() {
  const navigate = useNavigate()
  const { isAuthenticated, user, checkAuth } = useAuthStore()

  // 상태
  const [plans, setPlans] = useState<EnterprisePlanInfo[]>([])
  const [myApplications, setMyApplications] = useState<ServiceApplicationResponse[]>([])
  const [currentSubscription, setCurrentSubscription] = useState<{
    status: 'ACTIVE' | 'NONE' | 'EXPIRED'
    tier: string
    end_date: string | null
  } | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // 모달 상태
  const [showApplicationModal, setShowApplicationModal] = useState(false)
  const [showPaymentInfoModal, setShowPaymentInfoModal] = useState(false)
  const [paymentInfo, setPaymentInfo] = useState<PaymentInfoResponse | null>(null)

  // 폼 상태
  const [selectedPlan, setSelectedPlan] = useState<string>('1_YEAR') // 기본 선택: 1년
  const [applicantEmail, setApplicantEmail] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 데이터 로드
  useEffect(() => {
    loadData()
  }, [isAuthenticated])

  const loadData = async () => {
    setIsLoading(true)
    try {
      // 플랜 정보 로드
      const plansData = await getEnterprisePlans()
      setPlans(plansData.plans)

      // 로그인 상태면 내 신청 내역 로드
      if (isAuthenticated) {
        const myData = await getMyApplications()
        setMyApplications(myData.applications)
        setCurrentSubscription(myData.current_subscription)
        setApplicantEmail(user?.email || '')
      }
    } catch (err) {
      console.error('Failed to load data:', err)
    } finally {
      setIsLoading(false)
    }
  }

  // 신청 폼 열기
  const handleOpenApplicationModal = () => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: { pathname: '/service-application' } } })
      return
    }

    // 이미 PENDING 신청이 있는지 확인
    const hasPendingApplication = myApplications.some(app => app.status === 'PENDING')
    if (hasPendingApplication) {
      alert('이미 처리 중인 신청이 있습니다.')
      return
    }

    // 모달 열 때 이메일 재확인 (로그인된 사용자 이메일)
    if (user?.email) {
      setApplicantEmail(user.email)
    }

    setShowApplicationModal(true)
    setError(null)
    // selectedPlan은 유지 (첫 화면에서 선택한 플랜)
    setFile(null)
  }

  // 신청 제출
  const handleSubmit = async () => {
    if (!applicantEmail) {
      setError('이메일을 입력해주세요.')
      return
    }
    if (!file) {
      setError('사업자등록증을 첨부해주세요.')
      return
    }
    if (!selectedPlan) {
      setError('이용 기간을 선택해주세요.')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const result = await createServiceApplication(applicantEmail, selectedPlan, file!)
      setPaymentInfo(result)
      setShowApplicationModal(false)
      setShowPaymentInfoModal(true)

      // 목록 새로고침
      const myData = await getMyApplications()
      setMyApplications(myData.applications)

      // 인증 상태 새로고침
      await checkAuth()
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || '신청 중 오류가 발생했습니다.')
    } finally {
      setIsSubmitting(false)
    }
  }

  // 신청 취소
  const handleCancel = async (applicationId: string) => {
    if (!confirm('신청을 취소하시겠습니까?')) return

    try {
      await cancelApplication(applicationId)
      // 목록 새로고침
      const myData = await getMyApplications()
      setMyApplications(myData.applications)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      alert(error.response?.data?.detail || '취소 중 오류가 발생했습니다.')
    }
  }

  // 파일 선택
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      // 파일 타입 검증
      const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
      if (!allowedTypes.includes(selectedFile.type)) {
        setError('PDF, JPG, PNG 파일만 업로드 가능합니다.')
        return
      }
      // 파일 크기 검증 (10MB)
      if (selectedFile.size > 10 * 1024 * 1024) {
        setError('파일 크기는 10MB 이하여야 합니다.')
        return
      }
      setFile(selectedFile)
      setError(null)
    }
  }

  // 상태 배지 렌더링
  const renderStatusBadge = (status: ApplicationStatus) => {
    const info = APPLICATION_STATUS_INFO[status]
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${info.color} ${info.bgColor}`}>
        {info.label}
      </span>
    )
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-theme-bg flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-accent-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-theme-bg">
      {/* Header */}
      <header className="bg-dark-surface/80 backdrop-blur-xl border-b border-dark-border sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <Link to="/" className="inline-block">
              <RaymondsRiskLogo size="sm" variant="compact" />
            </Link>
            <nav className="flex items-center gap-4">
              <Link to="/" className="text-sm text-text-secondary hover:text-text-primary transition-colors">
                홈
              </Link>
              <Link to="/about" className="text-sm text-text-secondary hover:text-text-primary transition-colors">
                서비스 소개
              </Link>
              {isAuthenticated ? (
                <span className="text-sm text-text-muted">{user?.email}</span>
              ) : (
                <Link to="/login" className="text-sm text-accent-primary hover:text-accent-primary/80 transition-colors">
                  로그인
                </Link>
              )}
            </nav>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* 페이지 제목 */}
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-text-primary mb-3">서비스 이용신청</h1>
          <p className="text-text-secondary">
            엔터프라이즈 서비스를 신청하세요
          </p>
        </div>

        {/* 현재 이용권 상태 */}
        {currentSubscription && currentSubscription.status !== 'NONE' && (
          <div className={`mb-8 p-4 rounded-xl border ${
            currentSubscription.status === 'ACTIVE'
              ? 'bg-accent-success/10 border-accent-success/30'
              : 'bg-yellow-500/10 border-yellow-500/30'
          }`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-secondary">현재 이용권</p>
                <p className="text-lg font-semibold text-text-primary">
                  {currentSubscription.status === 'ACTIVE' ? '이용중' : '만료됨'}
                </p>
              </div>
              {currentSubscription.end_date && (
                <div className="text-right">
                  <p className="text-sm text-text-secondary">만료일</p>
                  <p className="text-text-primary">
                    {new Date(currentSubscription.end_date).toLocaleDateString('ko-KR')}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 서비스 이용 프로세스 */}
        <div className="bg-theme-card border border-theme-border rounded-2xl p-6 mb-8">
          <h2 className="text-lg font-semibold text-text-primary mb-6">서비스 이용 프로세스</h2>
          <div className="grid grid-cols-4 gap-4">
            {[
              { step: 1, title: '서비스이용신청', desc: '이메일, 사업자등록증, 이용기간 선택' },
              { step: 2, title: '입금안내 이메일', desc: '신청 완료 시 입금 계좌 안내' },
              { step: 3, title: '입금확인', desc: '관리자 입금 확인' },
              { step: 4, title: '서비스이용', desc: '이용권 활성화 및 서비스 이용' }
            ].map((item, index) => (
              <div key={item.step} className="relative">
                <div className="flex flex-col items-center text-center">
                  <div className="w-10 h-10 rounded-full bg-accent-primary flex items-center justify-center text-white font-bold mb-3">
                    {item.step}
                  </div>
                  <h3 className="text-sm font-medium text-text-primary mb-1">{item.title}</h3>
                  <p className="text-xs text-text-secondary">{item.desc}</p>
                </div>
                {index < 3 && (
                  <div className="absolute top-5 left-[60%] w-[80%] h-0.5 bg-accent-primary/30" />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 이용 요금 */}
        <div className="bg-theme-card border border-theme-border rounded-2xl p-6 mb-8">
          <h2 className="text-lg font-semibold text-text-primary mb-6">이용 요금</h2>
          <div className="grid md:grid-cols-3 gap-4">
            {plans.map((plan) => (
              <div
                key={plan.plan_type}
                onClick={() => setSelectedPlan(plan.plan_type)}
                className={`p-6 rounded-xl border transition-all cursor-pointer ${
                  selectedPlan === plan.plan_type
                    ? 'border-accent-primary bg-accent-primary/5'
                    : 'border-theme-border hover:border-accent-primary/50'
                }`}
              >
                {plan.plan_type === '1_YEAR' && (
                  <div className="text-xs text-accent-primary font-medium mb-2">추천</div>
                )}
                <h3 className="text-lg font-semibold text-text-primary mb-2">{plan.name_ko}</h3>
                <div className="flex items-baseline gap-1 mb-2">
                  <span className="text-2xl font-bold text-text-primary">{plan.price_display}</span>
                </div>
                {plan.discount && (
                  <span className="text-xs text-accent-success">({plan.discount})</span>
                )}
                {selectedPlan === plan.plan_type && (
                  <div className="mt-3 flex items-center gap-1 text-xs text-accent-primary">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    선택됨
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 신청 버튼 */}
        <div className="text-center mb-8">
          <button
            onClick={handleOpenApplicationModal}
            disabled={myApplications.some(app => app.status === 'PENDING')}
            className={`px-8 py-4 rounded-xl text-lg font-semibold transition-all ${
              myApplications.some(app => app.status === 'PENDING')
                ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                : 'bg-accent-primary hover:bg-accent-primary/90 text-white'
            }`}
          >
            {myApplications.some(app => app.status === 'PENDING')
              ? '처리 중인 신청이 있습니다'
              : '서비스 이용신청'}
          </button>
        </div>

        {/* 내 신청 내역 */}
        {isAuthenticated && myApplications.length > 0 && (
          <div className="bg-theme-card border border-theme-border rounded-2xl p-6">
            <h2 className="text-lg font-semibold text-text-primary mb-4">내 신청 내역</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-theme-border">
                    <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">신청일</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">플랜</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">금액</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">상태</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">액션</th>
                  </tr>
                </thead>
                <tbody>
                  {myApplications.map((app) => (
                    <tr key={app.id} className="border-b border-theme-border/50 last:border-b-0">
                      <td className="py-3 px-4 text-sm text-text-primary">
                        {new Date(app.created_at).toLocaleDateString('ko-KR')}
                      </td>
                      <td className="py-3 px-4 text-sm text-text-primary">{app.plan_name_ko}</td>
                      <td className="py-3 px-4 text-sm text-text-primary">{app.plan_amount.toLocaleString()}원</td>
                      <td className="py-3 px-4">{renderStatusBadge(app.status)}</td>
                      <td className="py-3 px-4 text-right">
                        {app.status === 'PENDING' && (
                          <button
                            onClick={() => handleCancel(app.id)}
                            className="text-sm text-red-400 hover:text-red-300 transition-colors"
                          >
                            취소
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      {/* 신청 모달 */}
      {showApplicationModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-theme-card border border-theme-border rounded-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-text-primary">서비스 이용신청</h2>
                <button
                  onClick={() => setShowApplicationModal(false)}
                  className="text-text-secondary hover:text-text-primary"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {error && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                  {error}
                </div>
              )}

              <div className="space-y-4">
                {/* 이메일 (로그인된 이메일 - 읽기 전용) */}
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    신청자 이메일
                  </label>
                  <div className="w-full px-4 py-3 bg-theme-surface/50 border border-theme-border rounded-xl text-text-primary flex items-center gap-2">
                    <svg className="w-4 h-4 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    <span>{applicantEmail}</span>
                  </div>
                  <p className="mt-1 text-xs text-text-muted">로그인된 계정의 이메일로 자동 입력됩니다.</p>
                </div>

                {/* 사업자등록증 */}
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    사업자등록증 첨부 <span className="text-red-400">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png"
                      onChange={handleFileChange}
                      className="hidden"
                      id="file-upload"
                    />
                    <label
                      htmlFor="file-upload"
                      className={`flex items-center gap-3 px-4 py-3 bg-theme-surface border border-dashed rounded-xl cursor-pointer transition-colors ${
                        file
                          ? 'border-accent-success bg-accent-success/5'
                          : 'border-theme-border hover:border-accent-primary'
                      }`}
                    >
                      {file ? (
                        <svg className="w-5 h-5 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <svg className="w-5 h-5 text-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                      )}
                      <span className={`text-sm ${file ? 'text-accent-success' : 'text-text-secondary'}`}>
                        {file ? file.name : '파일 선택 (PDF, JPG, PNG)'}
                      </span>
                    </label>
                  </div>
                  <p className="text-xs text-text-muted mt-1">최대 10MB · 사업자등록증은 필수 첨부 항목입니다</p>
                </div>

                {/* 이용 기간 선택 */}
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    이용 기간 선택 <span className="text-red-400">*</span>
                  </label>
                  <div className="space-y-2">
                    {plans.map((plan) => (
                      <label
                        key={plan.plan_type}
                        className={`flex items-center justify-between p-4 rounded-xl border cursor-pointer transition-all ${
                          selectedPlan === plan.plan_type
                            ? 'border-accent-primary bg-accent-primary/10'
                            : 'border-theme-border hover:border-accent-primary/50'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <input
                            type="radio"
                            name="plan"
                            value={plan.plan_type}
                            checked={selectedPlan === plan.plan_type}
                            onChange={(e) => setSelectedPlan(e.target.value)}
                            className="w-4 h-4 text-accent-primary"
                          />
                          <div>
                            <span className="text-text-primary font-medium">{plan.name_ko}</span>
                            {plan.discount && (
                              <span className="ml-2 text-xs text-accent-success">({plan.discount} 할인)</span>
                            )}
                          </div>
                        </div>
                        <span className="text-text-primary font-semibold">{plan.price_display}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* 제출 버튼 */}
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitting}
                  className="w-full py-4 bg-accent-primary hover:bg-accent-primary/90 text-white font-semibold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <span className="flex items-center justify-center gap-2">
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      처리 중...
                    </span>
                  ) : (
                    '신청하기'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 입금 안내 모달 */}
      {showPaymentInfoModal && paymentInfo && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-theme-card border border-theme-border rounded-2xl max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-text-primary">입금 안내</h2>
                <button
                  onClick={() => setShowPaymentInfoModal(false)}
                  className="text-text-secondary hover:text-text-primary"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="text-center mb-6">
                <div className="w-16 h-16 bg-accent-success/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <p className="text-lg text-text-primary font-medium">신청이 완료되었습니다</p>
              </div>

              {/* 입금 정보 */}
              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 mb-6">
                <h3 className="text-sm font-semibold text-yellow-400 mb-3">입금 정보</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-text-secondary">사명</span>
                    <span className="text-text-primary">{BANK_INFO.company_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">사업자등록번호</span>
                    <span className="text-text-primary">{BANK_INFO.business_number}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">입금계좌</span>
                    <span className="text-text-primary">{BANK_INFO.bank_name} {BANK_INFO.account_number}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">예금주</span>
                    <span className="text-text-primary">{BANK_INFO.account_holder}</span>
                  </div>
                </div>
              </div>

              {/* 결제 금액 */}
              <div className="bg-theme-surface border border-theme-border rounded-xl p-4 mb-6">
                <h3 className="text-sm font-semibold text-text-secondary mb-2">결제 금액</h3>
                <div className="flex justify-between items-baseline">
                  <span className="text-text-secondary">{paymentInfo.plan_name_ko} 이용권</span>
                  <span className="text-2xl font-bold text-accent-primary">{paymentInfo.plan_amount_display}</span>
                </div>
              </div>

              <p className="text-xs text-text-muted text-center mb-6">
                상기 내용은 신청하신 이메일로 발송됩니다.
              </p>

              <button
                onClick={() => setShowPaymentInfoModal(false)}
                className="w-full py-4 bg-accent-primary hover:bg-accent-primary/90 text-white font-semibold rounded-xl transition-colors"
              >
                확인
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ServiceApplicationPage

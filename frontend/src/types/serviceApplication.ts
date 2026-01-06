/**
 * 서비스 이용신청 관련 타입 정의
 */

// 플랜 타입
export type PlanType = '1_MONTH' | '6_MONTHS' | '1_YEAR'

// 신청 상태
export type ApplicationStatus =
  | 'PENDING'           // 신청완료 (입금대기)
  | 'PAYMENT_CONFIRMED' // 입금확인
  | 'APPROVED'          // 승인완료
  | 'REJECTED'          // 거절
  | 'CANCELLED'         // 취소

// 플랜 정보
export interface EnterprisePlanInfo {
  plan_type: PlanType
  name_ko: string
  price: number
  price_display: string
  duration_days: number
  discount: string | null
}

// 신청 응답 (사용자용)
export interface ServiceApplicationResponse {
  id: string
  applicant_email: string
  plan_type: PlanType
  plan_name_ko: string
  plan_amount: number
  status: ApplicationStatus
  subscription_start_date: string | null
  subscription_end_date: string | null
  created_at: string
  updated_at: string
}

// 신청 목록 응답 (사용자용)
export interface ServiceApplicationListResponse {
  applications: ServiceApplicationResponse[]
  current_subscription: {
    status: 'ACTIVE' | 'NONE' | 'EXPIRED'
    tier: string
    end_date: string | null
  } | null
}

// 신청 응답 (관리자용)
export interface ServiceApplicationAdminResponse extends ServiceApplicationResponse {
  user_id: string
  has_business_registration: boolean
  business_registration_file_name: string | null
  admin_memo: string | null
  processed_by: string | null
  processed_at: string | null
}

// 신청 목록 응답 (관리자용)
export interface ServiceApplicationAdminListResponse {
  applications: ServiceApplicationAdminResponse[]
  total: number
  page: number
  total_pages: number
}

// 입금 정보
export interface PaymentBankInfo {
  company_name: string
  business_number: string
  bank_name: string
  account_number: string
  account_holder: string
}

// 신청 완료 응답 (입금 안내 포함)
export interface PaymentInfoResponse {
  application_id: string
  plan_type: PlanType
  plan_name_ko: string
  plan_amount: number
  plan_amount_display: string
  bank_info: PaymentBankInfo
  message: string
}

// 관리자용 타입 별칭
export type ServiceApplicationAdmin = ServiceApplicationAdminResponse

// 엔터프라이즈 플랜 정보 (프론트엔드용)
export const ENTERPRISE_PLANS: EnterprisePlanInfo[] = [
  {
    plan_type: '1_MONTH',
    name_ko: '1개월',
    price: 300000,
    price_display: '300,000원',
    duration_days: 30,
    discount: null
  },
  {
    plan_type: '6_MONTHS',
    name_ko: '6개월',
    price: 1500000,
    price_display: '1,500,000원',
    duration_days: 180,
    discount: '17% 할인'
  },
  {
    plan_type: '1_YEAR',
    name_ko: '1년',
    price: 3000000,
    price_display: '3,000,000원',
    duration_days: 365,
    discount: '17% 할인'
  }
]

// 상태별 표시 정보
export const APPLICATION_STATUS_INFO: Record<ApplicationStatus, {
  label: string
  color: string
  textColor: string
  bgColor: string
}> = {
  PENDING: {
    label: '입금대기',
    color: 'text-yellow-400',
    textColor: 'text-yellow-400',
    bgColor: 'bg-yellow-400/10'
  },
  PAYMENT_CONFIRMED: {
    label: '입금확인',
    color: 'text-blue-400',
    textColor: 'text-blue-400',
    bgColor: 'bg-blue-400/10'
  },
  APPROVED: {
    label: '승인완료',
    color: 'text-green-400',
    textColor: 'text-green-400',
    bgColor: 'bg-green-400/10'
  },
  REJECTED: {
    label: '거절',
    color: 'text-red-400',
    textColor: 'text-red-400',
    bgColor: 'bg-red-400/10'
  },
  CANCELLED: {
    label: '취소',
    color: 'text-gray-400',
    textColor: 'text-gray-400',
    bgColor: 'bg-gray-400/10'
  }
}

/**
 * 서비스 이용신청 API
 */
import apiClient from './client'
import type {
  EnterprisePlanInfo,
  ServiceApplicationListResponse,
  ServiceApplicationAdminListResponse,
  PaymentInfoResponse,
  ApplicationStatus
} from '../types/serviceApplication'

// ========================================
// 플랜 정보
// ========================================

export async function getEnterprisePlans(): Promise<{ plans: EnterprisePlanInfo[] }> {
  const response = await apiClient.get('/api/service-applications/plans')
  return response.data
}

// ========================================
// 사용자 API
// ========================================

export async function createServiceApplication(
  applicantEmail: string,
  planType: string,
  file?: File
): Promise<PaymentInfoResponse> {
  const formData = new FormData()
  formData.append('applicant_email', applicantEmail)
  formData.append('plan_type', planType)
  if (file) {
    formData.append('business_registration_file', file)
  }

  const response = await apiClient.post('/api/service-applications/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

export async function getMyApplications(): Promise<ServiceApplicationListResponse> {
  const response = await apiClient.get('/api/service-applications/my')
  return response.data
}

export async function cancelApplication(applicationId: string): Promise<{ message: string }> {
  const response = await apiClient.delete(`/api/service-applications/${applicationId}`)
  return response.data
}

// ========================================
// 관리자 API
// ========================================

export async function getAdminApplications(
  status?: ApplicationStatus,
  page = 1,
  limit = 20
): Promise<ServiceApplicationAdminListResponse> {
  const params = new URLSearchParams()
  if (status) params.append('status_filter', status)
  params.append('page', page.toString())
  params.append('limit', limit.toString())

  const response = await apiClient.get(`/api/admin/service-applications?${params.toString()}`)
  return response.data
}

export async function updateApplicationStatus(
  applicationId: string,
  status: 'PAYMENT_CONFIRMED' | 'APPROVED' | 'REJECTED',
  data?: {
    admin_memo?: string
    subscription_start_date?: string  // YYYY-MM-DD
    subscription_end_date?: string    // YYYY-MM-DD
  }
): Promise<{ id: string; status: ApplicationStatus; message: string }> {
  const response = await apiClient.put(
    `/api/admin/service-applications/${applicationId}/status`,
    {
      status,
      ...data
    }
  )
  return response.data
}

export async function downloadBusinessRegistration(
  applicationId: string
): Promise<{ file_name: string; mime_type: string; data_url: string }> {
  const response = await apiClient.get(`/api/admin/service-applications/${applicationId}/file`)
  return response.data
}

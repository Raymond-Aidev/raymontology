'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/lib/auth';

// API URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://raymontology-production.up.railway.app/api';

interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  oauth_provider: string | null;
  subscription_tier: string;
  subscription_expires_at: string | null;
  created_at: string;
  last_login: string | null;
}

type SubscriptionTier = 'free' | 'light' | 'max';

const TIER_LABELS: Record<SubscriptionTier, string> = {
  free: '무료',
  light: '라이트',
  max: '맥스'
};

const TIER_COLORS: Record<SubscriptionTier, string> = {
  free: 'bg-gray-100 text-gray-600',
  light: 'bg-blue-100 text-blue-600',
  max: 'bg-purple-100 text-purple-600'
};

const TIER_PRICES: Record<SubscriptionTier, string> = {
  free: '무료',
  light: '3,000원/월',
  max: '30,000원/월'
};

interface Stats {
  total_users: number;
  active_users: number;
  oauth_users: number;
  superusers: number;
}

export default function AdminPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading, token } = useAuthStore();

  // 상태
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // 이용권 관리 모달
  const [subscriptionModal, setSubscriptionModal] = useState<{
    isOpen: boolean;
    user: User | null;
  }>({ isOpen: false, user: null });
  const [selectedTier, setSelectedTier] = useState<SubscriptionTier>('free');
  const [selectedDuration, setSelectedDuration] = useState<number | null>(null);
  const [isUpdatingSubscription, setIsUpdatingSubscription] = useState(false);

  // 로그인 체크
  useEffect(() => {
    if (authLoading) return;

    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    if (user && !user.is_superuser) {
      router.push('/');
      return;
    }
  }, [isAuthenticated, user, authLoading, router]);

  // API 호출 헬퍼
  const apiCall = async (endpoint: string, options: RequestInit = {}) => {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API Error: ${response.status}`);
    }

    return response.json();
  };

  // 데이터 로드
  const loadData = useCallback(async () => {
    if (!user?.is_superuser || !token) return;

    setIsLoading(true);
    setError(null);

    try {
      const [usersRes, statsRes] = await Promise.all([
        apiCall('/admin/users'),
        apiCall('/admin/stats')
      ]);

      setUsers(usersRes.users || []);
      setStats(statsRes);
    } catch (err) {
      console.error('Failed to load admin data:', err);
      setError('데이터를 불러오는데 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  }, [user, token]);

  useEffect(() => {
    if (user?.is_superuser && token) {
      loadData();
    }
  }, [loadData, user, token]);

  // 사용자 활성화/비활성화 토글
  const handleToggleUserActive = async (userId: string) => {
    try {
      await apiCall(`/admin/users/${userId}/toggle-active`, { method: 'PATCH' });
      const usersRes = await apiCall('/admin/users');
      setUsers(usersRes.users || []);
      setSuccessMessage('사용자 상태가 변경되었습니다.');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error('Failed to toggle user:', err);
      setError('사용자 상태 변경에 실패했습니다.');
    }
  };

  // 이용권 모달 열기
  const openSubscriptionModal = (u: User) => {
    setSubscriptionModal({ isOpen: true, user: u });
    setSelectedTier((u.subscription_tier as SubscriptionTier) || 'free');
    setSelectedDuration(null);
    setError(null);
  };

  // 이용권 모달 닫기
  const closeSubscriptionModal = () => {
    setSubscriptionModal({ isOpen: false, user: null });
    setSelectedTier('free');
    setSelectedDuration(null);
  };

  // 이용권 업데이트
  const handleUpdateSubscription = async () => {
    if (!subscriptionModal.user) return;

    setIsUpdatingSubscription(true);
    setError(null);

    try {
      await apiCall(`/admin/users/${subscriptionModal.user.id}/subscription`, {
        method: 'PATCH',
        body: JSON.stringify({
          tier: selectedTier,
          duration_days: selectedDuration
        })
      });

      const usersRes = await apiCall('/admin/users');
      setUsers(usersRes.users || []);
      setSuccessMessage('이용권이 업데이트되었습니다.');
      setTimeout(() => setSuccessMessage(null), 3000);
      closeSubscriptionModal();
    } catch (err) {
      console.error('Failed to update subscription:', err);
      setError('이용권 업데이트에 실패했습니다.');
    } finally {
      setIsUpdatingSubscription(false);
    }
  };

  // 만료일 포맷
  const formatSubscriptionExpiry = (expiresAt: string | null): string => {
    if (!expiresAt) return '무기한';
    const date = new Date(expiresAt);
    const now = new Date();
    if (date < now) return '만료됨';
    return date.toLocaleDateString('ko-KR');
  };

  // 로딩 중이거나 권한 없음
  if (authLoading || !user?.is_superuser) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/" className="text-xl font-bold text-blue-600">
                RaymondsIndex
              </Link>
              <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-600 rounded">
                관리자
              </span>
            </div>
            <Link
              href="/"
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              메인으로
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 통계 카드 */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
              <p className="text-sm text-gray-500">전체 회원</p>
              <p className="text-2xl font-bold text-gray-900">{stats.total_users}</p>
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
              <p className="text-sm text-gray-500">활성 회원</p>
              <p className="text-2xl font-bold text-green-600">{stats.active_users}</p>
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
              <p className="text-sm text-gray-500">OAuth 가입</p>
              <p className="text-2xl font-bold text-blue-600">{stats.oauth_users}</p>
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
              <p className="text-sm text-gray-500">관리자</p>
              <p className="text-2xl font-bold text-orange-600">{stats.superusers}</p>
            </div>
          </div>
        )}

        {/* 에러/성공 메시지 */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}
        {successMessage && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-600">{successMessage}</p>
          </div>
        )}

        {/* 회원 목록 */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">회원 관리</h2>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">이메일</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">이름</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">가입방식</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">이용권</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">만료일</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">가입일</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">상태</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">액션</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-gray-900">{u.email}</span>
                          {u.is_superuser && (
                            <span className="px-1.5 py-0.5 text-xs bg-orange-100 text-orange-600 rounded">
                              관리자
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {u.full_name || u.username}
                      </td>
                      <td className="px-4 py-3">
                        {u.oauth_provider ? (
                          <span className={`px-2 py-0.5 text-xs rounded ${
                            u.oauth_provider === 'google'
                              ? 'bg-blue-100 text-blue-600'
                              : 'bg-yellow-100 text-yellow-600'
                          }`}>
                            {u.oauth_provider}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">이메일</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 text-xs rounded ${
                          TIER_COLORS[u.subscription_tier as SubscriptionTier] || TIER_COLORS.free
                        }`}>
                          {TIER_LABELS[u.subscription_tier as SubscriptionTier] || '무료'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {formatSubscriptionExpiry(u.subscription_expires_at)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {new Date(u.created_at).toLocaleDateString('ko-KR')}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 text-xs rounded ${
                          u.is_active
                            ? 'bg-green-100 text-green-600'
                            : 'bg-red-100 text-red-600'
                        }`}>
                          {u.is_active ? '활성' : '비활성'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => openSubscriptionModal(u)}
                            className="px-2 py-1 text-xs rounded bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
                          >
                            이용권
                          </button>
                          {!u.is_superuser && (
                            <button
                              onClick={() => handleToggleUserActive(u.id)}
                              className={`px-2 py-1 text-xs rounded transition-colors ${
                                u.is_active
                                  ? 'bg-red-50 text-red-600 hover:bg-red-100'
                                  : 'bg-green-50 text-green-600 hover:bg-green-100'
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
          )}
          {!isLoading && users.length === 0 && (
            <div className="p-8 text-center text-gray-500">
              등록된 회원이 없습니다.
            </div>
          )}
        </div>
      </div>

      {/* 이용권 관리 모달 */}
      {subscriptionModal.isOpen && subscriptionModal.user && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white border border-gray-200 rounded-2xl w-full max-w-md shadow-2xl">
            {/* 모달 헤더 */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">이용권 관리</h3>
                <p className="text-sm text-gray-500 mt-1">{subscriptionModal.user.email}</p>
              </div>
              <button
                onClick={closeSubscriptionModal}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* 모달 내용 */}
            <div className="p-6 space-y-6">
              {/* 현재 이용권 정보 */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500 mb-2">현재 이용권</p>
                <div className="flex items-center gap-3">
                  <span className={`px-3 py-1 text-sm font-medium rounded ${
                    TIER_COLORS[subscriptionModal.user.subscription_tier as SubscriptionTier] || TIER_COLORS.free
                  }`}>
                    {TIER_LABELS[subscriptionModal.user.subscription_tier as SubscriptionTier] || '무료'}
                  </span>
                  <span className="text-sm text-gray-500">
                    {formatSubscriptionExpiry(subscriptionModal.user.subscription_expires_at)}
                  </span>
                </div>
              </div>

              {/* 이용권 선택 */}
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-3">
                  이용권 등급
                </label>
                <div className="space-y-2">
                  {(Object.keys(TIER_LABELS) as SubscriptionTier[]).map((tier) => (
                    <button
                      key={tier}
                      onClick={() => setSelectedTier(tier)}
                      className={`w-full px-4 py-3 rounded-lg border text-left transition-all ${
                        selectedTier === tier
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 bg-white hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`font-medium ${selectedTier === tier ? 'text-blue-600' : 'text-gray-900'}`}>
                          {TIER_LABELS[tier]}
                        </span>
                        <span className={`text-sm ${selectedTier === tier ? 'text-blue-600' : 'text-gray-400'}`}>
                          {TIER_PRICES[tier]}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* 기간 선택 */}
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-3">
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
                          ? 'border-blue-500 bg-blue-50 text-blue-600'
                          : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* 모달 푸터 */}
            <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
              <button
                onClick={closeSubscriptionModal}
                className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
              >
                취소
              </button>
              <button
                onClick={handleUpdateSubscription}
                disabled={isUpdatingSubscription}
                className={`px-6 py-2 rounded-lg text-sm font-medium text-white transition-colors ${
                  isUpdatingSubscription
                    ? 'bg-blue-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {isUpdatingSubscription ? '저장 중...' : '저장'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

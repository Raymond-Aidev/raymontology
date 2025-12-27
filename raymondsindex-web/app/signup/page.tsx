'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/lib/auth';

export default function SignupPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, register, error, clearError } = useAuthStore();

  // 이미 로그인된 경우 메인으로 리다이렉트
  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      router.push('/');
    }
  }, [isAuthenticated, authLoading, router]);

  // 폼 상태
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [touched, setTouched] = useState({
    username: false,
    fullName: false,
    email: false,
    password: false,
    confirmPassword: false,
  });

  // 유효성 검사
  const usernameError = touched.username && !username ? '사용자명을 입력해주세요' :
                        touched.username && username.length < 3 ? '사용자명은 3자 이상이어야 합니다' :
                        touched.username && username.length > 50 ? '사용자명은 50자 이하여야 합니다' :
                        touched.username && !/^[a-zA-Z0-9_]+$/.test(username) ? '영문, 숫자, 밑줄(_)만 사용 가능합니다' : '';

  const fullNameError = touched.fullName && fullName && fullName.length > 100 ? '이름은 100자 이하여야 합니다' : '';

  const emailError = touched.email && !email ? '이메일을 입력해주세요' :
                     touched.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? '유효한 이메일 형식이 아닙니다' : '';

  // 비밀번호 규칙: 8자 이상, 대문자, 소문자, 숫자, 특수문자 각 1개 이상
  const validatePassword = (pwd: string) => {
    if (!pwd) return '비밀번호를 입력해주세요';
    if (pwd.length < 8) return '비밀번호는 8자 이상이어야 합니다';
    if (!/[A-Z]/.test(pwd)) return '대문자를 1개 이상 포함해야 합니다';
    if (!/[a-z]/.test(pwd)) return '소문자를 1개 이상 포함해야 합니다';
    if (!/[0-9]/.test(pwd)) return '숫자를 1개 이상 포함해야 합니다';
    if (!/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(pwd)) return '특수문자를 1개 이상 포함해야 합니다';
    return '';
  };

  const passwordError = touched.password ? validatePassword(password) : '';
  const confirmPasswordError = touched.confirmPassword && !confirmPassword ? '비밀번호 확인을 입력해주세요' :
                               touched.confirmPassword && password !== confirmPassword ? '비밀번호가 일치하지 않습니다' : '';

  const isValid = username && email && password && confirmPassword &&
                  !usernameError && !emailError && !passwordError && !confirmPasswordError && agreeTerms;

  // 비밀번호 강도 표시
  const getPasswordStrength = (pwd: string) => {
    if (!pwd) return { level: 0, text: '', color: '' };
    let strength = 0;
    if (pwd.length >= 8) strength++;
    if (pwd.length >= 12) strength++;
    if (/[A-Z]/.test(pwd)) strength++;
    if (/[a-z]/.test(pwd)) strength++;
    if (/[0-9]/.test(pwd)) strength++;
    if (/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(pwd)) strength++;

    if (strength <= 2) return { level: 1, text: '약함', color: 'bg-red-500' };
    if (strength <= 4) return { level: 3, text: '보통', color: 'bg-yellow-500' };
    return { level: 5, text: '강함', color: 'bg-green-500' };
  };

  const passwordStrength = getPasswordStrength(password);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setTouched({ username: true, fullName: true, email: true, password: true, confirmPassword: true });

    if (!isValid) return;

    setLoading(true);
    clearError();

    const success = await register({
      username,
      email,
      password,
      full_name: fullName || undefined,
    });

    setLoading(false);

    if (success) {
      setShowSuccessModal(true);
    }
  }, [username, fullName, email, password, isValid, register, clearError]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-8 px-4">
      <div className="w-full max-w-md">
        {/* 로고 */}
        <div className="flex justify-center mb-8">
          <Link href="/" className="text-2xl font-bold text-blue-600">
            RaymondsIndex
          </Link>
        </div>

        {/* 회원가입 카드 */}
        <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-lg">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            회원가입
          </h2>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 사용자명 */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                사용자명 <span className="text-red-500">*</span>
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                onBlur={() => setTouched(prev => ({ ...prev, username: true }))}
                placeholder="영문, 숫자, 밑줄 (3-50자)"
                autoComplete="username"
                className={`w-full px-4 py-3 bg-white border rounded-lg text-gray-900 placeholder-gray-400 transition-colors focus:outline-none focus:ring-2
                           ${usernameError ? 'border-red-300 focus:ring-red-200 focus:border-red-500' :
                                            'border-gray-300 focus:ring-blue-200 focus:border-blue-500'}`}
              />
              {usernameError && <p className="mt-1 text-sm text-red-500">{usernameError}</p>}
            </div>

            {/* 이름 (선택) */}
            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-gray-700 mb-1">
                이름 <span className="text-gray-400">(선택)</span>
              </label>
              <input
                id="fullName"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                onBlur={() => setTouched(prev => ({ ...prev, fullName: true }))}
                placeholder="홍길동"
                autoComplete="name"
                className={`w-full px-4 py-3 bg-white border rounded-lg text-gray-900 placeholder-gray-400 transition-colors focus:outline-none focus:ring-2
                           ${fullNameError ? 'border-red-300 focus:ring-red-200 focus:border-red-500' :
                                            'border-gray-300 focus:ring-blue-200 focus:border-blue-500'}`}
              />
              {fullNameError && <p className="mt-1 text-sm text-red-500">{fullNameError}</p>}
            </div>

            {/* 이메일 */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                이메일 <span className="text-red-500">*</span>
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onBlur={() => setTouched(prev => ({ ...prev, email: true }))}
                placeholder="example@email.com"
                autoComplete="email"
                className={`w-full px-4 py-3 bg-white border rounded-lg text-gray-900 placeholder-gray-400 transition-colors focus:outline-none focus:ring-2
                           ${emailError ? 'border-red-300 focus:ring-red-200 focus:border-red-500' :
                                         'border-gray-300 focus:ring-blue-200 focus:border-blue-500'}`}
              />
              {emailError && <p className="mt-1 text-sm text-red-500">{emailError}</p>}
            </div>

            {/* 비밀번호 */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                비밀번호 <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onBlur={() => setTouched(prev => ({ ...prev, password: true }))}
                  placeholder="8자 이상, 대/소문자, 숫자, 특수문자 포함"
                  autoComplete="new-password"
                  className={`w-full px-4 py-3 pr-12 bg-white border rounded-lg text-gray-900 placeholder-gray-400 transition-colors focus:outline-none focus:ring-2
                             ${passwordError ? 'border-red-300 focus:ring-red-200 focus:border-red-500' :
                                              'border-gray-300 focus:ring-blue-200 focus:border-blue-500'}`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
              {passwordError && <p className="mt-1 text-sm text-red-500">{passwordError}</p>}

              {/* 비밀번호 강도 */}
              {password && (
                <div className="mt-2">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map(i => (
                      <div
                        key={i}
                        className={`h-1 flex-1 rounded-full transition-colors ${
                          i <= passwordStrength.level ? passwordStrength.color : 'bg-gray-200'
                        }`}
                      />
                    ))}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    비밀번호 강도: <span className={passwordStrength.level <= 1 ? 'text-red-500' : passwordStrength.level <= 3 ? 'text-yellow-500' : 'text-green-500'}>{passwordStrength.text}</span>
                  </p>
                </div>
              )}

              {/* 비밀번호 요구사항 */}
              <div className="mt-2 text-xs text-gray-500">
                <p className="font-medium mb-1">비밀번호 요구사항:</p>
                <ul className="space-y-0.5 ml-3">
                  <li className={password.length >= 8 ? 'text-green-500' : ''}>8자 이상</li>
                  <li className={/[A-Z]/.test(password) ? 'text-green-500' : ''}>대문자 1개 이상</li>
                  <li className={/[a-z]/.test(password) ? 'text-green-500' : ''}>소문자 1개 이상</li>
                  <li className={/[0-9]/.test(password) ? 'text-green-500' : ''}>숫자 1개 이상</li>
                  <li className={/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(password) ? 'text-green-500' : ''}>특수문자 1개 이상</li>
                </ul>
              </div>
            </div>

            {/* 비밀번호 확인 */}
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
                비밀번호 확인 <span className="text-red-500">*</span>
              </label>
              <input
                id="confirmPassword"
                type={showPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                onBlur={() => setTouched(prev => ({ ...prev, confirmPassword: true }))}
                placeholder="비밀번호 재입력"
                autoComplete="new-password"
                className={`w-full px-4 py-3 bg-white border rounded-lg text-gray-900 placeholder-gray-400 transition-colors focus:outline-none focus:ring-2
                           ${confirmPasswordError ? 'border-red-300 focus:ring-red-200 focus:border-red-500' :
                                                   'border-gray-300 focus:ring-blue-200 focus:border-blue-500'}`}
              />
              {confirmPasswordError && <p className="mt-1 text-sm text-red-500">{confirmPasswordError}</p>}
            </div>

            {/* 약관 동의 */}
            <div className="flex items-start gap-3">
              <input
                id="agreeTerms"
                type="checkbox"
                checked={agreeTerms}
                onChange={(e) => setAgreeTerms(e.target.checked)}
                className="mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <label htmlFor="agreeTerms" className="text-sm text-gray-600">
                <span className="text-blue-600 hover:underline cursor-pointer">이용약관</span> 및{' '}
                <span className="text-blue-600 hover:underline cursor-pointer">개인정보 처리방침</span>에 동의합니다
                <span className="text-red-500 ml-1">*</span>
              </label>
            </div>

            {/* 회원가입 버튼 */}
            <button
              type="submit"
              disabled={loading || !agreeTerms}
              className={`w-full py-3.5 px-4 rounded-lg font-semibold text-white transition-all ${
                loading || !agreeTerms
                  ? 'bg-blue-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-500/25'
              }`}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  가입 중...
                </span>
              ) : (
                '회원가입'
              )}
            </button>
          </form>

          {/* 로그인 링크 */}
          <div className="mt-6 pt-6 border-t border-gray-200 text-center">
            <p className="text-sm text-gray-600">
              이미 계정이 있으신가요?{' '}
              <Link href="/login" className="text-blue-600 hover:underline font-medium">
                로그인
              </Link>
            </p>
          </div>
        </div>
      </div>

      {/* 회원가입 완료 모달 */}
      {showSuccessModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-white border border-gray-200 rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl">
            {/* 성공 아이콘 */}
            <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>

            <h3 className="text-xl font-semibold text-gray-900 text-center mb-2">
              회원가입 완료
            </h3>

            <p className="text-sm text-gray-600 text-center mb-6">
              회원가입이 완료되었습니다.
              <br />
              로그인 페이지에서 로그인해주세요.
            </p>

            <Link
              href="/login"
              className="block w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl text-center transition-colors"
              onClick={() => {
                setShowSuccessModal(false);
                useAuthStore.getState().logout();
              }}
            >
              로그인하러 가기
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

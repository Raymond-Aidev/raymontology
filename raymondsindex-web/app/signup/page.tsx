'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/lib/auth';

// 이용약관 내용
const TERMS_OF_SERVICE = `# RaymondsIndex 서비스 이용약관

**시행일자**: 2025년 1월 1일

본 약관은 코넥트 (이하 "회사")가 제공하는 RaymondsIndex 서비스(이하 "서비스")의 이용과 관련하여 회사와 이용자 간의 권리, 의무 및 책임사항, 기타 필요한 사항을 규정함을 목적으로 합니다.

---

## 제1조 (목적)

본 약관은 회사가 제공하는 RaymondsIndex 서비스의 이용 조건 및 절차, 회사와 이용자 간의 권리, 의무 및 책임사항을 규정함을 목적으로 합니다.

---

## 제2조 (용어의 정의)

1. **"서비스"**란 DART(금융감독원 전자공시시스템) 공개 데이터를 기반으로 기업의 자본 배분 효율성을 분석하고 RaymondsIndex를 제공하는 정보 서비스를 말합니다.

2. **"이용자"**란 본 약관에 동의하고 회사가 제공하는 서비스를 이용하는 자를 말합니다.

3. **"구독"**이란 이용자가 일정 기간 동안 서비스를 이용할 수 있는 권한을 말합니다.

4. **"콘텐츠"**란 서비스를 통해 제공되는 기업 정보, RaymondsIndex 점수, 분석 자료 등 모든 정보를 말합니다.

---

## 제3조 (약관의 효력 및 변경)

1. 본 약관은 서비스 화면에 게시하거나 기타의 방법으로 이용자에게 공지함으로써 효력이 발생합니다.

2. 회사는 필요한 경우 관련 법령을 위배하지 않는 범위에서 본 약관을 변경할 수 있으며, 변경된 약관은 시행일자 7일 전부터 공지합니다.

3. 이용자가 변경된 약관에 동의하지 않는 경우, 서비스 이용을 중단하고 구독을 해지할 수 있습니다.

---

## 제4조 (서비스의 제공)

1. 회사는 다음과 같은 서비스를 제공합니다:
   - 기업 검색 및 RaymondsIndex 조회
   - 기업 스크리닝 및 필터링
   - 상세 재무 분석 정보
   - 기타 회사가 정하는 부가 서비스

2. 서비스는 연중무휴, 1일 24시간 제공함을 원칙으로 합니다. 단, 회사의 업무상 또는 기술상의 이유로 서비스가 일시 중지될 수 있습니다.

---

## 제5조 (서비스 이용 계약의 성립)

1. 서비스 이용 계약은 이용자가 본 약관에 동의하고 회원가입 절차를 완료함으로써 성립됩니다.

2. 회사는 다음 각 호에 해당하는 경우 이용 계약을 거절할 수 있습니다:
   - 본인의 실명으로 신청하지 않은 경우
   - 타인의 명의를 도용한 경우
   - 허위 정보를 기재한 경우
   - 관련 법령 위반 목적으로 신청한 경우

---

## 제6조 (구독 및 결제)

1. 서비스 이용을 위해서는 구독료를 결제해야 합니다.

2. 구독은 결제 완료 시점부터 유효하며, 구독 종류에 따라 기간이 다릅니다.

3. 구독료는 VAT가 포함된 금액입니다.

---

## 제7조 (구독 해지 및 환불)

1. 이용자는 언제든지 구독을 해지할 수 있습니다.

2. 환불 정책은 다음과 같습니다:
   - **7일 이내**: 전액 환불
   - **7일 경과 후**: 사용 기간을 일할 계산하여 잔여 기간에 해당하는 금액 환불

---

## 제8조 (이용자의 의무)

1. 이용자는 다음 행위를 하여서는 안 됩니다:
   - 타인의 정보를 도용하는 행위
   - 서비스의 정보를 무단으로 수집, 복제, 배포하는 행위
   - 자동화된 수단(크롤링, 봇 등)을 이용한 무단 접근
   - 서비스의 정상적인 운영을 방해하는 행위
   - 관련 법령을 위반하는 행위

2. 이용자는 본 서비스를 통해 취득한 정보를 상업적 목적으로 재배포할 수 없습니다.

---

## 제9조 (회사의 의무)

1. 회사는 관련 법령과 본 약관이 정하는 권리의 행사와 의무의 이행을 신의에 따라 성실하게 준수합니다.

2. 회사는 이용자의 개인정보 보호를 위해 개인정보처리방침을 수립하고 준수합니다.

---

## 제10조 (면책사항)

1. **투자 판단 관련 면책**
   - 본 서비스는 DART 공개 데이터를 기반으로 한 정보 제공 서비스이며, **투자 권유, 투자 자문, 금융 상품 판매를 목적으로 하지 않습니다**.
   - 본 서비스를 통해 제공되는 모든 정보는 **참고용**일 뿐이며, **투자 판단의 최종 책임은 전적으로 이용자에게 있습니다**.
   - 회사는 서비스 이용으로 인한 투자 손실, 수익 감소 등 **어떠한 금전적 손해에 대해서도 책임지지 않습니다**.

2. **데이터 정확성 관련 면책**
   - 본 서비스는 금융감독원 DART 시스템의 공개 데이터를 기반으로 하며, 회사는 **데이터의 정확성, 완전성, 최신성을 보증하지 않습니다**.

---

## 제11조 (저작권 및 지적재산권)

1. 회사가 제공하는 서비스의 디자인, 소프트웨어, 분석 알고리즘 등에 대한 저작권 및 지적재산권은 회사에 귀속됩니다.

2. 이용자는 서비스를 이용함으로써 얻은 정보를 회사의 사전 승낙 없이 복제, 송신, 출판, 배포, 방송 등의 방법으로 이용하거나 제3자에게 이용하게 하여서는 안 됩니다.

---

## 제12조 (분쟁 해결)

1. 회사와 이용자는 서비스와 관련하여 발생한 분쟁을 원만하게 해결하기 위하여 필요한 모든 노력을 해야 합니다.

2. 분쟁이 해결되지 않을 경우, 양 당사자는 대한민국 법률에 따라 관할 법원에 소를 제기할 수 있습니다.

---

## 부칙

**제1조 (시행일)**: 본 약관은 2025년 1월 1일부터 시행합니다.

---

## 고객센터

- **이메일**: support@raymondsindex.com
- **운영시간**: 평일 09:00 ~ 18:00 (주말 및 공휴일 휴무)

---

**코넥트**
대표: 박재준
사업자등록번호: 686-19-02309

© 2025 코넥트. All rights reserved.
`;

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
  const [showTermsModal, setShowTermsModal] = useState(false);
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
                <button
                  type="button"
                  onClick={() => setShowTermsModal(true)}
                  className="text-blue-600 hover:underline"
                >
                  이용약관
                </button>
                {' '}및{' '}
                <button
                  type="button"
                  onClick={() => setShowTermsModal(true)}
                  className="text-blue-600 hover:underline"
                >
                  개인정보 처리방침
                </button>
                에 동의합니다
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

      {/* 이용약관 모달 */}
      {showTermsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white border border-gray-200 rounded-2xl w-full max-w-2xl max-h-[80vh] shadow-2xl flex flex-col">
            {/* 모달 헤더 */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">이용약관</h3>
              <button
                type="button"
                onClick={() => setShowTermsModal(false)}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* 모달 내용 */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="prose prose-sm max-w-none text-gray-700">
                {TERMS_OF_SERVICE.split('\n').map((line, index) => {
                  if (line.startsWith('# ')) {
                    return <h1 key={index} className="text-xl font-bold text-gray-900 mt-4 mb-2">{line.slice(2)}</h1>;
                  } else if (line.startsWith('## ')) {
                    return <h2 key={index} className="text-lg font-semibold text-gray-800 mt-6 mb-2">{line.slice(3)}</h2>;
                  } else if (line.startsWith('**') && line.endsWith('**')) {
                    return <p key={index} className="font-semibold text-gray-900 mt-2">{line.slice(2, -2)}</p>;
                  } else if (line.startsWith('---')) {
                    return <hr key={index} className="my-4 border-gray-200" />;
                  } else if (line.startsWith('   - ')) {
                    return <li key={index} className="ml-6 text-gray-600">{line.slice(5)}</li>;
                  } else if (line.startsWith('1. ') || line.startsWith('2. ') || line.startsWith('3. ') || line.startsWith('4. ')) {
                    return <p key={index} className="mt-2 text-gray-700">{line}</p>;
                  } else if (line.trim() === '') {
                    return <br key={index} />;
                  } else {
                    return <p key={index} className="text-gray-700">{line}</p>;
                  }
                })}
              </div>
            </div>

            {/* 모달 푸터 */}
            <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200">
              <button
                type="button"
                onClick={() => setShowTermsModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
              >
                닫기
              </button>
              <button
                type="button"
                onClick={() => {
                  setAgreeTerms(true);
                  setShowTermsModal(false);
                }}
                className="px-6 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 transition-colors"
              >
                동의하고 닫기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

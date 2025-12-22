import { useState, useCallback } from 'react'
import { useAuthStore } from '../../store/authStore'

interface RegisterFormProps {
  onSuccess?: () => void
  onSwitchToLogin?: () => void
}

export default function RegisterForm({ onSuccess, onSwitchToLogin }: RegisterFormProps) {
  const { register, isLoading, error, clearError } = useAuthStore()

  const [username, setUsername] = useState('')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [agreeTerms, setAgreeTerms] = useState(false)
  const [touched, setTouched] = useState({
    username: false,
    fullName: false,
    email: false,
    password: false,
    confirmPassword: false,
  })

  // 유효성 검사
  const usernameError = touched.username && !username ? '사용자명을 입력해주세요' :
                        touched.username && username.length < 3 ? '사용자명은 3자 이상이어야 합니다' :
                        touched.username && username.length > 50 ? '사용자명은 50자 이하여야 합니다' :
                        touched.username && !/^[a-zA-Z0-9_]+$/.test(username) ? '영문, 숫자, 밑줄(_)만 사용 가능합니다' : ''

  const fullNameError = touched.fullName && fullName && fullName.length > 100 ? '이름은 100자 이하여야 합니다' : ''

  const emailError = touched.email && !email ? '이메일을 입력해주세요' :
                     touched.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? '유효한 이메일 형식이 아닙니다' : ''

  // 백엔드 비밀번호 규칙: 8자 이상, 대문자, 소문자, 숫자, 특수문자 각 1개 이상
  const validatePassword = (pwd: string) => {
    if (!pwd) return '비밀번호를 입력해주세요'
    if (pwd.length < 8) return '비밀번호는 8자 이상이어야 합니다'
    if (!/[A-Z]/.test(pwd)) return '대문자를 1개 이상 포함해야 합니다'
    if (!/[a-z]/.test(pwd)) return '소문자를 1개 이상 포함해야 합니다'
    if (!/[0-9]/.test(pwd)) return '숫자를 1개 이상 포함해야 합니다'
    if (!/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(pwd)) return '특수문자를 1개 이상 포함해야 합니다'
    return ''
  }

  const passwordError = touched.password ? validatePassword(password) : ''
  const confirmPasswordError = touched.confirmPassword && !confirmPassword ? '비밀번호 확인을 입력해주세요' :
                               touched.confirmPassword && password !== confirmPassword ? '비밀번호가 일치하지 않습니다' : ''

  const isValid = username && email && password && confirmPassword &&
                  !usernameError && !emailError && !passwordError && !confirmPasswordError && agreeTerms

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setTouched({ username: true, fullName: true, email: true, password: true, confirmPassword: true })

    if (!isValid) return

    clearError()
    const success = await register({
      username,
      email,
      password,
      full_name: fullName || undefined,
    })
    if (success && onSuccess) {
      onSuccess()
    }
  }, [username, fullName, email, password, isValid, register, clearError, onSuccess])

  // 비밀번호 강도 표시
  const getPasswordStrength = (pwd: string) => {
    if (!pwd) return { level: 0, text: '', color: '' }
    let strength = 0
    if (pwd.length >= 8) strength++
    if (pwd.length >= 12) strength++
    if (/[A-Z]/.test(pwd)) strength++
    if (/[a-z]/.test(pwd)) strength++
    if (/[0-9]/.test(pwd)) strength++
    if (/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(pwd)) strength++

    if (strength <= 2) return { level: 1, text: '약함', color: 'bg-red-500' }
    if (strength <= 4) return { level: 3, text: '보통', color: 'bg-yellow-500' }
    return { level: 5, text: '강함', color: 'bg-green-500' }
  }

  const passwordStrength = getPasswordStrength(password)

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* 에러 메시지 */}
      {error && (
        <div className="p-4 bg-accent-danger/10 border border-accent-danger/30 rounded-lg flex items-start gap-3">
          <svg className="w-5 h-5 text-accent-danger mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="text-sm font-medium text-accent-danger">회원가입 실패</p>
            <p className="text-sm text-accent-danger/80 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* 사용자명 입력 */}
      <div>
        <label htmlFor="username" className="block text-sm font-medium text-text-secondary mb-2">
          사용자명 <span className="text-accent-danger">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onBlur={() => setTouched(prev => ({ ...prev, username: true }))}
            placeholder="영문, 숫자, 밑줄 (3-50자)"
            autoComplete="username"
            className={`w-full pl-10 pr-4 py-3 bg-theme-surface border rounded-lg text-text-primary placeholder-text-muted transition-colors focus:outline-none focus:ring-2
                       ${usernameError ? 'border-accent-danger/50 focus:ring-accent-danger/30 focus:border-accent-danger' :
                                        'border-theme-border focus:ring-accent-primary/30 focus:border-accent-primary'}`}
          />
        </div>
        {usernameError && <p className="mt-1.5 text-sm text-accent-danger">{usernameError}</p>}
      </div>

      {/* 이름 입력 (선택) */}
      <div>
        <label htmlFor="fullName" className="block text-sm font-medium text-text-secondary mb-2">
          이름 <span className="text-text-muted">(선택)</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <input
            id="fullName"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            onBlur={() => setTouched(prev => ({ ...prev, fullName: true }))}
            placeholder="홍길동"
            autoComplete="name"
            className={`w-full pl-10 pr-4 py-3 bg-theme-surface border rounded-lg text-text-primary placeholder-text-muted transition-colors focus:outline-none focus:ring-2
                       ${fullNameError ? 'border-accent-danger/50 focus:ring-accent-danger/30 focus:border-accent-danger' :
                                        'border-theme-border focus:ring-accent-primary/30 focus:border-accent-primary'}`}
          />
        </div>
        {fullNameError && <p className="mt-1.5 text-sm text-accent-danger">{fullNameError}</p>}
      </div>

      {/* 이메일 입력 */}
      <div>
        <label htmlFor="register-email" className="block text-sm font-medium text-text-secondary mb-2">
          이메일 <span className="text-accent-danger">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
            </svg>
          </div>
          <input
            id="register-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onBlur={() => setTouched(prev => ({ ...prev, email: true }))}
            placeholder="example@email.com"
            autoComplete="email"
            className={`w-full pl-10 pr-4 py-3 bg-theme-surface border rounded-lg text-text-primary placeholder-text-muted transition-colors focus:outline-none focus:ring-2
                       ${emailError ? 'border-accent-danger/50 focus:ring-accent-danger/30 focus:border-accent-danger' :
                                     'border-theme-border focus:ring-accent-primary/30 focus:border-accent-primary'}`}
          />
        </div>
        {emailError && <p className="mt-1.5 text-sm text-accent-danger">{emailError}</p>}
      </div>

      {/* 비밀번호 입력 */}
      <div>
        <label htmlFor="register-password" className="block text-sm font-medium text-text-secondary mb-2">
          비밀번호 <span className="text-accent-danger">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <input
            id="register-password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onBlur={() => setTouched(prev => ({ ...prev, password: true }))}
            placeholder="8자 이상, 대/소문자, 숫자, 특수문자 포함"
            autoComplete="new-password"
            className={`w-full pl-10 pr-12 py-3 bg-theme-surface border rounded-lg text-text-primary placeholder-text-muted transition-colors focus:outline-none focus:ring-2
                       ${passwordError ? 'border-accent-danger/50 focus:ring-accent-danger/30 focus:border-accent-danger' :
                                        'border-theme-border focus:ring-accent-primary/30 focus:border-accent-primary'}`}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-text-muted hover:text-text-secondary"
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
        {passwordError && <p className="mt-1.5 text-sm text-accent-danger">{passwordError}</p>}

        {/* 비밀번호 강도 표시 */}
        {password && (
          <div className="mt-2">
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map(i => (
                <div
                  key={i}
                  className={`h-1 flex-1 rounded-full transition-colors ${
                    i <= passwordStrength.level ? passwordStrength.color : 'bg-theme-border'
                  }`}
                />
              ))}
            </div>
            <p className="text-xs text-text-muted mt-1">
              비밀번호 강도: <span className={passwordStrength.level <= 1 ? 'text-accent-danger' : passwordStrength.level <= 3 ? 'text-accent-warning' : 'text-accent-success'}>{passwordStrength.text}</span>
            </p>
          </div>
        )}

        {/* 비밀번호 요구사항 */}
        <div className="mt-2 text-xs text-text-muted">
          <p className="font-medium mb-1">비밀번호 요구사항:</p>
          <ul className="space-y-0.5 ml-3">
            <li className={password.length >= 8 ? 'text-accent-success' : ''}>8자 이상</li>
            <li className={/[A-Z]/.test(password) ? 'text-accent-success' : ''}>대문자 1개 이상</li>
            <li className={/[a-z]/.test(password) ? 'text-accent-success' : ''}>소문자 1개 이상</li>
            <li className={/[0-9]/.test(password) ? 'text-accent-success' : ''}>숫자 1개 이상</li>
            <li className={/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password) ? 'text-accent-success' : ''}>특수문자 1개 이상</li>
          </ul>
        </div>
      </div>

      {/* 비밀번호 확인 */}
      <div>
        <label htmlFor="confirm-password" className="block text-sm font-medium text-text-secondary mb-2">
          비밀번호 확인 <span className="text-accent-danger">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <input
            id="confirm-password"
            type={showPassword ? 'text' : 'password'}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            onBlur={() => setTouched(prev => ({ ...prev, confirmPassword: true }))}
            placeholder="비밀번호 재입력"
            autoComplete="new-password"
            className={`w-full pl-10 pr-4 py-3 bg-theme-surface border rounded-lg text-text-primary placeholder-text-muted transition-colors focus:outline-none focus:ring-2
                       ${confirmPasswordError ? 'border-accent-danger/50 focus:ring-accent-danger/30 focus:border-accent-danger' :
                                               'border-theme-border focus:ring-accent-primary/30 focus:border-accent-primary'}`}
          />
        </div>
        {confirmPasswordError && <p className="mt-1.5 text-sm text-accent-danger">{confirmPasswordError}</p>}
      </div>

      {/* 약관 동의 */}
      <div className="flex items-start gap-3">
        <input
          id="agree-terms"
          type="checkbox"
          checked={agreeTerms}
          onChange={(e) => setAgreeTerms(e.target.checked)}
          className="mt-1 w-4 h-4 text-accent-primary border-theme-border rounded focus:ring-accent-primary"
        />
        <label htmlFor="agree-terms" className="text-sm text-text-secondary">
          <span className="text-accent-primary hover:underline cursor-pointer">이용약관</span> 및{' '}
          <span className="text-accent-primary hover:underline cursor-pointer">개인정보 처리방침</span>에 동의합니다
        </label>
      </div>

      {/* 회원가입 버튼 */}
      <button
        type="submit"
        disabled={isLoading || !agreeTerms}
        className={`w-full py-3 px-4 rounded-lg font-medium text-white transition-all
                   ${isLoading || !agreeTerms ? 'bg-accent-primary/50 cursor-not-allowed' :
                                               'bg-accent-primary hover:bg-accent-primary/90 active:bg-accent-primary/80'}`}
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            가입 중...
          </span>
        ) : (
          '회원가입'
        )}
      </button>

      {/* 로그인 링크 */}
      {onSwitchToLogin && (
        <div className="text-center">
          <p className="text-sm text-text-secondary">
            이미 계정이 있으신가요?{' '}
            <button
              type="button"
              onClick={onSwitchToLogin}
              className="text-accent-primary hover:text-accent-primary/80 font-medium hover:underline"
            >
              로그인
            </button>
          </p>
        </div>
      )}
    </form>
  )
}

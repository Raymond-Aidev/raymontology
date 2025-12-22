import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

interface LoginFormProps {
  onSuccess?: () => void
  onSwitchToRegister?: () => void
}

export default function LoginForm({ onSuccess, onSwitchToRegister }: LoginFormProps) {
  const { login, isLoading, error, clearError } = useAuthStore()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [touched, setTouched] = useState({ email: false, password: false })

  // 유효성 검사
  const emailError = touched.email && !email ? '이메일을 입력해주세요' :
                     touched.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? '유효한 이메일 형식이 아닙니다' : ''
  const passwordError = touched.password && !password ? '비밀번호를 입력해주세요' :
                        touched.password && password.length < 4 ? '비밀번호는 4자 이상이어야 합니다' : ''

  const isValid = email && password && !emailError && !passwordError

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setTouched({ email: true, password: true })

    if (!isValid) return

    clearError()
    const success = await login({ email, password })
    if (success && onSuccess) {
      onSuccess()
    }
  }, [email, password, isValid, login, clearError, onSuccess])

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* 에러 메시지 */}
      {error && (
        <div className="p-4 bg-accent-danger/10 border border-accent-danger/30 rounded-lg flex items-start gap-3">
          <svg className="w-5 h-5 text-accent-danger mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="text-sm font-medium text-accent-danger">로그인 실패</p>
            <p className="text-sm text-accent-danger/80 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* 이메일 입력 */}
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-text-secondary mb-2">
          이메일
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
            </svg>
          </div>
          <input
            id="email"
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
        {emailError && (
          <p className="mt-1.5 text-sm text-accent-danger">{emailError}</p>
        )}
      </div>

      {/* 비밀번호 입력 */}
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-text-secondary mb-2">
          비밀번호
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <input
            id="password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onBlur={() => setTouched(prev => ({ ...prev, password: true }))}
            placeholder="비밀번호 입력"
            autoComplete="current-password"
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
        {passwordError && (
          <p className="mt-1.5 text-sm text-accent-danger">{passwordError}</p>
        )}

        {/* 비밀번호 찾기 링크 */}
        <div className="text-right mt-2">
          <Link
            to="/forgot-password"
            className="text-sm text-accent-primary hover:text-accent-primary/80 hover:underline"
          >
            비밀번호를 잊으셨나요?
          </Link>
        </div>
      </div>

      {/* 로그인 버튼 */}
      <button
        type="submit"
        disabled={isLoading}
        className={`w-full py-3 px-4 rounded-lg font-medium text-white transition-all
                   ${isLoading ? 'bg-accent-primary/50 cursor-not-allowed' :
                                'bg-accent-primary hover:bg-accent-primary/90 active:bg-accent-primary/80'}`}
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            로그인 중...
          </span>
        ) : (
          '로그인'
        )}
      </button>

      {/* 소셜 로그인 구분선 */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-theme-border" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-theme-card text-text-muted">또는</span>
        </div>
      </div>

      {/* 소셜 로그인 버튼 */}
      <div className="space-y-3">
        {/* Google 로그인 */}
        <a
          href={`${import.meta.env.VITE_API_URL || ''}/api/auth/google`}
          className="w-full flex items-center justify-center gap-3 py-3 px-4 border border-theme-border rounded-lg hover:bg-theme-hover transition-colors"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          <span className="text-text-primary font-medium">Google로 계속하기</span>
        </a>

        {/* Kakao 로그인 */}
        <a
          href={`${import.meta.env.VITE_API_URL || ''}/api/auth/kakao`}
          className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-lg transition-colors"
          style={{ backgroundColor: '#FEE500' }}
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none">
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M12 4C7.029 4 3 7.164 3 11.073c0 2.507 1.674 4.712 4.2 5.985l-.856 3.212c-.077.29.248.517.502.35l3.845-2.567c.428.037.864.057 1.309.057 4.971 0 9-3.164 9-7.073S16.971 4 12 4z"
              fill="#3C1E1E"
            />
          </svg>
          <span className="font-medium" style={{ color: '#3C1E1E' }}>카카오로 계속하기</span>
        </a>
      </div>

      {/* 회원가입 링크 */}
      {onSwitchToRegister && (
        <div className="text-center">
          <p className="text-sm text-text-secondary">
            계정이 없으신가요?{' '}
            <button
              type="button"
              onClick={onSwitchToRegister}
              className="text-accent-primary hover:text-accent-primary/80 font-medium hover:underline"
            >
              회원가입
            </button>
          </p>
        </div>
      )}
    </form>
  )
}

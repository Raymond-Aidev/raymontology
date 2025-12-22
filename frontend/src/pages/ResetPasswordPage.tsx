import { useState, useMemo } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import apiClient from '../api/client'

function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const [error, setError] = useState('')

  // 비밀번호 규칙 검증
  const validatePassword = (pwd: string) => {
    if (!pwd) return '비밀번호를 입력해주세요'
    if (pwd.length < 8) return '비밀번호는 8자 이상이어야 합니다'
    if (!/[A-Z]/.test(pwd)) return '대문자를 1개 이상 포함해야 합니다'
    if (!/[a-z]/.test(pwd)) return '소문자를 1개 이상 포함해야 합니다'
    if (!/[0-9]/.test(pwd)) return '숫자를 1개 이상 포함해야 합니다'
    if (!/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(pwd)) return '특수문자를 1개 이상 포함해야 합니다'
    return ''
  }

  const passwordError = password ? validatePassword(password) : ''
  const confirmError = confirmPassword && password !== confirmPassword ? '비밀번호가 일치하지 않습니다' : ''
  const isValid = password && confirmPassword && !passwordError && !confirmError

  // 비밀번호 강도
  const passwordStrength = useMemo(() => {
    if (!password) return { level: 0, text: '', color: '' }
    let strength = 0
    if (password.length >= 8) strength++
    if (password.length >= 12) strength++
    if (/[A-Z]/.test(password)) strength++
    if (/[a-z]/.test(password)) strength++
    if (/[0-9]/.test(password)) strength++
    if (/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password)) strength++

    if (strength <= 2) return { level: 1, text: '약함', color: 'bg-red-500' }
    if (strength <= 4) return { level: 3, text: '보통', color: 'bg-yellow-500' }
    return { level: 5, text: '강함', color: 'bg-green-500' }
  }, [password])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValid || !token) return

    setError('')
    setIsLoading(true)

    try {
      await apiClient.post('/api/auth/reset-password', {
        token,
        new_password: password
      })
      setIsSuccess(true)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || '비밀번호 재설정 중 오류가 발생했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  // 토큰이 없는 경우
  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-bg p-4">
        <div className="w-full max-w-md">
          <div className="bg-dark-card border border-dark-border rounded-2xl shadow-xl p-8 text-center">
            <div className="w-16 h-16 bg-accent-danger/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-8 h-8 text-accent-danger" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-text-primary mb-3">유효하지 않은 링크</h2>
            <p className="text-text-secondary mb-6">
              비밀번호 재설정 링크가 유효하지 않습니다.
              다시 비밀번호 찾기를 시도해주세요.
            </p>
            <Link
              to="/forgot-password"
              className="inline-block w-full py-3 px-4 bg-accent-primary text-white rounded-lg font-medium hover:bg-accent-primary/90 transition-colors"
            >
              비밀번호 찾기
            </Link>
          </div>
        </div>
      </div>
    )
  }

  // 성공 화면
  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-bg p-4">
        <div className="w-full max-w-md">
          <div className="bg-dark-card border border-dark-border rounded-2xl shadow-xl p-8 text-center">
            <div className="w-16 h-16 bg-accent-success/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-8 h-8 text-accent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-text-primary mb-3">비밀번호 변경 완료</h2>
            <p className="text-text-secondary mb-6">
              비밀번호가 성공적으로 변경되었습니다.
              새 비밀번호로 로그인해주세요.
            </p>
            <button
              onClick={() => navigate('/login')}
              className="w-full py-3 px-4 bg-accent-primary text-white rounded-lg font-medium hover:bg-accent-primary/90 transition-colors"
            >
              로그인하기
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-bg p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/">
            <img
              src="/logo.png?v=2"
              alt="Raymond Partners"
              className="h-14 w-auto object-contain mx-auto"
            />
          </Link>
        </div>

        <div className="bg-dark-card border border-dark-border rounded-2xl shadow-xl p-8">
          <h2 className="text-2xl font-bold text-text-primary mb-2">새 비밀번호 설정</h2>
          <p className="text-text-secondary mb-6">
            새로운 비밀번호를 입력해주세요.
          </p>

          {error && (
            <div className="mb-6 p-4 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
              <p className="text-sm text-accent-danger">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* 새 비밀번호 */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-text-secondary mb-2">
                새 비밀번호
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
                  placeholder="8자 이상, 대/소문자, 숫자, 특수문자 포함"
                  className={`w-full pl-10 pr-12 py-3 bg-dark-surface border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 transition-colors
                             ${passwordError ? 'border-accent-danger/50 focus:ring-accent-danger/30' : 'border-dark-border focus:ring-accent-primary/50 focus:border-accent-primary'}`}
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
                          i <= passwordStrength.level ? passwordStrength.color : 'bg-dark-border'
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
                비밀번호 확인
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
                  placeholder="비밀번호 재입력"
                  className={`w-full pl-10 pr-4 py-3 bg-dark-surface border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 transition-colors
                             ${confirmError ? 'border-accent-danger/50 focus:ring-accent-danger/30' : 'border-dark-border focus:ring-accent-primary/50 focus:border-accent-primary'}`}
                />
              </div>
              {confirmError && <p className="mt-1.5 text-sm text-accent-danger">{confirmError}</p>}
            </div>

            <button
              type="submit"
              disabled={isLoading || !isValid}
              className={`w-full py-3 px-4 rounded-lg font-medium text-white transition-all
                         ${isLoading || !isValid ? 'bg-accent-primary/50 cursor-not-allowed' : 'bg-accent-primary hover:bg-accent-primary/90'}`}
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  변경 중...
                </span>
              ) : (
                '비밀번호 변경'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

export default ResetPasswordPage

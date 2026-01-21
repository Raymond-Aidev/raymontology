import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore, selectUserName } from '../../store/authStore'
import { ApiStatusDot } from './ApiStatusIndicator'
import RaymondsRiskLogo from './RaymondsRiskLogo'
import UsageIndicator from './UsageIndicator'

function Header() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const navigate = useNavigate()
  const { user, isAuthenticated, logout } = useAuthStore()
  const displayName = useAuthStore(selectUserName)

  return (
    <header className="bg-dark-surface/80 backdrop-blur-xl border-b border-dark-border sticky top-0 z-50">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Logo + API Status */}
          <div className="flex items-center gap-4">
            <Link to="/" className="inline-block">
              <RaymondsRiskLogo size="md" variant="compact" />
            </Link>
            {/* API Status */}
            <div className="hidden sm:flex items-center gap-2 px-2 py-1 bg-dark-card rounded-full border border-dark-border">
              <ApiStatusDot className="scale-75" />
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            <Link
              to="/"
              className="px-3 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-dark-hover rounded-lg transition-all"
            >
              검색
            </Link>
            <Link
              to="/viewed-companies"
              className="px-3 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-dark-hover rounded-lg transition-all"
            >
              조회한 기업
            </Link>
            <Link
              to="/about"
              className="px-3 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-dark-hover rounded-lg transition-all"
            >
              서비스 소개
            </Link>
            <Link
              to="/contact"
              className="px-3 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-dark-hover rounded-lg transition-all"
            >
              문의
            </Link>
            <Link
              to="/service-application"
              className="px-3 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-dark-hover rounded-lg transition-all"
            >
              서비스 이용신청
            </Link>
          </nav>

          {/* User Menu (Desktop) */}
          <div className="hidden md:flex items-center gap-3">
            {/* Usage Indicator */}
            <UsageIndicator />

            {isAuthenticated && user ? (
              <div className="relative">
                <button
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="flex items-center gap-2 px-3 py-1.5 bg-dark-card border border-dark-border rounded-lg hover:border-dark-hover transition-all"
                >
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                    user.is_superuser
                      ? 'bg-gradient-to-br from-accent-primary to-purple-500'
                      : 'bg-dark-hover'
                  }`}>
                    <span className="text-xs font-medium text-white">
                      {displayName.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <span className="text-sm text-text-secondary">{displayName}</span>
                  <svg className={`w-4 h-4 text-text-muted transition-transform ${isUserMenuOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* Dropdown */}
                {isUserMenuOpen && (
                  <div className="absolute right-0 mt-2 w-56 bg-dark-card border border-dark-border rounded-xl shadow-card-hover py-1 animate-scale-in">
                    <div className="px-4 py-3 border-b border-dark-border">
                      <p className="text-sm font-medium text-text-primary">{displayName}</p>
                      <p className="text-xs text-text-muted mt-0.5">{user.email}</p>
                      {user.is_superuser && (
                        <span className="inline-block mt-2 px-2 py-0.5 text-xs bg-accent-primary/20 text-accent-primary rounded-full">
                          관리자
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => {
                        logout()
                        setIsUserMenuOpen(false)
                        navigate('/')
                      }}
                      className="w-full text-left px-4 py-2.5 text-sm text-accent-danger hover:bg-accent-danger/10 transition-colors flex items-center gap-2"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                      </svg>
                      로그아웃
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Link
                to="/login"
                className="px-4 py-2 text-sm font-medium text-white bg-accent-primary hover:bg-accent-primary/90 rounded-lg transition-all shadow-glow"
              >
                로그인
              </Link>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2 rounded-lg hover:bg-dark-hover text-text-secondary"
            aria-label="메뉴 열기"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {isMobileMenuOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-dark-border py-4 animate-slide-down">
            <nav className="flex flex-col gap-1">
              <Link
                to="/"
                onClick={() => setIsMobileMenuOpen(false)}
                className="px-4 py-2.5 text-sm text-text-secondary hover:text-text-primary hover:bg-dark-hover rounded-lg transition-all"
              >
                검색
              </Link>
              <Link
                to="/viewed-companies"
                onClick={() => setIsMobileMenuOpen(false)}
                className="px-4 py-2.5 text-sm text-text-secondary hover:text-text-primary hover:bg-dark-hover rounded-lg transition-all"
              >
                조회한 기업
              </Link>
              <Link
                to="/about"
                onClick={() => setIsMobileMenuOpen(false)}
                className="px-4 py-2.5 text-sm text-text-secondary hover:text-text-primary hover:bg-dark-hover rounded-lg transition-all"
              >
                서비스 소개
              </Link>
              <Link
                to="/contact"
                onClick={() => setIsMobileMenuOpen(false)}
                className="px-4 py-2.5 text-sm text-text-secondary hover:text-text-primary hover:bg-dark-hover rounded-lg transition-all"
              >
                문의
              </Link>
              <Link
                to="/service-application"
                onClick={() => setIsMobileMenuOpen(false)}
                className="px-4 py-2.5 text-sm text-text-secondary hover:text-text-primary hover:bg-dark-hover rounded-lg transition-all"
              >
                서비스 이용신청
              </Link>
              <div className="my-2 border-t border-dark-border" />
              {isAuthenticated && user ? (
                <div className="px-4 space-y-3">
                  <div className="flex items-center gap-3 py-2">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      user.is_superuser
                        ? 'bg-gradient-to-br from-accent-primary to-purple-500'
                        : 'bg-dark-hover'
                    }`}>
                      <span className="text-sm font-medium text-white">
                        {displayName.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-text-primary">{displayName}</p>
                      <p className="text-xs text-text-muted">{user.email}</p>
                    </div>
                    {user.is_superuser && (
                      <span className="ml-auto px-2 py-0.5 text-xs bg-accent-primary/20 text-accent-primary rounded-full">
                        관리자
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => {
                      logout()
                      setIsMobileMenuOpen(false)
                      navigate('/')
                    }}
                    className="w-full px-4 py-2.5 text-sm font-medium text-accent-danger bg-accent-danger/10 rounded-lg hover:bg-accent-danger/20 transition-colors"
                  >
                    로그아웃
                  </button>
                </div>
              ) : (
                <Link
                  to="/login"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="mx-4 px-4 py-2.5 text-center text-sm font-medium text-white bg-accent-primary rounded-lg"
                >
                  로그인
                </Link>
              )}
            </nav>
          </div>
        )}
      </div>
    </header>
  )
}

export default Header

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { BarChart3, Menu, X, User, LogOut, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useState, useEffect } from 'react';
import { useAuthStore } from '@/lib/auth';
import { CompanySearchBar } from '@/components/company-search-bar';

const navItems = [
  { href: '/', label: '홈' },
  { href: '/screener', label: '스크리너' },
  { href: '/ma-target', label: '적대적 M&A' },
  { href: '/methodology', label: '방법론' },
];

export function Header() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const { user, isAuthenticated, logout } = useAuthStore();

  // Hydration 문제 방지 (requestAnimationFrame으로 setState 지연)
  useEffect(() => {
    const rafId = requestAnimationFrame(() => {
      setMounted(true);
    });
    return () => cancelAnimationFrame(rafId);
  }, []);

  const handleLogout = () => {
    logout();
    setUserMenuOpen(false);
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-black/95 backdrop-blur supports-[backdrop-filter]:bg-black/80">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-[#5E6AD2] text-white">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold text-white">RaymondsIndex</span>
              <span className="text-[10px] text-zinc-500 -mt-1">2025</span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-4">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'text-sm font-medium transition-colors hover:text-white',
                  pathname === item.href
                    ? 'text-white'
                    : 'text-zinc-400'
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          {/* Search Bar - 데스크톱 */}
          <div className="hidden lg:block flex-1 max-w-md mx-4">
            <CompanySearchBar
              placeholder="기업 검색..."
              size="sm"
            />
          </div>

          {/* Auth Section */}
          <div className="hidden md:flex items-center gap-2">
            {mounted && isAuthenticated && user ? (
              <div className="relative">
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/5 transition-colors"
                >
                  <div className="w-8 h-8 bg-[#5E6AD2]/20 text-[#8B95E8] rounded-full flex items-center justify-center">
                    <User className="w-4 h-4" />
                  </div>
                  <span className="text-sm font-medium text-zinc-300">
                    {user.full_name || user.username}
                  </span>
                </button>

                {/* User Dropdown */}
                {userMenuOpen && (
                  <>
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setUserMenuOpen(false)}
                    />
                    <div className="absolute right-0 mt-2 w-48 bg-zinc-900 border border-white/10 rounded-lg shadow-xl shadow-black/50 py-1 z-20">
                      <div className="px-4 py-2 border-b border-white/10">
                        <p className="text-sm font-medium text-white">{user.full_name || user.username}</p>
                        <p className="text-xs text-zinc-500">{user.email}</p>
                      </div>
                      {user.is_superuser && (
                        <Link
                          href="/admin"
                          onClick={() => setUserMenuOpen(false)}
                          className="flex items-center gap-2 px-4 py-2 text-sm text-zinc-300 hover:bg-white/5 hover:text-white"
                        >
                          <Settings className="w-4 h-4" />
                          관리자
                        </Link>
                      )}
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10"
                      >
                        <LogOut className="w-4 h-4" />
                        로그아웃
                      </button>
                    </div>
                  </>
                )}
              </div>
            ) : mounted ? (
              <>
                <Link
                  href="/login"
                  className="px-4 py-2 text-sm font-medium text-zinc-400 hover:text-white transition-colors"
                >
                  로그인
                </Link>
                <Link
                  href="/signup"
                  className="px-4 py-2 text-sm font-medium text-white bg-[#5E6AD2] hover:bg-[#7C85E0] rounded-lg transition-colors"
                >
                  회원가입
                </Link>
              </>
            ) : null}
          </div>

          {/* Mobile Menu Button */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden text-zinc-400 hover:text-white"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </Button>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <nav className="md:hidden py-4 border-t border-white/10">
            {/* 모바일 검색바 */}
            <div className="mb-4 lg:hidden">
              <CompanySearchBar
                placeholder="기업 검색..."
                size="sm"
              />
            </div>

            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'block py-2 text-sm font-medium transition-colors hover:text-white',
                  pathname === item.href
                    ? 'text-white'
                    : 'text-zinc-400'
                )}
                onClick={() => setMobileMenuOpen(false)}
              >
                {item.label}
              </Link>
            ))}

            {/* Mobile Auth Links */}
            <div className="mt-4 pt-4 border-t border-white/10">
              {mounted && isAuthenticated && user ? (
                <>
                  <div className="flex items-center gap-2 py-2">
                    <div className="w-8 h-8 bg-[#5E6AD2]/20 text-[#8B95E8] rounded-full flex items-center justify-center">
                      <User className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{user.full_name || user.username}</p>
                      <p className="text-xs text-zinc-500">{user.email}</p>
                    </div>
                  </div>
                  {user.is_superuser && (
                    <Link
                      href="/admin"
                      className="flex items-center gap-2 py-2 text-sm text-zinc-300 hover:text-white"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      <Settings className="w-4 h-4" />
                      관리자
                    </Link>
                  )}
                  <button
                    onClick={() => {
                      handleLogout();
                      setMobileMenuOpen(false);
                    }}
                    className="flex items-center gap-2 py-2 text-sm text-red-400"
                  >
                    <LogOut className="w-4 h-4" />
                    로그아웃
                  </button>
                </>
              ) : mounted ? (
                <div className="flex flex-col gap-2">
                  <Link
                    href="/login"
                    className="block py-2 text-sm font-medium text-zinc-400 hover:text-white"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    로그인
                  </Link>
                  <Link
                    href="/signup"
                    className="block py-2 text-sm font-medium text-[#8B95E8] hover:text-[#5E6AD2]"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    회원가입
                  </Link>
                </div>
              ) : null}
            </div>
          </nav>
        )}
      </div>
    </header>
  );
}

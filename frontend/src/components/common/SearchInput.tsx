import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { searchCompanies } from '../../api/company'
import { riskLevelColors, gradeColors } from '../../types/company'
import { useGraphStore } from '../../store'
import type { CompanySearchResult } from '../../types/company'

interface SearchInputProps {
  placeholder?: string
  onSelect?: (company: CompanySearchResult) => void
  autoFocus?: boolean
  size?: 'sm' | 'md' | 'lg'
}

// 최근 검색어 저장 키
const RECENT_SEARCHES_KEY = 'raymontology_recent_searches'
const MAX_RECENT_SEARCHES = 5

export default function SearchInput({
  placeholder = '회사명 또는 종목코드를 입력하세요',
  onSelect,
  autoFocus = false,
  size = 'lg',
}: SearchInputProps) {
  const navigate = useNavigate()
  const clearNavigation = useGraphStore((state) => state.clearNavigation)

  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<CompanySearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [recentSearches, setRecentSearches] = useState<CompanySearchResult[]>([])

  const searchRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // 최근 검색어 로드
  useEffect(() => {
    const saved = localStorage.getItem(RECENT_SEARCHES_KEY)
    if (saved) {
      try {
        setRecentSearches(JSON.parse(saved))
      } catch {
        setRecentSearches([])
      }
    }
  }, [])

  // 검색 로직 (debounce 300ms)
  useEffect(() => {
    if (query.length < 2) {
      setSearchResults([])
      return
    }

    setIsSearching(true)
    const timer = setTimeout(async () => {
      try {
        const results = await searchCompanies(query, 20)
        setSearchResults(results)
        setShowResults(true)
      } catch (error) {
        console.error('검색 실패:', error)
        setSearchResults([])
      } finally {
        setIsSearching(false)
        setSelectedIndex(-1)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [query])

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 최근 검색어 저장
  const saveToRecentSearches = useCallback((company: CompanySearchResult) => {
    setRecentSearches(prev => {
      const filtered = prev.filter(c => c.id !== company.id)
      const updated = [company, ...filtered].slice(0, MAX_RECENT_SEARCHES)
      localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated))
      return updated
    })
  }, [])

  // 회사 선택
  const handleSelectCompany = useCallback((company: CompanySearchResult) => {
    setQuery('')
    setShowResults(false)
    saveToRecentSearches(company)

    if (onSelect) {
      onSelect(company)
    } else {
      // 새 검색 시 네비게이션 히스토리 초기화
      clearNavigation()
      // corp_code로 조회해야 CB 데이터가 함께 표시됨
      navigate(`/company/${company.corp_code}/graph`)
    }
  }, [navigate, onSelect, saveToRecentSearches, clearNavigation])

  // 최근 검색어 삭제
  const handleRemoveRecent = useCallback((e: React.MouseEvent, companyId: string) => {
    e.stopPropagation()
    setRecentSearches(prev => {
      const updated = prev.filter(c => c.id !== companyId)
      localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated))
      return updated
    })
  }, [])

  // 키보드 네비게이션
  const handleKeyDown = (e: React.KeyboardEvent) => {
    const currentList = query.length >= 2 ? searchResults : recentSearches

    if (!showResults || currentList.length === 0) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev =>
          prev < currentList.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1)
        break
      case 'Enter':
        e.preventDefault()
        if (selectedIndex >= 0 && selectedIndex < currentList.length) {
          handleSelectCompany(currentList[selectedIndex])
        }
        break
      case 'Escape':
        setShowResults(false)
        break
    }
  }

  // 검색어 하이라이트 (다크 테마용)
  const highlightMatch = (text: string, searchQuery: string) => {
    if (!searchQuery || searchQuery.length < 2) return text

    const regex = new RegExp(`(${searchQuery})`, 'gi')
    const parts = text.split(regex)

    return parts.map((part, index) =>
      regex.test(part) ? (
        <mark key={index} className="bg-accent-primary/30 text-accent-primary rounded px-0.5">
          {part}
        </mark>
      ) : (
        part
      )
    )
  }

  // 사이즈별 스타일
  const sizeStyles = {
    sm: 'pl-10 pr-10 py-2 text-sm',
    md: 'pl-11 pr-11 py-3 text-base',
    lg: 'pl-12 pr-12 py-4 text-lg',
  }

  const iconSizes = {
    sm: 'h-4 w-4',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  }

  const showRecentSearches = query.length < 2 && recentSearches.length > 0
  const showSearchResults = query.length >= 2 && searchResults.length > 0
  const showNoResults = query.length >= 2 && searchResults.length === 0 && !isSearching

  return (
    <div ref={searchRef} className="w-full relative">
      <div className="relative">
        {/* 검색 아이콘 */}
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <svg
            className={`${iconSizes[size]} text-text-muted`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

        {/* 검색 입력 - 다크 테마 */}
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setShowResults(true)}
          placeholder={placeholder}
          autoFocus={autoFocus}
          className={`w-full ${sizeStyles[size]}
                     bg-dark-card border border-dark-border rounded-xl
                     text-text-primary placeholder-text-muted
                     focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20
                     hover:border-dark-hover hover:bg-dark-surface
                     transition-all duration-200 outline-none`}
        />

        {/* 로딩 스피너 */}
        {isSearching && (
          <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
            <div className={`${iconSizes[size]} border-2 border-accent-primary border-t-transparent rounded-full animate-spin`} />
          </div>
        )}

        {/* 클리어 버튼 */}
        {query && !isSearching && (
          <button
            onClick={() => {
              setQuery('')
              inputRef.current?.focus()
            }}
            className="absolute inset-y-0 right-0 pr-4 flex items-center
                       text-text-muted hover:text-text-secondary transition-colors"
          >
            <svg className={iconSizes[size]} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* 드롭다운 - 다크 테마 */}
      {showResults && (showRecentSearches || showSearchResults || showNoResults) && (
        <div className="absolute w-full mt-2 bg-dark-card border border-dark-border rounded-xl shadow-card-hover
                      max-h-96 overflow-y-auto z-50 animate-slide-down backdrop-blur-xl">

          {/* 최근 검색어 */}
          {showRecentSearches && (
            <div>
              <div className="px-4 py-2 bg-dark-surface border-b border-dark-border flex items-center justify-between">
                <span className="text-xs font-medium text-text-muted flex items-center gap-1">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  최근 검색
                </span>
                <button
                  onClick={() => {
                    localStorage.removeItem(RECENT_SEARCHES_KEY)
                    setRecentSearches([])
                  }}
                  className="text-xs text-text-muted hover:text-text-secondary transition-colors"
                >
                  전체 삭제
                </button>
              </div>
              <ul className="py-2">
                {recentSearches.map((company, index) => (
                  <li key={company.id}>
                    <button
                      onClick={() => handleSelectCompany(company)}
                      onMouseEnter={() => setSelectedIndex(index)}
                      className={`w-full px-4 py-3 flex items-center justify-between
                                 hover:bg-dark-hover transition-colors text-left
                                 ${selectedIndex === index ? 'bg-accent-primary/10 border-l-2 border-accent-primary' : ''}`}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-text-primary truncate">
                            {company.name}
                          </span>
                          <span className="text-xs text-text-muted font-mono">
                            {company.corp_code}
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={(e) => handleRemoveRecent(e, company.id)}
                        className="ml-2 p-1 text-text-muted hover:text-accent-danger transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 검색 결과 */}
          {showSearchResults && (
            <ul className="py-2">
              {searchResults.map((company, index) => (
                <li key={company.id}>
                  <button
                    onClick={() => handleSelectCompany(company)}
                    onMouseEnter={() => setSelectedIndex(index)}
                    className={`w-full px-4 py-3 flex items-center justify-between
                               hover:bg-dark-hover transition-colors text-left
                               ${selectedIndex === index ? 'bg-accent-primary/10 border-l-2 border-accent-primary' : ''}`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-text-primary truncate">
                          {highlightMatch(company.name, query)}
                        </span>
                        <span className="text-xs text-text-muted font-mono">
                          {highlightMatch(company.corp_code, query)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-text-secondary">
                          CB <span className="text-accent-purple font-mono">{company.cb_count}</span>건
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      {company.investment_grade && (
                        <span className={`text-sm font-semibold font-mono ${gradeColors[company.investment_grade] || 'text-text-muted'}`}>
                          {company.investment_grade}
                        </span>
                      )}
                      {company.risk_level && (
                        <span className={`px-2 py-0.5 text-xs rounded-full ${riskLevelColors[company.risk_level]?.bg} ${riskLevelColors[company.risk_level]?.text}`}>
                          {riskLevelColors[company.risk_level]?.label}
                        </span>
                      )}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* 검색 결과 없음 */}
          {showNoResults && (
            <div className="px-4 py-8 text-center text-text-secondary">
              <svg className="w-12 h-12 mx-auto mb-3 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="font-medium text-text-primary">'{query}'에 대한 검색 결과가 없습니다</p>
              <p className="text-sm mt-1 text-text-muted">다른 검색어를 시도해보세요</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

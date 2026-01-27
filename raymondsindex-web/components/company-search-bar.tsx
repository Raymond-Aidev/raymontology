'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { useDebouncedSearch } from '@/hooks/use-search';
import { GradeBadge } from './grade-badge';
import { cn } from '@/lib/utils';

interface CompanySearchBarProps {
  placeholder?: string;
  className?: string;
  size?: 'sm' | 'lg';
}

export function CompanySearchBar({
  placeholder = '기업명 또는 종목코드로 검색',
  className,
  size = 'sm',
}: CompanySearchBarProps) {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { query, setQuery, data: results, isLoading } = useDebouncedSearch('', 200);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (companyId: string) => {
    setQuery('');
    setIsOpen(false);
    router.push(`/company/${companyId}`);
  };

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <div className="relative">
        <Search className={cn(
          'absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500',
          size === 'lg' ? 'w-5 h-5' : 'w-4 h-4'
        )} />
        <Input
          ref={inputRef}
          type="text"
          placeholder={placeholder}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          className={cn(
            'pl-10 pr-10',
            size === 'lg' && 'h-14 text-lg'
          )}
        />
        {query && (
          <button
            onClick={() => {
              setQuery('');
              inputRef.current?.focus();
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Search Results Dropdown */}
      {isOpen && query.length >= 1 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-zinc-900 rounded-lg border border-white/10 shadow-xl shadow-black/50 z-50 max-h-80 overflow-y-auto">
          {isLoading ? (
            <div className="p-4 text-center text-zinc-500">검색 중...</div>
          ) : results && results.length > 0 ? (
            <ul>
              {results.map((company) => (
                <li key={company.company_id}>
                  <button
                    onClick={() => handleSelect(company.company_id)}
                    className="w-full px-4 py-3 flex items-center gap-3 hover:bg-white/5 transition-colors text-left"
                  >
                    <GradeBadge grade={company.grade} size="sm" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-white truncate">
                        {company.company_name}
                      </p>
                      <p className="text-sm text-zinc-500">{company.stock_code}</p>
                    </div>
                    <span className="text-sm font-semibold text-zinc-300">
                      {company.total_score.toFixed(1)}점
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="p-4 text-center text-zinc-500">
              검색 결과가 없습니다
            </div>
          )}
        </div>
      )}
    </div>
  );
}

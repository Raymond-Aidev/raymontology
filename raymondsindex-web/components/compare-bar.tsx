'use client';

import { X, BarChart3 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GradeBadge } from '@/components/grade-badge';
import { useCompareStore, MAX_COMPARE_ITEMS } from '@/lib/compare-store';

export function CompareBar() {
  const { items, removeItem, clearAll, openModal } = useCompareStore();

  if (items.length === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg z-40">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          {/* 선택된 기업 목록 */}
          <div className="flex items-center gap-2 overflow-x-auto">
            <span className="text-sm font-medium text-gray-600 shrink-0">
              비교 ({items.length}/{MAX_COMPARE_ITEMS})
            </span>
            <div className="flex gap-2">
              {items.map((item) => (
                <div
                  key={item.company_id}
                  className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-full"
                >
                  <span className="text-sm font-medium">{item.company_name}</span>
                  <GradeBadge grade={item.grade} size="sm" />
                  <button
                    onClick={() => removeItem(item.company_id)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* 액션 버튼 */}
          <div className="flex items-center gap-2 shrink-0">
            <Button variant="ghost" size="sm" onClick={clearAll}>
              초기화
            </Button>
            <Button
              size="sm"
              onClick={openModal}
              disabled={items.length < 2}
            >
              <BarChart3 className="w-4 h-4 mr-1" />
              비교하기
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

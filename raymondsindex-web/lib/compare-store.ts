import { create } from 'zustand';
import type { RaymondsIndexResponse } from './types';

// 비교 대상 최대 개수
const MAX_COMPARE_ITEMS = 4;

interface CompareStore {
  items: RaymondsIndexResponse[];
  isOpen: boolean;

  // 액션
  addItem: (item: RaymondsIndexResponse) => void;
  removeItem: (companyId: string) => void;
  clearAll: () => void;
  isSelected: (companyId: string) => boolean;
  toggleItem: (item: RaymondsIndexResponse) => void;
  openModal: () => void;
  closeModal: () => void;
}

export const useCompareStore = create<CompareStore>((set, get) => ({
  items: [],
  isOpen: false,

  // 원자적 패턴: set() 콜백 내에서 모든 검사와 업데이트 수행
  addItem: (item) => {
    set((state) => {
      // 최대 개수 초과 검사
      if (state.items.length >= MAX_COMPARE_ITEMS) {
        return state; // 변경 없음
      }
      // 중복 검사
      if (state.items.some((i) => i.company_id === item.company_id)) {
        return state; // 변경 없음
      }
      return { items: [...state.items, item] };
    });
  },

  removeItem: (companyId) => {
    set((state) => ({
      items: state.items.filter((i) => i.company_id !== companyId),
    }));
  },

  clearAll: () => {
    set({ items: [], isOpen: false });
  },

  isSelected: (companyId) => {
    return get().items.some((i) => i.company_id === companyId);
  },

  // 원자적 토글: 단일 set() 호출로 검사와 업데이트 수행
  toggleItem: (item) => {
    set((state) => {
      const isCurrentlySelected = state.items.some((i) => i.company_id === item.company_id);
      if (isCurrentlySelected) {
        // 제거
        return { items: state.items.filter((i) => i.company_id !== item.company_id) };
      } else {
        // 추가 (최대 개수 검사)
        if (state.items.length >= MAX_COMPARE_ITEMS) {
          return state; // 변경 없음
        }
        return { items: [...state.items, item] };
      }
    });
  },

  openModal: () => {
    set({ isOpen: true });
  },

  closeModal: () => {
    set({ isOpen: false });
  },
}));

export { MAX_COMPARE_ITEMS };

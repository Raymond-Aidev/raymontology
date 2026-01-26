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

  addItem: (item) => {
    const { items } = get();
    if (items.length >= MAX_COMPARE_ITEMS) {
      return; // 최대 개수 초과
    }
    if (items.some((i) => i.company_id === item.company_id)) {
      return; // 이미 추가됨
    }
    set({ items: [...items, item] });
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

  toggleItem: (item) => {
    const { isSelected, addItem, removeItem } = get();
    if (isSelected(item.company_id)) {
      removeItem(item.company_id);
    } else {
      addItem(item);
    }
  },

  openModal: () => {
    set({ isOpen: true });
  },

  closeModal: () => {
    set({ isOpen: false });
  },
}));

export { MAX_COMPARE_ITEMS };

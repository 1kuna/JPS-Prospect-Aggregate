import { StateCreator } from 'zustand';

export interface ToastData {
  id: string;
  title: string;
  description: string;
  variant?: 'default' | 'destructive' | 'success';
  duration?: number;
}

export interface UIState {
  toasts: ToastData[];
  isNavOpen: boolean;
  
  // Actions
  addToast: (toast: Omit<ToastData, 'id'>) => void;
  removeToast: (id: string) => void;
  clearToasts: () => void;
  setNavOpen: (isOpen: boolean) => void;
  toggleNav: () => void;
}

export const uiSlice: StateCreator<UIState> = (set, get) => ({
  toasts: [],
  isNavOpen: true,
  
  addToast: (toast) => {
    const id = Math.random().toString(36).substring(2, 9);
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id }]
    }));
    
    // Auto-remove toast after duration (default 5 seconds)
    if (toast.duration !== 0) {
      setTimeout(() => {
        get().removeToast(id);
      }, toast.duration || 5000);
    }
    
    return id;
  },
  
  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id)
    }));
  },
  
  clearToasts: () => {
    set({ toasts: [] });
  },
  
  setNavOpen: (isOpen) => {
    set({ isNavOpen: isOpen });
  },
  
  toggleNav: () => {
    set((state) => ({ isNavOpen: !state.isNavOpen }));
  }
}); 
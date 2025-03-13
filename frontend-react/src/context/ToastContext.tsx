import React, { createContext, useContext, useState } from 'react';
import { useToast } from '@/hooks';

// Define the types for our toast notifications
interface ToastNotification {
  id: string;
  title: string;
  description: string;
  variant?: 'default' | 'destructive' | 'success';
  duration?: number;
}

// Define the context type
interface ToastContextType {
  addToast: (toast: Omit<ToastNotification, 'id'>) => void;
  removeToast: (id: string) => void;
  toasts: ToastNotification[];
}

// Create the context with a default value
const ToastContext = createContext<ToastContextType | undefined>(undefined);

// Generate a unique ID for each toast
const generateId = () => {
  return Math.random().toString(36).substring(2, 9);
};

// Create a provider component
export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastNotification[]>([]);
  const { toast: showToast } = useToast();

  // Add a new toast
  const addToast = (toast: Omit<ToastNotification, 'id'>) => {
    const id = generateId();
    setToasts((prev) => [...prev, { ...toast, id }]);
    
    // Also show the toast using the useToast hook
    showToast({
      ...toast,
      // If no duration is provided, use a default of 5 seconds
      duration: toast.duration || 5000,
    });
  };

  // Remove a toast by ID
  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  return (
    <ToastContext.Provider value={{ addToast, removeToast, toasts }}>
      {children}
    </ToastContext.Provider>
  );
};

// Create a hook to use the toast context
export const useGlobalToast = () => {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useGlobalToast must be used within a ToastProvider');
  }
  return context;
}; 
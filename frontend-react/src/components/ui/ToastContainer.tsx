import React, { useState, useEffect, createContext, useContext } from 'react';
import SimpleToast, { SimpleToastProps } from './SimpleToast';

// Define the context type
interface ToastContextType {
  addToast: (toast: Omit<SimpleToastProps, 'id' | 'onClose'>) => void;
  removeToast: (id: string) => void;
}

// Create the context
const ToastContext = createContext<ToastContextType | undefined>(undefined);

// Create a provider component
export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<SimpleToastProps[]>([]);

  // Add a new toast
  const addToast = (toast: Omit<SimpleToastProps, 'id' | 'onClose'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [
      ...prev,
      {
        ...toast,
        id,
        onClose: () => removeToast(id),
      },
    ]);
  };

  // Remove a toast by ID
  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <div className="toast-container">
        {toasts.map((toast) => (
          <SimpleToast key={toast.id} {...toast} />
        ))}
      </div>
    </ToastContext.Provider>
  );
};

// Create a hook to use the toast context
export const useToastContainer = () => {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToastContainer must be used within a ToastProvider');
  }
  return context;
};

// Export a standalone ToastContainer component
export const ToastContainer: React.FC = () => {
  const [toasts, setToasts] = useState<SimpleToastProps[]>([]);

  // Add a toast to the global window object for direct access
  useEffect(() => {
    // Define the global toast function
    const showToast = (props: Omit<SimpleToastProps, 'id' | 'onClose'>) => {
      const id = Math.random().toString(36).substring(2, 9);
      const toast = {
        ...props,
        id,
        onClose: () => {
          setToasts((prev) => prev.filter((t) => t.id !== id));
        },
      };
      setToasts((prev) => [...prev, toast]);
      return id;
    };

    // Add it to the window object
    (window as any).showToast = showToast;

    return () => {
      // Clean up
      delete (window as any).showToast;
    };
  }, []);

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <SimpleToast key={toast.id} {...toast} />
      ))}
    </div>
  );
};

export default ToastContainer; 
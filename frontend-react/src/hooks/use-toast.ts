import { useEffect, useState, useCallback } from 'react';

// Define placeholder types if they are used internally
type ToastProps = any; 
type ToastActionElement = React.ReactElement | any; // Define placeholder type

const TOAST_LIMIT = 1;
const TOAST_REMOVE_DELAY = 5000;

// Original type definition using ToastActionElement
type ToasterToast = ToastProps & {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: ToastActionElement; // Use the defined type
};

let count = 0;

function generateId() {
  count = (count + 1) % Number.MAX_SAFE_INTEGER;
  return count.toString();
}

interface State {
  toasts: ToasterToast[];
}

const toastTimeouts = new Map<string, ReturnType<typeof setTimeout>>();

// Create a singleton state that persists across hook instances
let globalToasts: ToasterToast[] = [];
let listeners: ((toasts: ToasterToast[]) => void)[] = [];

// Function to update global state and notify all listeners
function updateGlobalToasts(updater: (toasts: ToasterToast[]) => ToasterToast[]) {
  globalToasts = updater(globalToasts);
  listeners.forEach(listener => listener(globalToasts));
}

const useToast = () => {
  const [state, setState] = useState<State>({ toasts: globalToasts });

  // Register this component as a listener for global toast updates
  useEffect(() => {
    const listener = (toasts: ToasterToast[]) => {
      setState({ toasts });
    };
    
    listeners.push(listener);
    return () => {
      listeners = listeners.filter(l => l !== listener);
    };
  }, []);

  const toast = useCallback(
    ({ ...props }: Omit<ToasterToast, "id">) => {
      const id = generateId();
      console.log(`[useToast] Creating toast with ID: ${id}`, props);

      // Create the toast object
      const newToast: ToasterToast = {
        ...props,
        id,
        open: true,
        onOpenChange: (open: any) => {
          if (!open) {
            console.log(`[useToast] Dismissing toast with ID: ${id}`);
            updateGlobalToasts(toasts => 
              toasts.map(t => t.id === id ? { ...t, open: false } : t)
            );
            
            // Schedule removal after animation
            setTimeout(() => {
              console.log(`[useToast] Removing toast with ID: ${id}`);
              updateGlobalToasts(toasts => toasts.filter(t => t.id !== id));
            }, 300);
          }
        },
      };

      // Add toast to global state
      console.log(`[useToast] Adding toast to global state: ${id}`);
      updateGlobalToasts(toasts => [newToast, ...toasts].slice(0, TOAST_LIMIT));

      // Set up auto-dismiss timeout
      const duration = props.duration || TOAST_REMOVE_DELAY;
      const timeout = setTimeout(() => {
        console.log(`[useToast] Auto-dismissing toast with ID: ${id}`);
        updateGlobalToasts(toasts => 
          toasts.map(t => t.id === id ? { ...t, open: false } : t)
        );
        
        // Schedule removal after animation
        setTimeout(() => {
          console.log(`[useToast] Auto-removing toast with ID: ${id}`);
          updateGlobalToasts(toasts => toasts.filter(t => t.id !== id));
        }, 300);
      }, duration);

      toastTimeouts.set(id, timeout);

      return {
        id,
        dismiss: () => {
          console.log(`[useToast] Manually dismissing toast with ID: ${id}`);
          if (toastTimeouts.has(id)) {
            clearTimeout(toastTimeouts.get(id));
            toastTimeouts.delete(id);
          }
          
          updateGlobalToasts(toasts => 
            toasts.map(t => t.id === id ? { ...t, open: false } : t)
          );
          
          // Schedule removal after animation
          setTimeout(() => {
            console.log(`[useToast] Manually removing toast with ID: ${id}`);
            updateGlobalToasts(toasts => toasts.filter(t => t.id !== id));
          }, 300);
        },
        update: (props: Partial<ToasterToast>) => {
          console.log(`[useToast] Updating toast with ID: ${id}`, props);
          updateGlobalToasts(toasts => 
            toasts.map(t => t.id === id ? { ...t, ...props } : t)
          );
        },
      };
    },
    []
  );

  return {
    toasts: state.toasts,
    toast,
    dismiss: (id: string) => {
      console.log(`[useToast] Dismissing toast with ID: ${id} from dismiss function`);
      if (toastTimeouts.has(id)) {
        clearTimeout(toastTimeouts.get(id));
        toastTimeouts.delete(id);
      }
      
      updateGlobalToasts(toasts => 
        toasts.map(t => t.id === id ? { ...t, open: false } : t)
      );
      
      // Schedule removal after animation
      setTimeout(() => {
        console.log(`[useToast] Removing toast with ID: ${id} from dismiss function`);
        updateGlobalToasts(toasts => toasts.filter(t => t.id !== id));
      }, 300);
    },
  };
};

export const toast = {
  // Define a default toast function
  default: (props: Omit<ToasterToast, "id">) => {
    const { toast } = useToast();
    return toast(props);
  },
  // Shorthand for success variant
  success: (props: Omit<ToasterToast, "id" | "variant">) => {
    const { toast } = useToast();
    return toast({ ...props, variant: "success" });
  },
  // Shorthand for destructive variant
  error: (props: Omit<ToasterToast, "id" | "variant">) => {
    const { toast } = useToast();
    return toast({ ...props, variant: "destructive" });
  },
}; 
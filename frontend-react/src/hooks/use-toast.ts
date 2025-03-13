import { useState, useEffect, useCallback } from "react";
import type { ToastActionElement, ToastProps } from "@/components/ui/toast";

const TOAST_LIMIT = 5;
const TOAST_REMOVE_DELAY = 5000;

type ToasterToast = ToastProps & {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: ToastActionElement;
};

const actionTypes = {
  ADD_TOAST: "ADD_TOAST",
  UPDATE_TOAST: "UPDATE_TOAST",
  DISMISS_TOAST: "DISMISS_TOAST",
  REMOVE_TOAST: "REMOVE_TOAST",
} as const;

let count = 0;

function generateId() {
  count = (count + 1) % Number.MAX_SAFE_INTEGER;
  return count.toString();
}

type ActionType = typeof actionTypes;

type Action =
  | {
      type: ActionType["ADD_TOAST"];
      toast: ToasterToast;
    }
  | {
      type: ActionType["UPDATE_TOAST"];
      toast: Partial<ToasterToast>;
      id: string;
    }
  | {
      type: ActionType["DISMISS_TOAST"];
      id: string;
    }
  | {
      type: ActionType["REMOVE_TOAST"];
      id: string;
    };

interface State {
  toasts: ToasterToast[];
}

const toastTimeouts = new Map<string, ReturnType<typeof setTimeout>>();

const reducer = (state: State, action: Action): State => {
  switch (action.type) {
    case actionTypes.ADD_TOAST:
      return {
        ...state,
        toasts: [action.toast, ...state.toasts].slice(0, TOAST_LIMIT),
      };

    case actionTypes.UPDATE_TOAST:
      return {
        ...state,
        toasts: state.toasts.map((t) =>
          t.id === action.id ? { ...t, ...action.toast } : t
        ),
      };

    case actionTypes.DISMISS_TOAST: {
      const { id } = action;

      // Cancel any existing timeout
      if (toastTimeouts.has(id)) {
        clearTimeout(toastTimeouts.get(id));
        toastTimeouts.delete(id);
      }

      return {
        ...state,
        toasts: state.toasts.map((t) =>
          t.id === id
            ? {
                ...t,
                open: false,
              }
            : t
        ),
      };
    }

    case actionTypes.REMOVE_TOAST:
      if (toastTimeouts.has(action.id)) {
        clearTimeout(toastTimeouts.get(action.id));
        toastTimeouts.delete(action.id);
      }

      return {
        ...state,
        toasts: state.toasts.filter((t) => t.id !== action.id),
      };

    default:
      return state;
  }
};

export function useToast() {
  const [state, setState] = useState<State>({ toasts: [] });

  const dispatch = useCallback((action: Action) => {
    setState((prevState) => reducer(prevState, action));
  }, []);

  const toast = useCallback(
    ({ ...props }: Omit<ToasterToast, "id">) => {
      const id = generateId();

      const update = (props: Partial<ToasterToast>) =>
        dispatch({
          type: actionTypes.UPDATE_TOAST,
          id,
          toast: { ...props },
        });

      const dismiss = () =>
        dispatch({ type: actionTypes.DISMISS_TOAST, id });

      dispatch({
        type: actionTypes.ADD_TOAST,
        toast: {
          ...props,
          id,
          open: true,
          onOpenChange: (open) => {
            if (!open) dismiss();
          },
        },
      });

      return {
        id,
        dismiss,
        update,
      };
    },
    [dispatch]
  );

  useEffect(() => {
    state.toasts.forEach((t) => {
      if (t.open && !toastTimeouts.has(t.id)) {
        const timeout = setTimeout(() => {
          dispatch({ type: actionTypes.DISMISS_TOAST, id: t.id });
        }, TOAST_REMOVE_DELAY);

        toastTimeouts.set(t.id, timeout);
      }
    });

    return () => {
      toastTimeouts.forEach((timeout) => clearTimeout(timeout));
      toastTimeouts.clear();
    };
  }, [state.toasts, dispatch]);

  return {
    ...state,
    toast,
    dismiss: (id: string) => dispatch({ type: actionTypes.DISMISS_TOAST, id }),
  };
}

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
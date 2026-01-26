import { useEffect } from 'react';
import { X } from 'lucide-react';
import './Toast.css';

export interface ToastMessage {
  id: string;
  message: string;
  type: 'error' | 'success' | 'info';
}

interface ToastProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
  duration?: number;
}

export function Toast({ toasts, onDismiss, duration = 4000 }: ToastProps) {
  return (
    <div className="toast-container" role="region" aria-label="Notifications">
      {toasts.map((toast) => (
        <ToastItem
          key={toast.id}
          toast={toast}
          onDismiss={onDismiss}
          duration={duration}
        />
      ))}
    </div>
  );
}

interface ToastItemProps {
  toast: ToastMessage;
  onDismiss: (id: string) => void;
  duration: number;
}

function ToastItem({ toast, onDismiss, duration }: ToastItemProps) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss(toast.id);
    }, duration);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss, duration]);

  return (
    <div
      className={`toast toast--${toast.type}`}
      role="alert"
      aria-live="polite"
    >
      <span className="toast__message">{toast.message}</span>
      <button
        type="button"
        className="toast__dismiss"
        onClick={() => onDismiss(toast.id)}
        aria-label="Dismiss notification"
      >
        <X size={16} />
      </button>
    </div>
  );
}

interface Window {
  showToast?: (props: {
    title: string;
    message: string;
    type?: 'success' | 'error' | 'info' | 'warning';
    duration?: number;
  }) => string;
} 

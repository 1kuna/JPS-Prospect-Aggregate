import React from 'react';
import { LoadingSpinner, SpinnerColor, SpinnerSize } from './LoadingSpinner';

export interface LoadingButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading: boolean;
  loadingText?: string;
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  spinnerSize?: SpinnerSize;
  spinnerColor?: SpinnerColor;
  fullWidth?: boolean;
}

const variantClasses = {
  primary: 'bg-primary hover:bg-primary/80 text-primary-foreground border-transparent',
  secondary: 'bg-secondary hover:bg-secondary/80 text-secondary-foreground border-transparent',
  danger: 'bg-danger hover:bg-danger-dark dark:bg-danger dark:hover:bg-danger-dark text-danger-foreground border-transparent',
  success: 'bg-success hover:bg-success-dark dark:bg-success dark:hover:bg-success-dark text-success-foreground border-transparent',
  outline: 'bg-transparent hover:bg-accent text-accent-foreground border-border',
};

const sizeClasses = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
};

const disabledClasses = 'opacity-50 cursor-not-allowed';

const getSpinnerColor = (variant: string): SpinnerColor => {
  switch (variant) {
    case 'outline':
      return 'gray';
    default:
      return 'white';
  }
};

const getSpinnerSize = (size: string): SpinnerSize => {
  switch (size) {
    case 'sm':
      return 'xs';
    case 'lg':
      return 'sm';
    default:
      return 'xs';
  }
};

/**
 * Button component with integrated loading state and spinner
 */
export const LoadingButton: React.FC<LoadingButtonProps> = ({
  isLoading,
  loadingText,
  children,
  variant = 'primary',
  size = 'md',
  spinnerSize,
  spinnerColor,
  fullWidth = false,
  className = '',
  disabled,
  ...props
}) => {
  const isDisabled = disabled || isLoading;
  
  const finalSpinnerSize = spinnerSize || getSpinnerSize(size);
  const finalSpinnerColor = spinnerColor || getSpinnerColor(variant);

  const buttonClasses = [
    'inline-flex items-center justify-center',
    'border rounded-md font-medium',
    'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary',
    variantClasses[variant],
    sizeClasses[size],
    fullWidth ? 'w-full' : '',
    isDisabled ? disabledClasses : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      className={buttonClasses}
      disabled={isDisabled}
      {...props}
    >
      {isLoading ? (
        <>
          <LoadingSpinner
            size={finalSpinnerSize}
            color={finalSpinnerColor}
            inline
            className="mr-2"
          />
          {loadingText || 'Loading...'}
        </>
      ) : (
        children
      )}
    </button>
  );
};

/**
 * Icon button with loading state - for buttons that only contain icons
 */
export const LoadingIconButton: React.FC<
  LoadingButtonProps & { icon?: React.ReactNode }
> = ({
  isLoading,
  icon,
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  ...props
}) => {
  const buttonClasses = [
    'inline-flex items-center justify-center',
    'border rounded-md',
    'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary',
    variantClasses[variant],
    sizeClasses[size],
    'aspect-square', // Make it square for icon buttons
    isLoading || props.disabled ? disabledClasses : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      className={buttonClasses}
      disabled={isLoading || props.disabled}
      {...props}
    >
      {isLoading ? (
        <LoadingSpinner
          size={getSpinnerSize(size)}
          color={getSpinnerColor(variant)}
        />
      ) : (
        icon || children
      )}
    </button>
  );
};

export default LoadingButton;
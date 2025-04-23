import React from 'react';
import styles from './Button.module.css'; // Import CSS module

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  // Add any custom variants or props if needed later
  // variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  // size?: 'default' | 'sm' | 'lg' | 'icon';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, children, type = "button", ...props }, ref) => {
    return (
      <button
        type={type}
        // Combine passed className with CSS module class
        className={`${styles.buttonBase} ${className || ''}`}
        ref={ref}
        {...props}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button }; 
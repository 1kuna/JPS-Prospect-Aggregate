import React from 'react';
import styles from './Button.module.css'; // Import CSS module

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  // Add any custom variants or props if needed later
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', asChild = false, children, ...props }, ref) => {
    const Comp = asChild ? 'span' : 'button';
    return (
      <Comp
        className={`${styles.buttonBase} ${className || ''}`}
        ref={ref}
        {...props}
      >
        {children}
      </Comp>
    );
  }
);
Button.displayName = "Button"; 
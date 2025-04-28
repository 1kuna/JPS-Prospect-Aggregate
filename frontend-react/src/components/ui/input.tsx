import React from 'react';
import styles from './Input.module.css'; // Import CSS module

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  // Add custom props specific to your Input if needed
}

const Input = React.forwardRef<HTMLInputElement, InputProps>((
  { className, type, ...props },
  ref
) => {
  return (
    <input
      type={type}
      // Combine passed className with module className
      className={`${styles.inputBase} ${className || ''}`}
      ref={ref}
      {...props}
    />
  );
});
Input.displayName = "Input";

// ... rest of file if any ...
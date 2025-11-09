/**
 * Input Component
 * Accessible text input with labels and error states
 * - WCAG 2.1 AA compliant
 * - Keyboard accessible
 * - Error and disabled states
 */

import { InputHTMLAttributes, forwardRef } from 'react';
import { cn } from '../../lib/utils';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, helperText, id, ...props }, ref) => {
    const inputId = id || `input-${Math.random().toString(36).substring(2, 9)}`;
    const errorId = `${inputId}-error`;
    const helperId = `${inputId}-helper`;
    
    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-white mb-2"
          >
            {label}
            {props.required && <span className="text-status-danger ml-1">*</span>}
          </label>
        )}
        
        <input
          ref={ref}
          id={inputId}
          className={cn(
            'flex h-10 w-full rounded-lg border bg-astra-panel px-3 py-2 text-sm text-white',
            'placeholder:text-white/40',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-teal focus-visible:ring-offset-2 focus-visible:ring-offset-astra-bg',
            'disabled:cursor-not-allowed disabled:opacity-50',
            error
              ? 'border-status-danger focus-visible:ring-status-danger'
              : 'border-white/10 hover:border-white/20',
            className
          )}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={
            error ? errorId : helperText ? helperId : undefined
          }
          {...props}
        />
        
        {error && (
          <p id={errorId} className="mt-1.5 text-sm text-status-danger" role="alert">
            {error}
          </p>
        )}
        
        {!error && helperText && (
          <p id={helperId} className="mt-1.5 text-sm text-white/60">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;

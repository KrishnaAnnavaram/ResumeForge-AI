import { InputHTMLAttributes, forwardRef } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1">
        {label && <label className="text-sm text-text-secondary font-body">{label}</label>}
        <input
          ref={ref}
          className={`
            bg-bg-elevated border border-bg-border rounded-md px-3 py-2
            text-text-primary font-body text-sm
            placeholder:text-text-tertiary
            focus:outline-none focus:border-accent-primary
            transition-colors duration-150
            ${error ? 'border-accent-error' : ''}
            ${className}
          `}
          {...props}
        />
        {error && <span className="text-xs text-accent-error">{error}</span>}
      </div>
    )
  }
)

Input.displayName = 'Input'

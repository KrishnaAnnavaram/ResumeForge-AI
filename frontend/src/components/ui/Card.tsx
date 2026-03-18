import { HTMLAttributes, ReactNode } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  glow?: boolean
  elevated?: boolean
}

export function Card({ children, glow, elevated, className = '', ...props }: CardProps) {
  return (
    <div
      className={`
        rounded-lg border border-bg-border p-4
        ${elevated ? 'bg-bg-elevated' : 'bg-bg-surface'}
        ${glow ? 'shadow-accent border-accent-primary/30' : 'shadow-md'}
        transition-all duration-200
        ${className}
      `}
      {...props}
    >
      {children}
    </div>
  )
}

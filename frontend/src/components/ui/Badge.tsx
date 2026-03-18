import { ReactNode } from 'react'

interface BadgeProps {
  children: ReactNode
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'muted'
  className?: string
}

const variants = {
  default: 'border-bg-border text-text-secondary',
  success: 'border-accent-success/40 text-accent-success bg-accent-success/10',
  warning: 'border-accent-warning/40 text-accent-warning bg-accent-warning/10',
  error: 'border-accent-error/40 text-accent-error bg-accent-error/10',
  info: 'border-accent-secondary/40 text-accent-secondary bg-accent-secondary/10',
  muted: 'border-bg-border text-text-tertiary bg-bg-elevated',
}

export function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  return (
    <span className={`
      inline-flex items-center px-2 py-0.5 rounded text-xs font-mono
      border ${variants[variant]} ${className}
    `}>
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, BadgeProps['variant']> = {
    applied: 'info',
    screening: 'warning',
    phone_screen: 'warning',
    technical: 'default',
    onsite: 'default',
    offer: 'success',
    rejected: 'error',
    withdrawn: 'muted',
    ghosted: 'muted',
    active: 'info',
    generating: 'warning',
    awaiting_feedback: 'warning',
    approved: 'success',
    error: 'error',
  }
  return <Badge variant={map[status] ?? 'muted'}>{status.replace(/_/g, ' ')}</Badge>
}

interface ProgressProps {
  value: number // 0-100
  className?: string
  showLabel?: boolean
  color?: string
}

export function Progress({ value, className = '', showLabel, color = 'bg-accent-primary' }: ProgressProps) {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="flex-1 bg-bg-elevated rounded-full h-1.5 overflow-hidden">
        <div
          className={`${color} h-full rounded-full transition-all duration-500`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {showLabel && (
        <span className="font-mono text-xs text-text-secondary w-8 text-right">{clamped}%</span>
      )}
    </div>
  )
}

interface CircularProgressProps {
  value: number // 0-100
  size?: number
  strokeWidth?: number
  label?: string
}

export function CircularProgress({ value, size = 80, strokeWidth = 6, label }: CircularProgressProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (value / 100) * circumference

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="var(--bg-border)" strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="var(--accent-primary)" strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.5s ease' }}
        />
      </svg>
      <div className="absolute text-center">
        <span className="font-mono text-sm font-semibold text-accent-primary">{value}%</span>
        {label && <div className="text-xs text-text-tertiary mt-0.5">{label}</div>}
      </div>
    </div>
  )
}

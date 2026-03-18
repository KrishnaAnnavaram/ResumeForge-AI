interface SkeletonProps {
  className?: string
  lines?: number
}

export function Skeleton({ className = '', lines = 1 }: SkeletonProps) {
  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="bg-bg-elevated rounded animate-pulse h-4"
          style={{ width: `${100 - (i % 3) * 15}%` }}
        />
      ))}
    </div>
  )
}

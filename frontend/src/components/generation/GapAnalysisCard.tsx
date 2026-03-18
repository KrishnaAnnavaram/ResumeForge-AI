import { Check, AlertTriangle, X } from 'lucide-react'

interface GapAnalysis {
  matched: Array<{ skill: string; confidence: string }>
  partial: Array<{ skill: string; reason: string }>
  missing: Array<{ skill: string; severity: string }>
  gap_severity_score: number
}

interface GapAnalysisCardProps {
  gapAnalysis: GapAnalysis
}

export function GapAnalysisCard({ gapAnalysis }: GapAnalysisCardProps) {
  const { matched, partial, missing, gap_severity_score } = gapAnalysis

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-text-secondary font-mono">Coverage Score</span>
        <span className={`text-sm font-mono font-semibold ${
          gap_severity_score >= 80 ? 'text-accent-success' :
          gap_severity_score >= 60 ? 'text-accent-warning' : 'text-accent-error'
        }`}>
          {gap_severity_score.toFixed(0)}%
        </span>
      </div>

      {/* Matched */}
      {matched.slice(0, 5).map((item) => (
        <div key={item.skill} className="flex items-center gap-2 text-sm">
          <Check size={12} className="text-accent-success flex-shrink-0" />
          <span className="text-text-primary">{item.skill}</span>
          {item.confidence === 'medium' && (
            <span className="text-xs text-text-tertiary">(partial)</span>
          )}
        </div>
      ))}

      {/* Partial */}
      {partial.map((item) => (
        <div key={item.skill} className="flex items-center gap-2 text-sm">
          <AlertTriangle size={12} className="text-accent-warning flex-shrink-0" />
          <span className="text-accent-warning">{item.skill}</span>
        </div>
      ))}

      {/* Missing */}
      {missing.filter(m => m.severity === 'critical').map((item) => (
        <div key={item.skill} className="flex items-center gap-2 text-sm group relative">
          <X size={12} className="text-accent-error flex-shrink-0" />
          <span className="text-text-tertiary line-through">{item.skill}</span>
          <span className="absolute left-full ml-2 hidden group-hover:block text-xs bg-bg-elevated border border-bg-border rounded px-2 py-1 text-text-secondary whitespace-nowrap z-10">
            No evidence — will not appear in resume
          </span>
        </div>
      ))}
    </div>
  )
}

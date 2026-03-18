import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { CircularProgress, Progress } from '../components/ui/Progress'
import { vaultApi } from '../api/vault'

interface Experience {
  id: string
  company: string
  title: string
  start_date: string
  end_date: string | null
  is_current: boolean
}

interface Skill {
  id: string
  name: string
  category: string | null
  proficiency: string
}

interface VaultHealth {
  completeness_score: number
  warnings: string[]
  has_summary: boolean
  experiences_count: number
  skills_count: number
  has_master_resume: boolean
}

const proficiencyColor = {
  expert: 'warning',
  proficient: 'info',
  familiar: 'muted',
} as const

export default function Vault() {
  const [health, setHealth] = useState<VaultHealth | null>(null)
  const [experiences, setExperiences] = useState<Experience[]>([])
  const [skills, setSkills] = useState<Skill[]>([])
  const [selectedExp, setSelectedExp] = useState<Experience | null>(null)

  useEffect(() => {
    vaultApi.getHealth().then(r => setHealth(r.data)).catch(() => {})
    vaultApi.listExperiences().then(r => setExperiences(r.data)).catch(() => {})
    vaultApi.listSkills().then(r => setSkills(r.data)).catch(() => {})
  }, [])

  const vaultScore = health ? Math.round(health.completeness_score * 100) : 0

  const healthMetrics = health ? [
    { label: 'Summary', value: health.has_summary ? 100 : 0 },
    { label: 'Experience', value: Math.min(health.experiences_count / 3 * 100, 100) },
    { label: 'Skills', value: Math.min(health.skills_count / 10 * 100, 100) },
    { label: 'Master Resume', value: health.has_master_resume ? 100 : 0 },
  ] : []

  const groupedSkills = skills.reduce<Record<string, Skill[]>>((acc, s) => {
    const cat = s.category || 'Other'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(s)
    return acc
  }, {})

  return (
    <div className="p-6">
      <h1 className="font-display text-2xl text-text-primary mb-6">My Vault</h1>

      {/* Health Card */}
      {health && (
        <Card className="mb-6" glow={vaultScore > 80}>
          <div className="flex items-start gap-6">
            <CircularProgress value={vaultScore} size={80} label="Health" />
            <div className="flex-1">
              <div className="text-xs text-text-tertiary font-mono mb-3">VAULT COMPLETENESS</div>
              <div className="grid grid-cols-2 gap-2">
                {healthMetrics.map(({ label, value }) => (
                  <div key={label}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-text-secondary">{label}</span>
                      <span className="font-mono text-text-tertiary">{Math.round(value)}%</span>
                    </div>
                    <Progress value={value} />
                  </div>
                ))}
              </div>
              {health.warnings.length > 0 && (
                <div className="mt-3 space-y-1">
                  {health.warnings.map((w, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-accent-warning">
                      <AlertTriangle size={10} />
                      {w}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-3 gap-4">
        {/* Experience List */}
        <Card elevated className="col-span-1">
          <div className="text-xs text-text-tertiary font-mono mb-3">EXPERIENCES</div>
          <div className="space-y-2">
            {experiences.map(exp => (
              <motion.div
                key={exp.id}
                whileHover={{ x: 2 }}
                onClick={() => setSelectedExp(exp)}
                className={`p-3 rounded-md cursor-pointer transition-colors border ${
                  selectedExp?.id === exp.id
                    ? 'border-accent-primary/40 bg-accent-primary/5'
                    : 'border-bg-border hover:border-bg-border hover:bg-bg-elevated'
                }`}
              >
                <div className="text-sm text-text-primary font-semibold">{exp.company}</div>
                <div className="text-xs text-text-secondary">{exp.title}</div>
                <div className="text-xs text-text-tertiary font-mono mt-1">
                  {exp.start_date.slice(0, 7)} — {exp.is_current ? 'present' : exp.end_date?.slice(0, 7) || '?'}
                </div>
              </motion.div>
            ))}
            {experiences.length === 0 && (
              <p className="text-text-tertiary text-sm">No experiences yet. Upload a resume to import.</p>
            )}
          </div>
        </Card>

        {/* Experience Detail */}
        <Card elevated className="col-span-1">
          {selectedExp ? (
            <div>
              <div className="font-display text-lg text-text-primary mb-1">{selectedExp.company}</div>
              <div className="text-text-secondary text-sm mb-4">{selectedExp.title}</div>
              <div className="text-xs text-text-tertiary font-mono">Bullets loaded from API</div>
            </div>
          ) : (
            <div className="text-text-tertiary text-sm text-center py-8">
              Select an experience to view bullets
            </div>
          )}
        </Card>

        {/* Skills */}
        <Card elevated className="col-span-1">
          <div className="text-xs text-text-tertiary font-mono mb-3">SKILLS</div>
          <div className="space-y-4">
            {Object.entries(groupedSkills).map(([category, catSkills]) => (
              <div key={category}>
                <div className="text-xs text-text-tertiary mb-2">{category}</div>
                <div className="flex flex-wrap gap-1.5">
                  {catSkills.map(skill => (
                    <Badge
                      key={skill.id}
                      variant={proficiencyColor[skill.proficiency as keyof typeof proficiencyColor] || 'muted'}
                    >
                      {skill.name}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
            {skills.length === 0 && (
              <p className="text-text-tertiary text-sm">No skills yet. Upload a resume to import.</p>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}

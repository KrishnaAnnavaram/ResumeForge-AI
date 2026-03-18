import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { PlusCircle, TrendingUp, Clock } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { StatusBadge } from '../components/ui/Badge'
import { CircularProgress } from '../components/ui/Progress'
import { vaultApi } from '../api/vault'
import { trackerApi } from '../api/tracker'
import { Button } from '../components/ui/Button'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
}

interface Application {
  id: string
  company: string
  role_title: string
  status: string
  applied_date: string
}

interface VaultHealth {
  completeness_score: number
  warnings: string[]
  has_summary: boolean
  experiences_count: number
  skills_count: number
  has_master_resume: boolean
}

export default function Dashboard() {
  const [vaultHealth, setVaultHealth] = useState<VaultHealth | null>(null)
  const [recentApps, setRecentApps] = useState<Application[]>([])

  useEffect(() => {
    vaultApi.getHealth().then(r => setVaultHealth(r.data)).catch(() => {})
    trackerApi.listApplications({ limit: 5 }).then(r => setRecentApps(r.data)).catch(() => {})
  }, [])

  const vaultScore = vaultHealth ? Math.round(vaultHealth.completeness_score * 100) : 0

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display text-2xl text-text-primary">Dashboard</h1>
        <Link to="/apply">
          <Button>
            <PlusCircle size={14} />
            New Application
          </Button>
        </Link>
      </div>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-2 gap-4"
      >
        {/* Vault Health */}
        <motion.div variants={itemVariants}>
          <Card glow={vaultScore > 80}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="text-xs text-text-tertiary font-mono mb-1">VAULT HEALTH</div>
                <div className="font-display text-xl text-text-primary">Career Data</div>
              </div>
              <CircularProgress value={vaultScore} size={64} />
            </div>
            {vaultHealth?.warnings.slice(0, 2).map((w, i) => (
              <div key={i} className="text-xs text-accent-warning bg-accent-warning/10 rounded px-2 py-1 mb-1">
                {w}
              </div>
            ))}
            <Link to="/vault">
              <Button variant="ghost" size="sm" className="mt-2 w-full justify-center">
                Complete Vault →
              </Button>
            </Link>
          </Card>
        </motion.div>

        {/* Recent Applications */}
        <motion.div variants={itemVariants}>
          <Card>
            <div className="text-xs text-text-tertiary font-mono mb-3">RECENT APPLICATIONS</div>
            {recentApps.length === 0 ? (
              <div className="text-text-tertiary text-sm py-4 text-center">
                No applications yet
              </div>
            ) : (
              <div className="space-y-2">
                {recentApps.map(app => (
                  <div key={app.id} className="flex items-center justify-between py-2 border-b border-bg-border last:border-0">
                    <div>
                      <div className="text-sm text-text-primary">{app.company}</div>
                      <div className="text-xs text-text-secondary">{app.role_title}</div>
                    </div>
                    <StatusBadge status={app.status} />
                  </div>
                ))}
              </div>
            )}
          </Card>
        </motion.div>

        {/* Quick Stats */}
        <motion.div variants={itemVariants}>
          <Card elevated>
            <div className="text-xs text-text-tertiary font-mono mb-3">QUICK STATS</div>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Total Applied', value: recentApps.length, icon: TrendingUp },
                { label: 'This Month', value: recentApps.filter(a => a.applied_date.startsWith(new Date().toISOString().slice(0, 7))).length, icon: Clock },
              ].map(({ label, value, icon: Icon }) => (
                <div key={label} className="bg-bg-elevated rounded-md p-3">
                  <Icon size={16} className="text-accent-primary mb-1" />
                  <div className="font-mono text-2xl text-text-primary">{value}</div>
                  <div className="text-xs text-text-tertiary">{label}</div>
                </div>
              ))}
            </div>
          </Card>
        </motion.div>

        {/* CTA */}
        <motion.div variants={itemVariants}>
          <Card elevated className="flex flex-col items-center justify-center text-center py-8">
            <div className="w-12 h-12 bg-accent-primary/10 rounded-full flex items-center justify-center mb-3">
              <PlusCircle size={24} className="text-accent-primary" />
            </div>
            <div className="font-display text-lg text-text-primary mb-1">Start Applying</div>
            <div className="text-sm text-text-secondary mb-4">Paste a JD and generate a tailored resume</div>
            <Link to="/apply">
              <Button>Generate Resume</Button>
            </Link>
          </Card>
        </motion.div>
      </motion.div>
    </div>
  )
}

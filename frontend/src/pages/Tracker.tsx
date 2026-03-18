import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, ChevronRight } from 'lucide-react'
import { StatusBadge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { trackerApi } from '../api/tracker'
import toast from 'react-hot-toast'

interface Application {
  id: string
  company: string
  role_title: string
  status: string
  applied_date: string
  source_platform: string | null
}

const STATUSES = ['applied', 'screening', 'phone_screen', 'technical', 'onsite', 'offer', 'rejected', 'withdrawn', 'ghosted']

export default function Tracker() {
  const [applications, setApplications] = useState<Application[]>([])
  const [selected, setSelected] = useState<Application | null>(null)
  const [events, setEvents] = useState<unknown[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    trackerApi.listApplications({ limit: 50 })
      .then(r => setApplications(r.data))
      .catch(() => toast.error('Failed to load applications'))
      .finally(() => setLoading(false))
  }, [])

  const handleStatusChange = async (appId: string, newStatus: string) => {
    try {
      await trackerApi.updateStatus(appId, newStatus)
      setApplications(prev => prev.map(a => a.id === appId ? { ...a, status: newStatus } : a))
      if (selected?.id === appId) setSelected(prev => prev ? { ...prev, status: newStatus } : null)
      toast.success(`Status updated to ${newStatus.replace('_', ' ')}`)
    } catch {
      toast.error('Failed to update status')
    }
  }

  const loadEvents = async (appId: string) => {
    const res = await trackerApi.getEvents(appId)
    setEvents(res.data)
  }

  const handleRowClick = (app: Application) => {
    setSelected(app)
    loadEvents(app.id)
  }

  return (
    <div className="flex h-full">
      {/* Table */}
      <div className={`flex-1 p-6 overflow-auto ${selected ? 'border-r border-bg-border' : ''}`}>
        <div className="flex items-center justify-between mb-6">
          <h1 className="font-display text-2xl text-text-primary">Applications</h1>
          <Button size="sm">
            <Plus size={14} />
            Log Application
          </Button>
        </div>

        {loading ? (
          <div className="text-text-tertiary text-sm">Loading...</div>
        ) : (
          <div className="bg-bg-surface border border-bg-border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-bg-border">
                  {['Company', 'Role', 'Status', 'Applied', 'Platform', ''].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs text-text-tertiary font-mono">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {applications.map(app => (
                  <tr
                    key={app.id}
                    onClick={() => handleRowClick(app)}
                    className={`border-b border-bg-border cursor-pointer transition-colors hover:bg-bg-elevated ${
                      selected?.id === app.id ? 'bg-bg-elevated' : ''
                    }`}
                  >
                    <td className="px-4 py-3 text-sm text-text-primary font-semibold">{app.company}</td>
                    <td className="px-4 py-3 text-sm text-text-secondary">{app.role_title}</td>
                    <td className="px-4 py-3">
                      <select
                        value={app.status}
                        onChange={(e) => { e.stopPropagation(); handleStatusChange(app.id, e.target.value) }}
                        onClick={(e) => e.stopPropagation()}
                        className="bg-bg-elevated border border-bg-border rounded text-xs text-text-primary px-2 py-1 cursor-pointer"
                      >
                        {STATUSES.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                      </select>
                    </td>
                    <td className="px-4 py-3 text-sm text-text-tertiary font-mono">{app.applied_date}</td>
                    <td className="px-4 py-3 text-sm text-text-tertiary">{app.source_platform || '—'}</td>
                    <td className="px-4 py-3">
                      <ChevronRight size={14} className="text-text-tertiary" />
                    </td>
                  </tr>
                ))}
                {applications.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-text-tertiary text-sm">
                      No applications yet. Generate a resume and log your first application.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Detail slide-over */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="w-80 bg-bg-surface border-l border-bg-border overflow-y-auto"
          >
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="font-display text-xl text-text-primary">{selected.company}</h2>
                  <p className="text-text-secondary text-sm">{selected.role_title}</p>
                </div>
                <button
                  onClick={() => setSelected(null)}
                  className="text-text-tertiary hover:text-text-primary"
                >
                  ✕
                </button>
              </div>

              <div className="mb-4">
                <StatusBadge status={selected.status} />
              </div>

              {/* Timeline */}
              <div className="text-xs text-text-tertiary font-mono mb-3">EVENT TIMELINE</div>
              <div className="space-y-3">
                {(events as Array<{ id: string; event_type: string; old_value: string | null; new_value: string | null; note: string | null; occurred_at: string }>).map(event => (
                  <div key={event.id} className="flex gap-3">
                    <div className="w-2 h-2 rounded-full bg-accent-primary mt-1.5 flex-shrink-0" />
                    <div>
                      <div className="text-xs text-text-primary">
                        {event.event_type === 'status_change'
                          ? `${event.old_value || 'created'} → ${event.new_value}`
                          : event.event_type.replace('_', ' ')}
                      </div>
                      {event.note && (
                        <div className="text-xs text-text-tertiary mt-0.5">{event.note}</div>
                      )}
                      <div className="text-xs text-text-tertiary font-mono mt-0.5">
                        {new Date(event.occurred_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

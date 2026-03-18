import { NavLink } from 'react-router-dom'
import { LayoutDashboard, PlusCircle, BookOpen, Briefcase } from 'lucide-react'
import { motion } from 'framer-motion'
import { useAuthStore } from '../../store/authStore'
import { CircularProgress } from '../ui/Progress'

const navItems = [
  { path: '/apply', icon: PlusCircle, label: 'New Application', accent: true },
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/vault', icon: BookOpen, label: 'My Vault' },
  { path: '/tracker', icon: Briefcase, label: 'Applications' },
]

export function Sidebar() {
  const { displayName, email, logout } = useAuthStore()
  const vaultScore = 45 // TODO: pull from vault health API

  return (
    <motion.aside
      initial={{ x: -16, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="w-56 h-full bg-bg-surface border-r border-bg-border flex flex-col"
    >
      {/* Logo */}
      <div className="p-4 border-b border-bg-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-accent-primary rounded-md flex items-center justify-center">
            <span className="font-display text-bg-base font-bold text-sm">C</span>
          </div>
          <div>
            <div className="font-display text-text-primary text-sm">CareerOS</div>
            <div className="font-mono text-text-tertiary text-xs">v1.0.0</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 flex flex-col gap-1">
        {navItems.map(({ path, icon: Icon, label, accent }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            className={({ isActive }) => `
              flex items-center gap-3 px-3 py-2 rounded-md text-sm font-body
              transition-all duration-150 group
              ${isActive
                ? 'bg-accent-primary/10 text-accent-primary border-l-2 border-accent-primary pl-[10px]'
                : accent
                  ? 'text-accent-primary border border-accent-primary/30 hover:bg-accent-primary/10'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
              }
            `}
          >
            <Icon size={16} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User + Vault Health */}
      <div className="p-3 border-t border-bg-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-bg-elevated rounded-full flex items-center justify-center border border-bg-border">
            <span className="font-mono text-xs text-text-secondary">
              {(displayName || email || 'U')[0].toUpperCase()}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm text-text-primary truncate">{displayName || email}</div>
            <div className="text-xs text-text-tertiary">Vault: {vaultScore}%</div>
          </div>
          <button
            onClick={logout}
            className="text-text-tertiary hover:text-accent-error text-xs transition-colors"
          >
            out
          </button>
        </div>
        <div className="mt-2">
          <div className="bg-bg-elevated rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-accent-primary h-full rounded-full transition-all duration-500"
              style={{ width: `${vaultScore}%` }}
            />
          </div>
        </div>
      </div>
    </motion.aside>
  )
}

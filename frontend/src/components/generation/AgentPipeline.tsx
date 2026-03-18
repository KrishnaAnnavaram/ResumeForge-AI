import { motion, AnimatePresence } from 'framer-motion'
import { Check, AlertCircle } from 'lucide-react'
import { useSessionStore } from '../../store/sessionStore'

export function AgentPipeline() {
  const { agentStatuses } = useSessionStore()

  return (
    <div className="flex flex-col gap-2">
      {agentStatuses.map((agent, i) => (
        <motion.div
          key={agent.agent}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.05 }}
          className="flex items-center gap-3 py-1"
        >
          {/* Status dot */}
          <div className="relative w-5 h-5 flex items-center justify-center">
            {agent.status === 'idle' && (
              <div className="w-2 h-2 rounded-full bg-text-tertiary" />
            )}
            {agent.status === 'running' && (
              <div className="w-2.5 h-2.5 rounded-full bg-accent-primary agent-running" />
            )}
            {agent.status === 'done' && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
              >
                <Check size={14} className="text-accent-success" />
              </motion.div>
            )}
            {agent.status === 'error' && (
              <AlertCircle size={14} className="text-accent-error" />
            )}
          </div>

          {/* Label */}
          <span className={`text-sm font-body transition-colors ${
            agent.status === 'running'
              ? 'text-accent-primary'
              : agent.status === 'done'
                ? 'text-text-secondary line-through'
                : agent.status === 'error'
                  ? 'text-accent-error'
                  : 'text-text-tertiary'
          }`}>
            {agent.label}
          </span>

          {agent.status === 'running' && (
            <span className="text-xs text-text-tertiary font-mono ml-auto animate-pulse">running...</span>
          )}
        </motion.div>
      ))}
    </div>
  )
}

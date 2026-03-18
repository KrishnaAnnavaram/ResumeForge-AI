import { useState } from 'react'
import { CheckCircle, RefreshCw, Save } from 'lucide-react'
import { Button } from '../ui/Button'
import { generationApi } from '../../api/generation'
import toast from 'react-hot-toast'
import { useSessionStore } from '../../store/sessionStore'

interface FeedbackControlsProps {
  onApproved: () => void
}

export function FeedbackControls({ onApproved }: FeedbackControlsProps) {
  const { sessionId } = useSessionStore()
  const [feedback, setFeedback] = useState('')
  const [loading, setLoading] = useState(false)
  const [approving, setApproving] = useState(false)

  const handleRefine = async () => {
    if (!sessionId || !feedback.trim()) return
    setLoading(true)
    try {
      await generationApi.submitFeedback(sessionId, 'refine_section', feedback)
      toast.success('Feedback submitted — regenerating...')
      setFeedback('')
    } catch {
      toast.error('Failed to submit feedback')
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async () => {
    if (!sessionId) return
    setApproving(true)
    try {
      await generationApi.approve(sessionId)
      toast.success('Approved! Ready to log application.')
      onApproved()
    } catch {
      toast.error('Failed to approve')
    } finally {
      setApproving(false)
    }
  }

  const handleFullRegen = async () => {
    if (!sessionId) return
    try {
      await generationApi.submitFeedback(sessionId, 'full_regen', 'Please regenerate with a fresh approach.')
      toast.success('Requesting full regeneration...')
    } catch {
      toast.error('Failed to request regeneration')
    }
  }

  return (
    <div className="border-t border-bg-border p-4 bg-bg-surface">
      <div className="flex flex-col gap-3">
        {/* Feedback input */}
        <div className="flex gap-2">
          <input
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Describe what to refine (e.g. 'Make summary more technical')"
            className="flex-1 bg-bg-elevated border border-bg-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent-primary"
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleRefine()}
          />
          <Button variant="secondary" size="sm" onClick={handleRefine} loading={loading}>
            <RefreshCw size={14} />
            Refine
          </Button>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={handleFullRegen}>
            <RefreshCw size={14} />
            Full Regen
          </Button>
          <Button variant="secondary" size="sm">
            <Save size={14} />
            Save Draft
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleApprove}
            loading={approving}
            className="ml-auto"
          >
            <CheckCircle size={14} />
            Approve
          </Button>
        </div>
      </div>
    </div>
  )
}

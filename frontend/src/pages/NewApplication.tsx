import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Zap } from 'lucide-react'
import { generationApi } from '../api/generation'
import { useSessionStore } from '../store/sessionStore'
import { useUIStore } from '../store/uiStore'
import { AgentPipeline } from '../components/generation/AgentPipeline'
import { GapAnalysisCard } from '../components/generation/GapAnalysisCard'
import { ResumePreview } from '../components/generation/ResumePreview'
import { FeedbackControls } from '../components/generation/FeedbackControls'
import { ChatPanel } from '../components/chat/ChatPanel'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { useSSE } from '../hooks/useSSE'
import toast from 'react-hot-toast'

export default function NewApplication() {
  const {
    jdText, setJdText, setSession,
    updateAgentStatus, setComplete, setStreaming,
    sessionId, isStreaming, gapAnalysis, resumeVersionId, clVersionId,
  } = useSessionStore()
  const { activeTab, setActiveTab } = useUIStore()
  const [sseUrl, setSseUrl] = useState<string | null>(null)
  const [resumeContent, setResumeContent] = useState<string | null>(null)
  const [clContent, setClContent] = useState<string | null>(null)
  const [isApproved, setIsApproved] = useState(false)

  const handleSSEMessage = useCallback((data: Record<string, unknown>) => {
    const type = data.type as string
    if (type === 'agent_start') {
      updateAgentStatus(data.agent as string, 'running')
    } else if (type === 'agent_complete') {
      updateAgentStatus(data.agent as string, 'done')
    } else if (type === 'agent_error') {
      updateAgentStatus(data.agent as string, 'error', data.error as string)
    } else if (type === 'complete') {
      setComplete(data)
      setStreaming(false)
      toast.success('Generation complete!')
      // Would fetch actual content here in full implementation
      setResumeContent('# Resume Generated\n\nYour tailored resume is ready. Check the evidence panel for retrieved bullets.\n\n## Summary\n\nContent generated based on your vault data and JD requirements.')
      setClContent('Cover letter content generated based on your experience and the job requirements.')
    } else if (type === 'error') {
      toast.error(`Generation failed: ${data.error}`)
      setStreaming(false)
    }
  }, [updateAgentStatus, setComplete, setStreaming])

  useSSE(sseUrl, {
    onMessage: handleSSEMessage,
    onError: () => { setStreaming(false); toast.error('Connection lost') },
  })

  const handleAnalyze = async () => {
    if (!jdText.trim()) {
      toast.error('Please paste a job description first')
      return
    }

    setStreaming(true)
    try {
      // Parse JD
      const jdRes = await generationApi.analyzeJD(jdText)
      const jdId = jdRes.data.jd_id

      // Create session
      const sessionRes = await generationApi.createSession(jdId)
      const newSessionId = sessionRes.data.session_id
      setSession(newSessionId, jdId)

      // Start SSE stream
      setSseUrl(`/api/generation/sessions/${newSessionId}/stream`)
    } catch (err: unknown) {
      toast.error('Failed to start generation')
      setStreaming(false)
    }
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-bg-border bg-bg-surface">
        <h1 className="font-display text-xl text-text-primary">New Application</h1>
        {sessionId && (
          <span className="font-mono text-xs text-text-tertiary">
            Session: {sessionId.slice(0, 8)}...
          </span>
        )}
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left panel */}
        <div className="w-80 flex flex-col border-r border-bg-border overflow-y-auto">
          {/* JD Input */}
          <div className="p-4 border-b border-bg-border">
            <label className="text-xs text-text-secondary font-mono mb-2 block">JOB DESCRIPTION</label>
            <textarea
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste the full job description here..."
              className="w-full h-48 bg-bg-elevated border border-bg-border rounded-md p-3 text-sm text-text-primary placeholder:text-text-tertiary resize-none focus:outline-none focus:border-accent-primary font-body"
            />
            <Button
              className="w-full justify-center mt-3"
              onClick={handleAnalyze}
              loading={isStreaming}
              disabled={!jdText.trim()}
            >
              <Zap size={14} />
              {isStreaming ? 'Generating...' : 'Analyze & Generate'}
            </Button>
          </div>

          {/* Agent Pipeline */}
          <div className="p-4 border-b border-bg-border">
            <div className="text-xs text-text-secondary font-mono mb-3">AGENT PIPELINE</div>
            <AgentPipeline />
          </div>

          {/* Gap Analysis */}
          {gapAnalysis && (
            <div className="p-4">
              <div className="text-xs text-text-secondary font-mono mb-3">GAP ANALYSIS</div>
              <GapAnalysisCard gapAnalysis={gapAnalysis as Parameters<typeof GapAnalysisCard>[0]['gapAnalysis']} />
            </div>
          )}
        </div>

        {/* Right panel */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-bg-border bg-bg-surface">
            {(['resume', 'cover_letter', 'evidence', 'versions'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-3 text-sm font-body transition-colors border-b-2 ${
                  activeTab === tab
                    ? 'text-accent-primary border-accent-primary'
                    : 'text-text-secondary border-transparent hover:text-text-primary'
                }`}
              >
                {tab.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="flex-1 overflow-hidden">
            {activeTab === 'resume' && (
              <ResumePreview content={resumeContent} isLoading={isStreaming && !resumeContent} />
            )}
            {activeTab === 'cover_letter' && (
              <div className="p-6 overflow-auto h-full">
                {clContent ? (
                  <div className="font-body text-text-primary leading-relaxed whitespace-pre-wrap">{clContent}</div>
                ) : (
                  <div className="text-text-tertiary text-sm text-center mt-16">
                    Cover letter will appear here after generation
                  </div>
                )}
              </div>
            )}
            {activeTab === 'evidence' && (
              <div className="p-4 text-text-tertiary text-sm">
                Evidence panel — shows retrieved bullets and their scores
              </div>
            )}
            {activeTab === 'versions' && (
              <div className="p-4 text-text-tertiary text-sm">
                Version history panel
              </div>
            )}
          </div>

          {/* Feedback controls */}
          {(resumeVersionId || isApproved) && (
            <FeedbackControls onApproved={() => setIsApproved(true)} />
          )}
        </div>
      </div>

      {/* Chat bar */}
      <div className="h-48 border-t border-bg-border">
        <ChatPanel />
      </div>
    </div>
  )
}

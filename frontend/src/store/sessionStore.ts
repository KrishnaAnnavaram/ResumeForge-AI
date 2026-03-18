import { create } from 'zustand'

interface AgentStatus {
  agent: string
  label: string
  status: 'idle' | 'running' | 'done' | 'error'
  error?: string
}

interface SessionState {
  sessionId: string | null
  jdId: string | null
  jdText: string
  agentStatuses: AgentStatus[]
  gapAnalysis: Record<string, unknown> | null
  criticReport: Record<string, unknown> | null
  resumeVersionId: string | null
  clVersionId: string | null
  warnings: string[]
  isStreaming: boolean
  setJdText: (text: string) => void
  setSession: (sessionId: string, jdId: string) => void
  updateAgentStatus: (agent: string, status: AgentStatus['status'], error?: string) => void
  setComplete: (data: Record<string, unknown>) => void
  setStreaming: (v: boolean) => void
  reset: () => void
}

const DEFAULT_AGENTS: AgentStatus[] = [
  { agent: 'load_profile', label: 'Load Profile', status: 'idle' },
  { agent: 'parse_jd', label: 'Parse JD', status: 'idle' },
  { agent: 'retrieve_evidence', label: 'Retrieve Evidence', status: 'idle' },
  { agent: 'analyze_gaps', label: 'Gap Analysis', status: 'idle' },
  { agent: 'plan_rewrite', label: 'Plan Strategy', status: 'idle' },
  { agent: 'generate_resume', label: 'Write Resume', status: 'idle' },
  { agent: 'generate_cl', label: 'Write Cover Letter', status: 'idle' },
  { agent: 'critic_validate', label: 'Validate', status: 'idle' },
]

export const useSessionStore = create<SessionState>((set) => ({
  sessionId: null,
  jdId: null,
  jdText: '',
  agentStatuses: DEFAULT_AGENTS,
  gapAnalysis: null,
  criticReport: null,
  resumeVersionId: null,
  clVersionId: null,
  warnings: [],
  isStreaming: false,

  setJdText: (text) => set({ jdText: text }),
  setSession: (sessionId, jdId) => set({ sessionId, jdId, agentStatuses: DEFAULT_AGENTS }),
  updateAgentStatus: (agent, status, error) =>
    set((state) => ({
      agentStatuses: state.agentStatuses.map((a) =>
        a.agent === agent ? { ...a, status, error } : a
      ),
    })),
  setComplete: (data) =>
    set({
      gapAnalysis: (data.gap_analysis as Record<string, unknown>) ?? null,
      criticReport: (data.critic_report as Record<string, unknown>) ?? null,
      resumeVersionId: (data.resume_version_id as string) ?? null,
      clVersionId: (data.cl_version_id as string) ?? null,
      warnings: (data.warnings as string[]) ?? [],
      isStreaming: false,
    }),
  setStreaming: (v) => set({ isStreaming: v }),
  reset: () => set({
    sessionId: null, jdId: null, jdText: '',
    agentStatuses: DEFAULT_AGENTS, gapAnalysis: null,
    criticReport: null, resumeVersionId: null, clVersionId: null,
    warnings: [], isStreaming: false,
  }),
}))

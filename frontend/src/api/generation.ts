import client from './client'

export const generationApi = {
  analyzeJD: (rawText: string, sourceUrl?: string) =>
    client.post('/jd/analyze', { raw_text: rawText, source_url: sourceUrl }),
  createSession: (jdId: string) =>
    client.post('/generation/sessions', { jd_id: jdId }),
  getSession: (sessionId: string) =>
    client.get(`/generation/sessions/${sessionId}`),
  submitFeedback: (sessionId: string, type: string, content: string) =>
    client.post(`/generation/sessions/${sessionId}/feedback`, { type, content }),
  approve: (sessionId: string) =>
    client.post(`/generation/sessions/${sessionId}/approve`),
  abandon: (sessionId: string) =>
    client.post(`/generation/sessions/${sessionId}/abandon`),
  getVersions: (sessionId: string) =>
    client.get(`/generation/sessions/${sessionId}/versions`),
  getEvidence: (sessionId: string) =>
    client.get(`/generation/sessions/${sessionId}/evidence`),
}

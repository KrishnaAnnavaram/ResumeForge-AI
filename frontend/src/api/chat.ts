import client from './client'

export const chatApi = {
  createSession: (contextType: string, generationSessionId?: string) =>
    client.post('/chat/sessions', { context_type: contextType, generation_session_id: generationSessionId }),
  sendMessage: (sessionId: string, content: string) =>
    client.post(`/chat/sessions/${sessionId}/messages`, { content }),
  listMessages: (sessionId: string, limit = 50) =>
    client.get(`/chat/sessions/${sessionId}/messages`, { params: { limit } }),
}

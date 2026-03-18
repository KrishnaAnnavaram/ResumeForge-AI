import client from './client'

export const trackerApi = {
  createApplication: (data: Record<string, unknown>) =>
    client.post('/tracker/applications', data),
  listApplications: (params?: Record<string, unknown>) =>
    client.get('/tracker/applications', { params }),
  getApplication: (id: string) =>
    client.get(`/tracker/applications/${id}`),
  updateStatus: (id: string, newStatus: string, note?: string) =>
    client.patch(`/tracker/applications/${id}/status`, { new_status: newStatus, note }),
  addNote: (id: string, content: string) =>
    client.post(`/tracker/applications/${id}/notes`, { content }),
  getEvents: (id: string) =>
    client.get(`/tracker/applications/${id}/events`),
}

import client from './client'

export const vaultApi = {
  getHealth: () => client.get('/vault/health'),
  getProfile: () => client.get('/vault/profile'),
  updateProfile: (data: Record<string, unknown>) => client.patch('/vault/profile', data),
  listExperiences: () => client.get('/vault/experiences'),
  createExperience: (data: Record<string, unknown>) => client.post('/vault/experiences', data),
  getBullets: (expId: string) => client.get(`/vault/experiences/${expId}/bullets`),
  createBullet: (expId: string, data: Record<string, unknown>) =>
    client.post(`/vault/experiences/${expId}/bullets`, data),
  updateBullet: (bulletId: string, data: Record<string, unknown>) =>
    client.patch(`/vault/bullets/${bulletId}`, data),
  listSkills: () => client.get('/vault/skills'),
  createSkill: (data: Record<string, unknown>) => client.post('/vault/skills', data),
}

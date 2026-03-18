import client from './client'

export const authApi = {
  register: (email: string, password: string, displayName?: string) =>
    client.post('/auth/register', { email, password, display_name: displayName }),
  login: (email: string, password: string) =>
    client.post('/auth/login', { email, password }),
  me: () =>
    client.get('/auth/me'),
}

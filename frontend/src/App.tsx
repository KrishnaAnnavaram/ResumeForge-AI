import { Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import Dashboard from './pages/Dashboard'
import NewApplication from './pages/NewApplication'
import Vault from './pages/Vault'
import Tracker from './pages/Tracker'
import Login from './pages/Login'
import { useAuthStore } from './store/authStore'

export default function App() {
  const { token } = useAuthStore()

  if (!token) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/apply" element={<NewApplication />} />
        <Route path="/vault" element={<Vault />} />
        <Route path="/tracker" element={<Tracker />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  )
}

import { create } from 'zustand'

interface UIState {
  sidebarCollapsed: boolean
  activeTab: 'resume' | 'cover_letter' | 'evidence' | 'versions'
  chatOpen: boolean
  setSidebarCollapsed: (v: boolean) => void
  setActiveTab: (tab: UIState['activeTab']) => void
  setChatOpen: (v: boolean) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  activeTab: 'resume',
  chatOpen: false,
  setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setChatOpen: (v) => set({ chatOpen: v }),
}))

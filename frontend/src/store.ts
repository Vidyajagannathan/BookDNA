import { create } from 'zustand'
type UIState = { theme: 'light' | 'dark'; toggleTheme: () => void }
export const useUI = create<UIState>((set) => ({ theme: (localStorage.getItem('theme') as 'light' | 'dark') || 'light', toggleTheme: () => set((state) => { const theme = state.theme === 'light' ? 'dark' : 'light'; localStorage.setItem('theme', theme); return { theme } }) }))


import { create } from 'zustand'
import api from '../api/client'

interface AdminState {
  token: string | null
  isAuthenticated: boolean
  login: (password: string) => Promise<boolean>
  logout: () => void
}

export const useAdminStore = create<AdminState>((set) => ({
  token: sessionStorage.getItem('admin_token'),
  isAuthenticated: !!sessionStorage.getItem('admin_token'),

  login: async (password: string) => {
    try {
      const { data } = await api.post('/admin/login', { password })
      const token = data.token as string
      sessionStorage.setItem('admin_token', token)
      set({ token, isAuthenticated: true })
      return true
    } catch {
      return false
    }
  },

  logout: () => {
    sessionStorage.removeItem('admin_token')
    set({ token: null, isAuthenticated: false })
  },
}))

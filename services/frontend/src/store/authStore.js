import { create } from 'zustand'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || '/api/v1'

const api = axios.create({ baseURL: API })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('access_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(
  r => r,
  async err => {
    if (err.response?.status === 401) {
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post(`${API}/auth/refresh`, { refresh_token: refresh })
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          err.config.headers.Authorization = `Bearer ${data.access_token}`
          return api.request(err.config)
        } catch {
          useAuthStore.getState().logout()
        }
      }
    }
    return Promise.reject(err)
  }
)

export { api }

export const useAuthStore = create((set, get) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  loading: false,
  error: null,

  login: async (email, password) => {
    set({ loading: true, error: null })
    try {
      const { data } = await api.post('/auth/login', { email, password })
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      const { data: user } = await api.get('/auth/users/me')
      set({ user, isAuthenticated: true, loading: false })
      return true
    } catch (e) {
      set({ error: e.response?.data?.detail || 'Login failed', loading: false })
      return false
    }
  },

  register: async (email, fullName, password) => {
    set({ loading: true, error: null })
    try {
      const { data } = await api.post('/auth/register', { email, full_name: fullName, password })
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      const { data: user } = await api.get('/auth/users/me')
      set({ user, isAuthenticated: true, loading: false })
      return true
    } catch (e) {
      set({ error: e.response?.data?.detail || 'Registration failed', loading: false })
      return false
    }
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null, isAuthenticated: false })
  },

  fetchUser: async () => {
    try {
      const { data } = await api.get('/auth/users/me')
      set({ user: data })
    } catch { get().logout() }
  },
}))

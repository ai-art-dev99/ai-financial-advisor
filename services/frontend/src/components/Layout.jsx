import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import {
  LayoutDashboard, PieChart, TrendingUp, Shield, MessageSquare,
  LogOut, Bot, Zap
} from 'lucide-react'
import clsx from 'clsx'

const NAV = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/portfolio', label: 'Portfolio', icon: PieChart },
  { path: '/market', label: 'Market', icon: TrendingUp },
  { path: '/risk-profile', label: 'Risk Profile', icon: Shield },
  { path: '/chat', label: 'AI Advisor', icon: MessageSquare },
]

export default function Layout() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
    : '?'

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ── Sidebar ──────────────────────────────── */}
      <aside className="w-64 flex flex-col bg-obsidian-900 border-r border-obsidian-700 shrink-0">
        {/* Logo */}
        <div className="px-6 py-6 border-b border-obsidian-700">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gold-500 flex items-center justify-center">
              <Bot size={18} className="text-obsidian-950" />
            </div>
            <div>
              <p className="font-display text-white text-lg leading-none">Argo</p>
              <p className="text-xs text-obsidian-400 mt-0.5">AI Advisor</p>
            </div>
          </div>
        </div>

        {/* Status pill */}
        <div className="px-4 pt-4">
          <div className="flex items-center gap-2 px-3 py-2 bg-obsidian-800 rounded-lg border border-obsidian-700">
            <Zap size={12} className="text-gold-400 glow-gold" />
            <span className="text-xs text-obsidian-300">Markets open</span>
            <div className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-500" />
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 mt-4 space-y-1">
          {NAV.map(({ path, label, icon: Icon }) => (
            <div
              key={path}
              className={clsx('nav-item', pathname === path && 'active')}
              onClick={() => navigate(path)}
            >
              <Icon size={16} />
              <span>{label}</span>
            </div>
          ))}
        </nav>

        {/* User */}
        <div className="p-4 border-t border-obsidian-700">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gold-500 flex items-center justify-center text-obsidian-950 text-xs font-medium">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white truncate">{user?.full_name || 'User'}</p>
              <p className="text-xs text-obsidian-400 truncate">{user?.email}</p>
            </div>
            <button onClick={logout} className="text-obsidian-500 hover:text-red-400 transition-colors">
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Content ─────────────────────────── */}
      <main className="flex-1 overflow-y-auto bg-obsidian-950">
        <Outlet />
      </main>
    </div>
  )
}
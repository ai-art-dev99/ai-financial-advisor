import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { Bot, Eye, EyeOff, ArrowRight } from 'lucide-react'

export default function Login() {
  const [mode, setMode] = useState('login')  // 'login' | 'register'
  const [form, setForm] = useState({ email: '', password: '', fullName: '' })
  const [showPwd, setShowPwd] = useState(false)
  const { login, register, loading, error } = useAuthStore()
  const navigate = useNavigate()

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async e => {
    e.preventDefault()
    let ok
    if (mode === 'login') {
      ok = await login(form.email, form.password)
    } else {
      ok = await register(form.email, form.fullName, form.password)
    }
    if (ok) navigate('/')
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-obsidian-950 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-96 h-96 rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(201,168,76,0.08) 0%, transparent 70%)' }} />
      </div>

      <div className="w-full max-w-md px-6">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-10 justify-center">
          <div className="w-12 h-12 rounded-2xl bg-gold-500 flex items-center justify-center">
            <Bot size={22} className="text-obsidian-950" />
          </div>
          <div>
            <p className="font-display text-white text-2xl leading-none">Argo</p>
            <p className="text-obsidian-400 text-xs">AI Financial Advisor</p>
          </div>
        </div>

        {/* Card */}
        <div className="card p-8">
          <h2 className="font-display text-xl text-white mb-1">
            {mode === 'login' ? 'Welcome back' : 'Create account'}
          </h2>
          <p className="text-obsidian-400 text-sm mb-6">
            {mode === 'login' ? 'Sign in to your portfolio' : 'Start your investment journey'}
          </p>

          <form onSubmit={submit} className="space-y-4">
            {mode === 'register' && (
              <div>
                <label className="stat-label block mb-2">Full Name</label>
                <input className="input" placeholder="Jane Doe"
                  value={form.fullName} onChange={set('fullName')} required />
              </div>
            )}
            <div>
              <label className="stat-label block mb-2">Email</label>
              <input className="input" type="email" placeholder="jane@example.com"
                value={form.email} onChange={set('email')} required />
            </div>
            <div>
              <label className="stat-label block mb-2">Password</label>
              <div className="relative">
                <input className="input pr-10" type={showPwd ? 'text' : 'password'}
                  placeholder="••••••••" value={form.password} onChange={set('password')} required minLength={8} />
                <button type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-obsidian-500 hover:text-obsidian-300"
                  onClick={() => setShowPwd(!showPwd)}>
                  {showPwd ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
                <p className="text-red-400 text-xs">{error}</p>
              </div>
            )}

            <button type="submit" disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2 mt-2">
              {loading ? (
                <div className="w-4 h-4 border-2 border-obsidian-950/30 border-t-obsidian-950 rounded-full animate-spin" />
              ) : (
                <>
                  {mode === 'login' ? 'Sign In' : 'Create Account'}
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          </form>

          <p className="text-center text-sm text-obsidian-400 mt-6">
            {mode === 'login' ? "Don't have an account?" : "Already have an account?"}
            {' '}
            <button className="text-gold-400 hover:text-gold-300 transition-colors"
              onClick={() => setMode(m => m === 'login' ? 'register' : 'login')}>
              {mode === 'login' ? 'Sign up' : 'Sign in'}
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
